"""
Tests for brain.mechanisms.making_layer.MakingLayer.

Covers:
  - Empty tick is a safe no-op
  - record_execution updates intent_state correctly
  - Untagged executions stored but flagged, don't credit valid intents
  - should_block fires on invalid intent
  - should_block fires when flailing
  - Flailing detection (5+ consecutive failures)
  - Flailing resets on a successful execution
  - Rumination detection (same code re-run within window)
  - Refinement chain reconstruction via parent_id
  - Mastery detection (high rolling success ratio)
  - making_state classification (idle / making / refining / flailing / mastering)
  - State persists across instances
  - IPW handshake throttle (acknowledge_proposal suppresses re-fire)
  - reset_flailing clears state
  - configure_limits overrides defaults
  - get_state shape consistent
  - tick with execution dict records it

PYTHONDONTWRITEBYTECODE=1 + AGENT_HOME=/tmp + monkeypatched _STATE_DIR keeps
these isolated per-test (the same fix applied to test_outward_reach_layer.py).
"""
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Fresh AGENT_HOME + per-test state dir.

    base_mechanism._STATE_DIR is captured at module import, so just changing
    AGENT_HOME via env var isn't enough — point _STATE_DIR explicitly at the
    test tmp_path or persisted state leaks across tests.
    """
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    import importlib
    import brain.mechanisms.making_layer as mod
    importlib.reload(mod)
    return mod.MakingLayer()


def test_empty_tick_is_noop():
    layer = _fresh_layer()
    out = layer.tick({})
    assert out["_fired_tick"] is False
    assert out["execution_count"] == 0
    assert out["making_state"] == "idle"


def test_record_execution_updates_intent_state():
    layer = _fresh_layer()
    rec = layer.record_execution(
        intent="compute",
        code="2 + 2",
        outcome="success",
        duration_ms=5,
    )
    assert rec["intent"] == "compute"
    assert rec["outcome"] == "success"
    assert rec["id"]  # has an id
    assert layer.intent_state["compute"]["total"] == 1
    assert layer.intent_state["compute"]["success"] == 1
    assert layer.intent_state["compute"]["failure"] == 0


def test_untagged_execution_is_recorded_but_not_credited():
    layer = _fresh_layer()
    layer.record_execution(intent="not-valid", code="print(1)", outcome="success")
    # No valid intent should be credited.
    for k in ("compute", "explore", "build", "debug"):
        assert layer.intent_state[k]["total"] == 0
    # But it lands in the history.
    assert layer.executions[-1]["intent"] == "__untagged__"


def test_should_block_invalid_intent():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="banana")
    assert block is True
    assert "invalid intent" in reason


def test_should_block_when_flailing():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(
            intent="debug",
            code="raise Exception()",
            outcome="runtime_error",
            error_class="Exception",
        )
    assert layer.is_flailing() is True
    block, reason = layer.should_block("debug")
    assert block is True
    assert "flailing" in reason


def test_flailing_resets_on_success():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(intent="debug", code=f"raise X{_}", outcome="runtime_error")
    assert layer.is_flailing() is True
    layer.record_execution(intent="debug", code="2 + 2", outcome="success")
    assert layer.consecutive_failures == 0
    assert layer.is_flailing() is False


def test_rumination_detected_on_same_code_replay():
    layer = _fresh_layer()
    code = "x = 1\nprint(x)"
    layer.record_execution(intent="explore", code=code, outcome="success")
    layer.record_execution(intent="explore", code=code, outcome="success")
    rumination_hashes = layer.detect_rumination()
    assert len(rumination_hashes) == 1


def test_rumination_not_detected_on_modified_code():
    layer = _fresh_layer()
    layer.record_execution(intent="explore", code="x = 1", outcome="success")
    layer.record_execution(intent="explore", code="x = 2", outcome="success")
    assert layer.detect_rumination() == []


def test_refinement_chain_walks_parent_ids():
    layer = _fresh_layer()
    rec1 = layer.record_execution(intent="build", code="def f(): pass", outcome="syntax_error")
    rec2 = layer.record_execution(
        intent="debug",
        code="def f():\n    pass",
        outcome="success",
        previous_execution_id=rec1["id"],
    )
    rec3 = layer.record_execution(
        intent="debug",
        code="f()",
        outcome="success",
        previous_execution_id=rec2["id"],
    )
    chain = layer.refinement_chain(rec3["id"])
    chain_ids = [r["id"] for r in chain]
    # Chronological order: rec1 → rec2 → rec3
    assert chain_ids == [rec1["id"], rec2["id"], rec3["id"]]


def test_refinement_chain_unknown_id_returns_empty():
    layer = _fresh_layer()
    layer.record_execution(intent="compute", code="2+2", outcome="success")
    assert layer.refinement_chain("does_not_exist") == []


def test_mastery_detection():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    # Need at least MASTERY_WINDOW // 2 entries with high success rate.
    needed = mod.MASTERY_WINDOW // 2 + 2
    for i in range(needed):
        layer.record_execution(intent="compute", code=f"x={i}", outcome="success")
    assert layer.is_mastering() is True
    assert layer.mastery_score() == 1.0


def test_mastery_below_threshold():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    # Half success, half failure → 0.5, below the 0.85 threshold.
    needed = mod.MASTERY_WINDOW
    for i in range(needed // 2):
        layer.record_execution(intent="compute", code=f"x={i}", outcome="success")
        layer.record_execution(intent="compute", code=f"y={i}", outcome="runtime_error")
    assert layer.is_mastering() is False


def test_making_state_priority():
    from brain.mechanisms import making_layer as mod

    # Idle state initially.
    layer = _fresh_layer()
    assert layer.making_state() == "idle"

    # Single recent success → making.
    layer.record_execution(intent="compute", code="1+1", outcome="success")
    assert layer.making_state() == "making"

    # Recent execution with parent → refining.
    rec1 = layer.record_execution(intent="compute", code="bad code", outcome="syntax_error")
    layer.record_execution(
        intent="debug", code="good code",
        outcome="success", previous_execution_id=rec1["id"],
    )
    assert layer.making_state() == "refining"

    # Drive flailing.
    layer = _fresh_layer()
    for _ in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(intent="debug", code=f"x{_}", outcome="runtime_error")
    assert layer.making_state() == "flailing"


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    layer1.record_execution(intent="compute", code="2+2", outcome="success")
    layer1.record_execution(intent="compute", code="raise X", outcome="runtime_error")

    from brain.mechanisms.making_layer import MakingLayer
    layer2 = MakingLayer()
    assert layer2.intent_state["compute"]["total"] == 2
    assert layer2.intent_state["compute"]["success"] == 1
    assert layer2.intent_state["compute"]["failure"] == 1
    assert len(layer2.executions) == 2
    assert layer2.consecutive_failures == 1


def test_ipw_handshake_throttled():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(intent="debug", code=f"x{_}", outcome="runtime_error")
    assert layer.should_propose_identity_update() is True

    layer.acknowledge_proposal()
    # Same state — should now suppress.
    assert layer.should_propose_identity_update() is False

    # Need IPW_REPORT_EVERY more failures to re-fire.
    for _ in range(mod.IPW_REPORT_EVERY):
        layer.record_execution(intent="debug", code=f"y{_}", outcome="runtime_error")
    assert layer.should_propose_identity_update() is True


def test_proposed_identity_signal_shape():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    for i in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(
            intent="build",
            code=f"x{i}",
            outcome="runtime_error",
            error_class="ValueError",
        )
    sig = layer.proposed_identity_signal()
    for key in ("source", "kind", "consecutive_failures", "dominant_intent",
                "intent_success_rates", "recent_errors"):
        assert key in sig
    assert sig["source"] == "MakingLayer"
    assert sig["kind"] == "sustained_flailing"
    assert sig["dominant_intent"] == "build"


def test_reset_flailing():
    from brain.mechanisms import making_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FLAILING_THRESHOLD):
        layer.record_execution(intent="debug", code=f"x{_}", outcome="runtime_error")
    layer.acknowledge_proposal()  # bump report count
    layer.reset_flailing()
    assert layer.consecutive_failures == 0
    assert layer.is_flailing() is False


def test_configure_limits_overrides_defaults():
    layer = _fresh_layer()
    result = layer.configure_limits(memory_mb=512, output_kb=64)
    assert result["memory_mb"] == 512
    assert result["output_kb"] == 64


def test_get_state_shape_consistent():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "making_state", "consecutive_failures", "is_flailing", "is_mastering",
        "mastery_score", "rumination_hashes", "intent_distribution",
        "execution_count", "last_dominant_failure_intent", "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), (
        f"missing keys: {expected - set(state.keys())}"
    )


def test_tick_with_execution_records_it():
    layer = _fresh_layer()
    out = layer.tick({
        "execution": {
            "intent": "compute",
            "code": "result = sum(range(100))",
            "outcome": "success",
            "duration_ms": 12,
        }
    })
    assert out["_fired_tick"] is True
    assert out["execution_count"] == 1
    assert layer.intent_state["compute"]["total"] == 1
    assert layer.intent_state["compute"]["success"] == 1


def test_blocked_outcome_does_not_count_as_success_or_failure():
    layer = _fresh_layer()
    layer.record_execution(intent="build", code="any code", outcome="blocked")
    # blocked is recorded in totals but not in success/failure bins
    assert layer.intent_state["build"]["total"] == 1
    assert layer.intent_state["build"]["success"] == 0
    assert layer.intent_state["build"]["failure"] == 0
    # And the success window doesn't get a vote.
    assert len(layer.success_window) == 0
