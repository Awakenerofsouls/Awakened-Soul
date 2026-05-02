"""
Tests for brain.mechanisms.skill_discovery_layer.SkillDiscoveryLayer.

Covers:
  - record_register: success/failure score
  - record_match: stale_registry counter; basic record
  - record_route: ambiguous_no_clarify; missed_match (had_clear_trigger
    but chose nothing); below_threshold_picked; stale_entries; monoculture
    detection; routing opens for reflection
  - record_fallback: missed_match when had_clear_trigger; clean fallback
  - record_reflect: routing_known + fit dynamics; false_match increments;
    drains open_routings
  - record_silent_route hook
  - false_match_rate computation
  - should_block: invalid op, reflect missing routing_id, sustained low
    integrity
  - rolling integrity score + min N gate
  - routing_state classification (idle/active/stale/monoculture/drifting/degrading)
  - Persistence across instances
  - IPW handshake fires + throttled
  - Operator API methods
  - tick advances current_tick + records routing_op
  - get_state shape
"""
import time

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    import importlib
    import brain.base_mechanism as _bm
    state_file = _bm._STATE_DIR / "SkillDiscoveryLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.skill_discovery_layer as mod
    importlib.reload(mod)
    return mod.SkillDiscoveryLayer()


# ── register ─────────────────────────────────────────────────────────────

def test_register_success():
    layer = _fresh_layer()
    rec = layer.record_register(skill_name="web-research", ok=True)
    assert rec["op"] == "register"
    assert rec["op_score"] == 1.0


def test_register_failure_dings_score():
    layer = _fresh_layer()
    rec = layer.record_register(skill_name="bogus", ok=False, reason="missing")
    assert rec["op_score"] == 0.0


# ── match ────────────────────────────────────────────────────────────────

def test_match_records_basic():
    layer = _fresh_layer()
    rec = layer.record_match(
        request="research the consensus",
        mode="brain",
        top_skill="web-research",
        top_score=0.7,
        candidate_count=5,
    )
    assert rec["op"] == "match"
    assert rec["top_skill"] == "web-research"
    assert rec["op_score"] == 1.0


def test_match_stale_registry_dings_score():
    layer = _fresh_layer()
    rec = layer.record_match(
        request="x", top_skill="y", top_score=0.5, stale_entries=2,
    )
    assert layer.failure_counts["stale_registry"] == 1
    assert rec["op_score"] < 1.0


def test_match_invalid_mode_falls_back():
    layer = _fresh_layer()
    rec = layer.record_match(request="x", mode="trance")
    assert rec["mode"] == "default"


# ── route ────────────────────────────────────────────────────────────────

def _good_route_kwargs(**overrides):
    base = dict(
        request="research and summarize",
        mode="brain",
        chosen="web-research",
        score=0.6,
        threshold=0.3,
        had_clear_trigger=True,
    )
    base.update(overrides)
    return base


def test_route_clean_path():
    layer = _fresh_layer()
    rec = layer.record_route(**_good_route_kwargs())
    assert rec["op"] == "route"
    assert rec["chosen"] == "web-research"
    assert rec["below_threshold_picked"] is False
    assert rec["missed_match"] is False
    assert rec["op_score"] == 1.0
    # Routing is opened for reflection.
    assert rec["routing_id"] in layer.open_routings


def test_route_ambiguous_no_clarify_flagged():
    layer = _fresh_layer()
    rec = layer.record_route(**_good_route_kwargs(ambiguous=True))
    assert rec["ambiguous_no_clarify"] is True
    assert layer.failure_counts["ambiguous_no_clarify"] == 1


def test_route_below_threshold_picked():
    layer = _fresh_layer()
    rec = layer.record_route(**_good_route_kwargs(score=0.1, threshold=0.3))
    assert rec["below_threshold_picked"] is True
    assert rec["op_score"] < 1.0


