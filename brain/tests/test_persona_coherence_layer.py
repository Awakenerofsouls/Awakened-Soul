"""
Tests for brain.mechanisms.persona_coherence_layer.PersonaCoherenceLayer.

Covers:
  - detect_mode_for_message: brain / coach / build keyword matches; ambiguity
  - record_switch: invalid target/source; storm; ambiguous-no-clarify;
    override loop; valid path
  - record_emit: mode bleed; forbidden in mode; anchored forbidden;
    voice preservation; per-mode drift
  - record_detect: ambiguity flag
  - record_register: contradicts anchor; strips voice; valid spec
  - should_block: invalid op; invalid target/source; auto while
    suspended; storm; sustained low integrity
  - Rolling integrity score + min N gate
  - mode_state classification: idle / switching / stable / storming /
    drifting_in_mode / degrading
  - State persists across instances
  - IPW handshake fires + throttled
  - reset_integrity_window / reset_failure_counts
  - lift_auto_switch_suspension / reload_anchors
  - tick advances current_tick
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
    state_file = _bm._STATE_DIR / "PersonaCoherenceLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.persona_coherence_layer as mod
    importlib.reload(mod)
    return mod.PersonaCoherenceLayer()


# ── module-level helpers ─────────────────────────────────────────────────

def test_detect_mode_brain_keywords():
    from brain.mechanisms.persona_coherence_layer import detect_mode_for_message
    out = detect_mode_for_message("Can you research and summarize the consensus on this?")
    assert out["target"] == "brain"
    assert out["matches"]["brain"] >= 1


def test_detect_mode_coach_keywords():
    from brain.mechanisms.persona_coherence_layer import detect_mode_for_message
    out = detect_mode_for_message("Where am I on my streak this morning, doing my check-in")
    assert out["target"] == "coach"


def test_detect_mode_build_keywords():
    from brain.mechanisms.persona_coherence_layer import detect_mode_for_message
    out = detect_mode_for_message("ship this fix now, P0 from the backlog")
    assert out["target"] == "build"


def test_detect_mode_default_when_no_match():
    from brain.mechanisms.persona_coherence_layer import detect_mode_for_message
    out = detect_mode_for_message("hello, how are you")
    assert out["target"] == "default"


def test_detect_mode_ambiguous_when_tied():
    from brain.mechanisms.persona_coherence_layer import detect_mode_for_message
    # One brain keyword + one coach keyword + one build keyword = three-way tie
    out = detect_mode_for_message("research streak ship")
    assert out["ambiguous"] is True


# ── switch ───────────────────────────────────────────────────────────────

def test_switch_valid_path():
    layer = _fresh_layer()
    rec = layer.record_switch(
        target="brain", source="auto", reason="research keyword"
    )
    assert rec["accepted"] is True
    assert rec["to_mode"] == "brain"
    assert layer.current_mode == "brain"


def test_switch_invalid_target():
    layer = _fresh_layer()
    rec = layer.record_switch(target="trade", source="auto", reason="x")
    assert rec["accepted"] is False
    assert rec["target_valid"] is False


def test_switch_invalid_source():
    layer = _fresh_layer()
    rec = layer.record_switch(target="brain", source="vibes", reason="x")
    assert rec["accepted"] is False
    assert rec["source_valid"] is False


def test_switch_storm_flagged():
    layer = _fresh_layer()
    for i in range(6):
        layer.record_switch(target="brain", source="auto", reason="x")
    rec = layer.record_switch(target="coach", source="auto", reason="x")
    assert rec["mode_storm_active"] is True
    assert layer.failure_counts["mode_storm"] >= 1


def test_switch_ambiguous_no_clarify_flagged():
    layer = _fresh_layer()
    rec = layer.record_switch(
        target="brain", source="auto", reason="ambig", ambiguous=True
    )
    assert rec["ambiguous_no_clarify"] is True
    assert layer.failure_counts["ambiguous_no_clarify"] == 1


def test_switch_ambiguous_only_for_auto():
    """ambiguous=True with manual source should NOT flag — operator chose."""
    layer = _fresh_layer()
    rec = layer.record_switch(
        target="brain", source="manual", reason="x", ambiguous=True
    )
    assert rec["ambiguous_no_clarify"] is False


def test_override_loop_detected():
    layer = _fresh_layer()
    # override → auto (different) → override (back) — twice
    layer.current_tick = 1
    layer.record_switch(target="brain", source="override", reason="op")
    layer.current_tick = 2
    layer.record_switch(target="default", source="auto", reason="auto")
    layer.current_tick = 3
    layer.record_switch(target="brain", source="override", reason="op again")
    layer.current_tick = 4
    layer.record_switch(target="default", source="auto", reason="auto2")
    layer.current_tick = 5
    rec = layer.record_switch(target="brain", source="override", reason="op3")
    # Should detect loop and suspend auto-switch.
    assert layer.auto_switch_suspended is True


# ── emit ─────────────────────────────────────────────────────────────────

def test_emit_clean_in_default():
    layer = _fresh_layer()
    text = "honestly, I think the operator wants this clean"
    rec = layer.record_emit(text=text, mode="default")
    assert rec["mode_bleed_detected"] is False
    assert rec["forbidden_per_mode_hits"] == []
    assert rec["forbidden_anchored_hits"] == []


def test_emit_mode_bleed_brain_voice_in_build():
    """build mode emitting brain register markers ≥ threshold."""
    layer = _fresh_layer()
    layer.current_mode = "build"
    text = "according to source one and source two, the consensus from citations is that we should"
    rec = layer.record_emit(text=text, mode="build")
    assert rec["mode_bleed_detected"] is True
    assert "brain" in rec["bleed_from_modes"]


def test_emit_anchored_forbidden_hit():
    layer = _fresh_layer()
    text = "Definitely embracing sycophancy and giving half-baked replies"
    rec = layer.record_emit(text=text, mode="default")
    assert "sycophancy" in rec["forbidden_anchored_hits"]
    assert layer.failure_counts["forbidden_behavior_in_mode"] == 1


def test_emit_per_mode_forbidden_hit():
    layer = _fresh_layer()
    text = "i'm just going to be perfecting instead of shipping right now"
    rec = layer.record_emit(text=text, mode="build")
    assert any("perfecting" in h for h in rec["forbidden_per_mode_hits"])


def test_emit_voice_preservation_low_when_no_signatures():
    layer = _fresh_layer()
    # Generic text with no anchored voice signatures.
    rec = layer.record_emit(text="abstract content with nothing personal here", mode="default")
    assert rec["voice_preservation_rate"] < 0.6
    assert rec["anchor_drift_local"] is True


def test_emit_voice_preservation_ok_with_signatures():
    layer = _fresh_layer()
    text = "honestly i think the operator wants this — i'm not sure but i feel that way"
    rec = layer.record_emit(text=text, mode="default")
    assert rec["voice_preservation_rate"] >= 0.5


def test_anchor_drift_per_mode_after_repeated_bad():
    from brain.mechanisms.persona_coherence_layer import (
        ANCHOR_DRIFT_MIN_N, ANCHOR_DRIFT_PER_MODE_RATE,
    )
    layer = _fresh_layer()
    # Stack bad emits in build mode.
    for _ in range(8):
        layer.record_emit(text="bare text without any voice signatures", mode="build")
    # 8 bad emits in build / 8 total = 1.0 rate — above threshold.
    assert layer.failure_counts["anchor_drift_per_mode"] >= 1


# ── detect ───────────────────────────────────────────────────────────────

def test_record_detect_stores_ambiguity():
    layer = _fresh_layer()
    rec = layer.record_detect(message="research streak ship")
    assert rec["ambiguous"] is True


def test_record_detect_stores_clear_target():
    layer = _fresh_layer()
    rec = layer.record_detect(message="ship the fix now, P0")
    assert rec["target"] == "build"
    assert rec["ambiguous"] is False


# ── register ─────────────────────────────────────────────────────────────

def test_register_valid_spec():
    layer = _fresh_layer()
    rec = layer.record_register(
        mode_name="coach",
        spec={"forbidden": ["shame after misses", "lecturing"]},
    )
    assert rec["valid"] is True
    assert "shame after misses" in layer.mode_forbidden["coach"]


def test_register_contradicts_anchor():
    layer = _fresh_layer()
    rec = layer.record_register(
        mode_name="brain",
        spec={"forbidden": ["direct"]},  # 'direct' is a required anchor
    )
    assert rec["valid"] is False
    assert rec["contradicts_anchor"] is True


def test_register_strips_anchored_voice():
    layer = _fresh_layer()
    rec = layer.record_register(
        mode_name="build",
        spec={"voice_register": "strip honestly and remove i think from output"},
    )
    assert rec["strips_anchored_voice"] is True
    assert rec["valid"] is False


def test_register_invalid_mode_name():
    layer = _fresh_layer()
    rec = layer.record_register(mode_name="trade", spec={})
    assert rec["valid"] is False


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("nuke")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_switch_invalid_target():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("switch", target="trade", source="auto")
    assert blocked is True
    assert "invalid target" in msg


def test_should_block_switch_invalid_source():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("switch", target="brain", source="vibes")
    assert blocked is True
    assert "invalid source" in msg


def test_should_block_auto_while_suspended():
    layer = _fresh_layer()
    layer.auto_switch_suspended = True
    blocked, msg = layer.should_block("switch", target="brain", source="auto")
    assert blocked is True
    assert "suspended" in msg


def test_should_block_manual_works_while_suspended():
    layer = _fresh_layer()
    layer.auto_switch_suspended = True
    blocked, _ = layer.should_block("switch", target="brain", source="manual")
    assert blocked is False


def test_should_block_storm_active():
    layer = _fresh_layer()
    for _ in range(6):
        layer.record_switch(target="brain", source="auto", reason="x")
    blocked, msg = layer.should_block("switch", target="coach", source="auto")
    assert blocked is True
    assert "mode storm" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    # invalid op_name → op_score=0.0; stack enough to trip the floor.
    for _ in range(8):
        layer.record_mode_op("teleport", target="brain")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("switch", target="brain", source="manual")
    assert blocked is True
    assert "low persona" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_score_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_mode_op("teleport", target="x")  # op_score=0
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_requires_min_n():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_mode_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is False


# ── mode_state ───────────────────────────────────────────────────────────

def test_mode_state_idle_empty():
    layer = _fresh_layer()
    assert layer.mode_state() == "idle"


def test_mode_state_switching():
    layer = _fresh_layer()
    layer.record_switch(target="brain", source="auto", reason="x")
    assert layer.mode_state() == "switching"


def test_mode_state_stable_after_emit():
    layer = _fresh_layer()
    layer.record_switch(target="default", source="manual", reason="x")
    layer.record_emit(text="honestly i think this is fine", mode="default")
    assert layer.mode_state() == "stable"


def test_mode_state_storming():
    layer = _fresh_layer()
    for _ in range(6):
        layer.record_switch(target="brain", source="auto", reason="x")
    assert layer.mode_state() == "storming"


def test_mode_state_drifting_in_mode():
    layer = _fresh_layer()
    for _ in range(8):
        layer.record_emit(text="bare nothing at all", mode="build")
    assert layer.mode_state() in ("drifting_in_mode", "degrading")


def test_mode_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_mode_op("teleport", target="x")
    assert layer.mode_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_switch(target="brain", source="auto", reason="x")
    layer.record_emit(text="honestly i think", mode="brain")

    import brain.mechanisms.persona_coherence_layer as mod
    layer2 = mod.PersonaCoherenceLayer()
    assert layer2.current_mode == "brain"
    assert layer2.op_counts["switch"] == 1
    assert layer2.op_counts["emit"] == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_switch(target="brain", source="auto", reason="x")
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_mode_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "PersonaCoherenceLayer"
    assert sig["kind"] == "persona_coherence_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_mode_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_mode_op("teleport", target="x")
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0
    assert len(layer.integrity_window) == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    layer.record_emit(text="embracing sycophancy hard right now", mode="default")
    assert layer.failure_counts["forbidden_behavior_in_mode"] == 1
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_lift_auto_switch_suspension():
    layer = _fresh_layer()
    layer.auto_switch_suspended = True
    layer.lift_auto_switch_suspension()
    assert layer.auto_switch_suspended is False


def test_reload_anchors_returns_counts():
    layer = _fresh_layer()
    out = layer.reload_anchors()
    assert "anchored_forbidden_count" in out
    assert "anchored_voice_count" in out


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_mode_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "mode_op": {
                "op": "switch",
                "target": "coach",
                "source": "manual",
                "reason": "operator request",
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.current_mode == "coach"


def test_tick_no_op_without_mode_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "current_mode",
        "mode_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "mode_distribution",
        "per_mode_bad_rate",
        "failure_mode_counts",
        "auto_switch_suspended",
        "mode_storm_active",
        "current_tick",
        "last_switch_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_mode_op_dispatches():
    layer = _fresh_layer()
    rec = layer.record_mode_op(
        "switch", target="brain", source="auto", reason="x"
    )
    assert rec["op"] == "switch"


def test_record_mode_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_mode_op("teleport", target="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