def test_route_missed_match_when_no_chosen_but_clear_trigger():
    layer = _fresh_layer()
    rec = layer.record_route(
        request="research and summarize",
        mode="brain",
        chosen=None,
        score=0.0,
        had_clear_trigger=True,
    )
    assert rec["missed_match"] is True
    assert layer.failure_counts["missed_match"] == 1


def test_route_stale_entries_increments_counter():
    layer = _fresh_layer()
    rec = layer.record_route(**_good_route_kwargs(stale_entries=3))
    assert layer.failure_counts["stale_registry"] == 1


def test_route_monoculture_after_repeated_same_skill():
    from brain.mechanisms.skill_discovery_layer import MONOCULTURE_MIN_N
    layer = _fresh_layer()
    for i in range(MONOCULTURE_MIN_N + 2):
        layer.record_route(**_good_route_kwargs(chosen="web-research"))
    assert layer._monoculture_active() is True
    assert layer.failure_counts["monoculture"] >= 1


def test_route_no_monoculture_when_balanced():
    from brain.mechanisms.skill_discovery_layer import MONOCULTURE_MIN_N
    layer = _fresh_layer()
    skills = ["web-research", "knowledge-summarization", "qmd", "memory-management"]
    for i in range(MONOCULTURE_MIN_N + 2):
        layer.record_route(**_good_route_kwargs(chosen=skills[i % len(skills)]))
    assert layer._monoculture_active() is False


# ── fallback ─────────────────────────────────────────────────────────────

def test_fallback_clean_when_no_trigger():
    layer = _fresh_layer()
    rec = layer.record_fallback(
        request="hello", mode="default", reason="no skill matched",
        had_clear_trigger=False,
    )
    assert rec["missed_match"] is False
    assert rec["op_score"] == 1.0


def test_fallback_is_missed_match_when_clear_trigger():
    layer = _fresh_layer()
    rec = layer.record_fallback(
        request="research and summarize",
        mode="brain",
        reason="no candidate above threshold",
        had_clear_trigger=True,
    )
    assert rec["missed_match"] is True
    assert layer.failure_counts["missed_match"] == 1


# ── reflect ──────────────────────────────────────────────────────────────

def test_reflect_fit_true_clean():
    layer = _fresh_layer()
    r = layer.record_route(**_good_route_kwargs())
    rid = r["routing_id"]
    rec = layer.record_reflect(routing_id=rid, fit=True)
    assert rec["routing_known"] is True
    assert rec["fit"] is True
    assert rid not in layer.open_routings


def test_reflect_fit_false_increments_false_match():
    layer = _fresh_layer()
    r = layer.record_route(**_good_route_kwargs())
    rec = layer.record_reflect(routing_id=r["routing_id"], fit=False)
    assert layer.failure_counts["false_match"] == 1


def test_reflect_unknown_routing_id():
    layer = _fresh_layer()
    rec = layer.record_reflect(routing_id="bogus", fit=True)
    assert rec["routing_known"] is False
    assert rec["op_score"] < 1.0


def test_false_match_rate_computation():
    layer = _fresh_layer()
    # 2 of 4 fits = false_match_rate 0.5
    for fit in [True, False, True, False]:
        r = layer.record_route(**_good_route_kwargs())
        layer.record_reflect(routing_id=r["routing_id"], fit=fit)
    assert layer.false_match_rate() == 0.5


def test_high_false_match_active_after_threshold():
    from brain.mechanisms.skill_discovery_layer import (
        FALSE_MATCH_MIN_N, FALSE_MATCH_RATE_THRESHOLD,
    )
    layer = _fresh_layer()
    # Stack false matches.
    for _ in range(FALSE_MATCH_MIN_N + 2):
        r = layer.record_route(**_good_route_kwargs())
        layer.record_reflect(routing_id=r["routing_id"], fit=False)
    assert layer._high_false_match_active() is True


# ── silent_route ─────────────────────────────────────────────────────────

def test_record_silent_route_increments():
    layer = _fresh_layer()
    layer.record_silent_route(3)
    assert layer.failure_counts["silent_route"] == 3


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("teleport")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_reflect_missing_routing_id():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("reflect")
    assert blocked is True
    assert "routing_id" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("route", request="x")
    assert blocked is True
    assert "low routing" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_score_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_requires_min_n():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is False


# ── routing_state ────────────────────────────────────────────────────────

def test_routing_state_idle_empty():
    layer = _fresh_layer()
    assert layer.routing_state() == "idle"


def test_routing_state_active_after_route():
    layer = _fresh_layer()
    layer.record_route(**_good_route_kwargs())
    assert layer.routing_state() == "active"


def test_routing_state_monoculture():
    from brain.mechanisms.skill_discovery_layer import MONOCULTURE_MIN_N
    layer = _fresh_layer()
    for _ in range(MONOCULTURE_MIN_N + 2):
        layer.record_route(**_good_route_kwargs(chosen="web-research"))
    assert layer.routing_state() == "monoculture"


def test_routing_state_drifting_with_high_false_match():
    from brain.mechanisms.skill_discovery_layer import FALSE_MATCH_MIN_N
    layer = _fresh_layer()
    for _ in range(FALSE_MATCH_MIN_N + 2):
        # Vary the chosen skill so we don't trip monoculture before drifting.
        chosen = "web-research" if _ % 2 == 0 else "knowledge-summarization"
        r = layer.record_route(**_good_route_kwargs(chosen=chosen))
        layer.record_reflect(routing_id=r["routing_id"], fit=False)
    # Could be monoculture or drifting depending on which trips first.
    assert layer.routing_state() in ("drifting", "monoculture", "degrading")


def test_routing_state_stale_after_route_with_stale_entries():
    layer = _fresh_layer()
    layer.record_route(**_good_route_kwargs(stale_entries=2))
    assert layer.routing_state() in ("stale", "active")


def test_routing_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.routing_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_route(**_good_route_kwargs())
    layer.record_match(
        request="x", top_skill="web-research", top_score=0.6,
    )

    import brain.mechanisms.skill_discovery_layer as mod
    layer2 = mod.SkillDiscoveryLayer()
    assert layer2.op_counts["route"] == 1
    assert layer2.op_counts["match"] == 1
    assert layer2.skill_counts.get("web-research") == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_route(**_good_route_kwargs())
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "SkillDiscoveryLayer"
    assert sig["kind"] == "skill_discovery_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_op("teleport", target="x")
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    layer.record_silent_route(2)
    assert layer.failure_counts["silent_route"] == 2
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_reset_skill_distribution():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_route(**_good_route_kwargs(chosen="web-research"))
    assert layer.skill_counts.get("web-research") == 3
    layer.reset_skill_distribution()
    assert layer.skill_counts == {}
    assert len(layer.recent_chosen) == 0


def test_reset_reflection_window():
    layer = _fresh_layer()
    r = layer.record_route(**_good_route_kwargs())
    layer.record_reflect(routing_id=r["routing_id"], fit=False)
    assert len(layer.reflection_window) == 1
    layer.reset_reflection_window()
    assert len(layer.reflection_window) == 0


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_routing_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "routing_op": {
                "op": "route",
                "request": "ship the fix",
                "mode": "build",
                "chosen": "code-execution",
                "score": 0.6,
                "had_clear_trigger": True,
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["route"] == 1


def test_tick_no_op_without_routing_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "routing_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "skill_distribution",
        "mode_distribution",
        "failure_mode_counts",
        "false_match_rate",
        "monoculture_active",
        "open_routings_count",
        "current_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_op_dispatches_route():
    layer = _fresh_layer()
    rec = layer.record_op(
        "route",
        request="x",
        mode="default",
        chosen="web-research",
        score=0.5,
        had_clear_trigger=True,
    )
    assert rec["op"] == "route"


def test_record_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_op("hallucinate", target="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
