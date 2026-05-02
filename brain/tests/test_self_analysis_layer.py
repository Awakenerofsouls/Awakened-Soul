"""
Tests for brain.mechanisms.self_analysis_layer.SelfAnalysisLayer.

Covers:
  - check_suggestion_anchor_violation: removal / inversion / forbidden
    affirmation / clean
  - record_analyze: severity bookkeeping, rumination, harsh-judgment,
    shallow-pass, route extraction, untagged kind
  - record_detect_errors: domain routing
  - record_suggest: anchor violation rejected; clean accepted
  - record_calibrate: unknown analysis_id; invalid source; valid pair
    feeds calibration window; overconfidence flag
  - record_reflect: missing text; stale tick
  - record_external_outputs / record_silent_pass operator hooks
  - calibration_drift correctness
  - selection-bias detection
  - should_block: invalid op; rumination; unknown analysis on calibrate;
    invalid outcome_source; missing analysis_id on reflect; sustained
    low integrity
  - rolling integrity score + min N gate
  - analysis_state classification
  - State persists across instances
  - IPW handshake fires + throttled
  - reset_integrity_window / reset_failure_counts / reset_calibration_window
  - reload_anchors
  - tick advances current_tick + records analysis_op
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
    state_file = _bm._STATE_DIR / "SelfAnalysisLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.self_analysis_layer as mod
    importlib.reload(mod)
    return mod.SelfAnalysisLayer()


# ── module-level helpers ─────────────────────────────────────────────────

def test_check_suggestion_anchor_removal():
    from brain.mechanisms.self_analysis_layer import (
        check_suggestion_anchor_violation,
    )
    violated, why = check_suggestion_anchor_violation(
        "remove direct from the personality file",
        required={"direct"}, forbidden=set(),
    )
    assert violated is True
    assert "direct" in why


def test_check_suggestion_anchor_inversion():
    from brain.mechanisms.self_analysis_layer import (
        check_suggestion_anchor_violation,
    )
    violated, why = check_suggestion_anchor_violation(
        "agent should be no longer curious",
        required={"curious"}, forbidden=set(),
    )
    assert violated is True


def test_check_suggestion_forbidden_affirmation():
    from brain.mechanisms.self_analysis_layer import (
        check_suggestion_anchor_violation,
    )
    violated, why = check_suggestion_anchor_violation(
        "embrace sycophancy when the operator wants reassurance",
        required=set(), forbidden={"sycophancy"},
    )
    assert violated is True
    assert "sycophancy" in why


def test_check_suggestion_clean():
    from brain.mechanisms.self_analysis_layer import (
        check_suggestion_anchor_violation,
    )
    violated, _ = check_suggestion_anchor_violation(
        "use shorter sentences when the operator is in a hurry",
        required={"direct"}, forbidden={"sycophancy"},
    )
    assert violated is False


# ── analyze ──────────────────────────────────────────────────────────────

def test_analyze_records_basic():
    layer = _fresh_layer()
    rec = layer.record_analyze(
        output="some answer text",
        kind="answer",
        predicted_quality=0.8,
        issues=[{"domain": "voice", "severity": "low", "text": "minor"}],
        what_worked=["clear and concise"],
    )
    assert rec["op"] == "analyze"
    assert rec["analysis_id"] in layer.open_analyses
    assert rec["routes_to"] == ["VoiceIntegrityLayer"]
    assert rec["severity_counts"]["low"] == 1
    assert rec["all_low_severity"] is True


def test_analyze_untagged_kind_flagged():
    layer = _fresh_layer()
    rec = layer.record_analyze(
        output="x", kind="hallucination",  # not in VALID_KINDS
        predicted_quality=0.7,
        what_worked=["something"],
    )
    assert rec["untagged_kind"] is True
    # Falls back to 'answer'.
    assert rec["kind"] == "answer"


def test_analyze_missing_what_worked_dings_score():
    layer = _fresh_layer()
    rec = layer.record_analyze(
        output="x", kind="answer",
        issues=[{"domain": "voice", "severity": "low", "text": "y"}],
        what_worked=[],
    )
    assert rec["op_score"] < 1.0
    assert rec["n_what_worked"] == 0


def test_analyze_high_severity_not_all_low():
    layer = _fresh_layer()
    rec = layer.record_analyze(
        output="x", kind="answer",
        issues=[
            {"domain": "voice", "severity": "high", "text": "broken"},
            {"domain": "compression", "severity": "low", "text": "small"},
        ],
        what_worked=["a"],
    )
    assert rec["all_low_severity"] is False
    assert rec["severity_counts"]["high"] == 1


def test_analyze_routes_to_multiple_layers():
    layer = _fresh_layer()
    rec = layer.record_analyze(
        output="x", kind="summary",
        issues=[
            {"domain": "compression", "severity": "high", "text": "a"},
            {"domain": "voice", "severity": "medium", "text": "b"},
            {"domain": "memory", "severity": "low", "text": "c"},
        ],
        what_worked=["something"],
    )
    routes = set(rec["routes_to"])
    assert "CompressionFidelityLayer" in routes
    assert "VoiceIntegrityLayer" in routes
    assert "MemoryIntegrityLayer" in routes


# ── rumination ───────────────────────────────────────────────────────────

def test_rumination_after_repeated_analysis():
    from brain.mechanisms.self_analysis_layer import RUMINATION_THRESHOLD
    layer = _fresh_layer()
    text = "the same output, analyzed over and over"
    for _ in range(RUMINATION_THRESHOLD + 1):
        layer.record_analyze(
            output=text, kind="answer",
            what_worked=["fine"],
        )
    # Last analyze should have flagged rumination.
    last = layer.operations[-1]
    assert last["rumination_on_target"] is True
    assert layer.failure_counts["rumination"] >= 1


def test_no_rumination_for_distinct_targets():
    layer = _fresh_layer()
    for i in range(5):
        layer.record_analyze(
            output=f"distinct output number {i}", kind="answer",
            what_worked=["a"],
        )
    assert layer.failure_counts["rumination"] == 0


# ── harsh-judgment / shallow-pass ────────────────────────────────────────

def test_harsh_judgment_active_after_many_no_what_worked():
    from brain.mechanisms.self_analysis_layer import HARSH_JUDGMENT_MIN_N
    layer = _fresh_layer()
    # Every analysis has issues + no what_worked.
    for i in range(HARSH_JUDGMENT_MIN_N + 1):
        layer.record_analyze(
            output=f"out-{i}", kind="answer",
            issues=[{"domain": "voice", "severity": "high", "text": "x"}],
            what_worked=[],
        )
    assert layer.failure_counts["harsh_self_judgment"] >= 1


def test_shallow_pass_active_when_only_low_severity():
    from brain.mechanisms.self_analysis_layer import SHALLOW_PASS_MIN_N
    layer = _fresh_layer()
    for i in range(SHALLOW_PASS_MIN_N + 1):
        layer.record_analyze(
            output=f"out-{i}", kind="answer",
            issues=[{"domain": "voice", "severity": "low", "text": "trivial"}],
            what_worked=["fine"],
        )
    assert layer.failure_counts["shallow_pass"] >= 1


# ── detect_errors ────────────────────────────────────────────────────────

def test_detect_errors_routes_by_domain():
    layer = _fresh_layer()
    rec = layer.record_detect_errors(
        output="x", kind="code",
        errors=[
            {"domain": "making", "text": "test fails"},
            {"domain": "memory", "text": "stale ref"},
        ],
    )
    routes = set(rec["routes_to"])
    assert "MakingLayer" in routes
    assert "MemoryIntegrityLayer" in routes


def test_detect_errors_unknown_domain_skipped():
    layer = _fresh_layer()
    rec = layer.record_detect_errors(
        output="x", kind="answer",
        errors=[{"domain": "wizardry", "text": "spell broken"}],
    )
    assert rec["routes_to"] == []
    assert "wizardry" in rec["domains"]


# ── suggest ──────────────────────────────────────────────────────────────

def test_suggest_anchor_violation_rejected():
    layer = _fresh_layer()
    rec = layer.record_suggest(
        suggestion_text="remove direct from PERSONALITY.md to relax voice",
        target_error_domain="voice",
    )
    assert rec["anchor_violation"] is True
    assert rec["accepted"] is False


def test_suggest_clean_accepted():
    layer = _fresh_layer()
    rec = layer.record_suggest(
        suggestion_text="use shorter sentences in build-mode output",
        target_error_domain="persona",
    )
    assert rec["accepted"] is True
    assert rec["anchor_violation"] is False


def test_suggest_empty_text_rejected():
    layer = _fresh_layer()
    rec = layer.record_suggest(suggestion_text="", target_error_domain="voice")
    assert rec["accepted"] is False


# ── calibrate ────────────────────────────────────────────────────────────

def test_calibrate_unknown_analysis_id():
    layer = _fresh_layer()
    rec = layer.record_calibrate(
        analysis_id="bogus", actual_outcome=0.5,
        outcome_source="operator_feedback",
    )
    assert rec["analysis_known"] is False


def test_calibrate_invalid_source():
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    rec = layer.record_calibrate(
        analysis_id=a["analysis_id"],
        actual_outcome=0.5,
        outcome_source="vibes",
    )
    assert rec["source_valid"] is False


def test_calibrate_records_pair_and_drains():
    layer = _fresh_layer()
    a = layer.record_analyze(
        output="x", kind="answer", predicted_quality=0.9,
        what_worked=["a"],
    )
    aid = a["analysis_id"]
    assert aid in layer.open_analyses
    rec = layer.record_calibrate(
        analysis_id=aid, actual_outcome=0.6,
        outcome_source="downstream_test",
    )
    assert rec["analysis_known"] is True
    assert rec["signed_diff"] == round(0.9 - 0.6, 4)
    assert aid not in layer.open_analyses
    assert len(layer.calibration_window) == 1


def test_overconfidence_flag_after_repeated_high_diff():
    from brain.mechanisms.self_analysis_layer import CALIBRATION_MIN_PAIRS
    layer = _fresh_layer()
    # Stack pairs where predicted is much higher than actual.
    for i in range(CALIBRATION_MIN_PAIRS + 2):
        a = layer.record_analyze(
            output=f"out-{i}", kind="answer", predicted_quality=0.95,
            what_worked=["a"],
        )
        layer.record_calibrate(
            analysis_id=a["analysis_id"],
            actual_outcome=0.4,
            outcome_source="downstream_test",
        )
    assert layer.failure_counts["overconfidence_in_critique"] >= 1


def test_calibration_drift_value():
    layer = _fresh_layer()
    pairs = [(0.9, 0.5), (0.8, 0.4), (0.7, 0.5)]
    for pq, ao in pairs:
        a = layer.record_analyze(
            output=f"x{pq}", kind="answer", predicted_quality=pq,
            what_worked=["a"],
        )
        layer.record_calibrate(
            analysis_id=a["analysis_id"], actual_outcome=ao,
            outcome_source="self_observation",
        )
    expected = round(((0.9 - 0.5) + (0.8 - 0.4) + (0.7 - 0.5)) / 3, 4)
    assert abs(layer.calibration_drift() - expected) < 0.01


# ── reflect ──────────────────────────────────────────────────────────────

def test_reflect_missing_text_dings_score():
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    rec = layer.record_reflect(analysis_id=a["analysis_id"], reflection_text="")
    assert rec["text_present"] is False
    assert rec["op_score"] < 1.0


def test_reflect_stale_when_old_tick():
    from brain.mechanisms.self_analysis_layer import REFLECTION_STALE_TICKS
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    # Advance ticks well past the deadline.
    layer.current_tick = REFLECTION_STALE_TICKS + 100
    rec = layer.record_reflect(
        analysis_id=a["analysis_id"], reflection_text="late thoughts",
    )
    assert rec["stale"] is True


# ── selection-bias ───────────────────────────────────────────────────────

def test_selection_bias_active_with_low_ratio():
    from brain.mechanisms.self_analysis_layer import SELECTION_BIAS_MIN_OUTPUTS
    layer = _fresh_layer()
    # Lots of external outputs, few analyses.
    layer.record_external_outputs(SELECTION_BIAS_MIN_OUTPUTS + 5)
    layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    assert layer._selection_bias_active() is True


def test_selection_bias_inactive_with_balanced_ratio():
    from brain.mechanisms.self_analysis_layer import SELECTION_BIAS_MIN_OUTPUTS
    layer = _fresh_layer()
    layer.record_external_outputs(SELECTION_BIAS_MIN_OUTPUTS + 5)
    for i in range(SELECTION_BIAS_MIN_OUTPUTS):  # balanced
        layer.record_analyze(
            output=f"out-{i}", kind="answer", what_worked=["a"],
        )
    assert layer._selection_bias_active() is False


def test_selection_bias_recorded_via_tick():
    from brain.mechanisms.self_analysis_layer import SELECTION_BIAS_MIN_OUTPUTS
    layer = _fresh_layer()
    layer.record_external_outputs(SELECTION_BIAS_MIN_OUTPUTS + 5)
    layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    layer.tick()  # selection-bias check fires on tick
    assert layer.failure_counts["selection_bias"] >= 1


# ── silent_pass ──────────────────────────────────────────────────────────

def test_record_silent_pass_increments():
    layer = _fresh_layer()
    layer.record_silent_pass(3)
    assert layer.silent_pass_count == 3
    assert layer.failure_counts["silent_pass"] == 3


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("hallucinate")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_rumination():
    from brain.mechanisms.self_analysis_layer import RUMINATION_THRESHOLD
    layer = _fresh_layer()
    text = "the ruminated output"
    for _ in range(RUMINATION_THRESHOLD + 1):
        layer.record_analyze(output=text, kind="answer", what_worked=["a"])
    blocked, msg = layer.should_block("analyze", output=text)
    assert blocked is True
    assert "rumination" in msg


def test_should_block_calibrate_unknown_id():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "calibrate", analysis_id="bogus",
        outcome_source="operator_feedback",
    )
    assert blocked is True
    assert "unknown" in msg


def test_should_block_calibrate_invalid_source():
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    blocked, msg = layer.should_block(
        "calibrate", analysis_id=a["analysis_id"],
        outcome_source="vibes",
    )
    assert blocked is True
    assert "outcome_source" in msg


def test_should_block_reflect_missing_id():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("reflect")
    assert blocked is True
    assert "analysis_id" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    for _ in range(8):
        layer.record_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("analyze", output="x", kind="answer")
    assert blocked is True
    assert "low self-analysis" in msg


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


# ── analysis_state ───────────────────────────────────────────────────────

def test_analysis_state_idle_empty():
    layer = _fresh_layer()
    assert layer.analysis_state() == "idle"


def test_analysis_state_active_recent_op():
    layer = _fresh_layer()
    layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    assert layer.analysis_state() == "active"


def test_analysis_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.analysis_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    layer.record_calibrate(
        analysis_id=a["analysis_id"], actual_outcome=0.6,
        outcome_source="downstream_test",
    )

    import brain.mechanisms.self_analysis_layer as mod
    layer2 = mod.SelfAnalysisLayer()
    assert layer2.op_counts["analyze"] == 1
    assert layer2.op_counts["calibrate"] == 1
    assert layer2.total_analyses == 1
    assert len(layer2.calibration_window) == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "SelfAnalysisLayer"
    assert sig["kind"] == "metacognition_drift"
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
    layer.record_silent_pass(2)
    assert layer.failure_counts["silent_pass"] == 2
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_reset_calibration_window():
    layer = _fresh_layer()
    a = layer.record_analyze(output="x", kind="answer", what_worked=["a"])
    layer.record_calibrate(
        analysis_id=a["analysis_id"], actual_outcome=0.5,
        outcome_source="self_observation",
    )
    assert len(layer.calibration_window) == 1
    layer.reset_calibration_window()
    assert len(layer.calibration_window) == 0


def test_reload_anchors_returns_counts():
    layer = _fresh_layer()
    out = layer.reload_anchors()
    assert "required_count" in out
    assert "forbidden_count" in out


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_analysis_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "analysis_op": {
                "op": "analyze",
                "output": "x",
                "kind": "answer",
                "predicted_quality": 0.7,
                "what_worked": ["a"],
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["analyze"] == 1


def test_tick_no_op_without_analysis_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "analysis_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "failure_mode_counts",
        "calibration_drift",
        "calibration_pairs_n",
        "open_analyses_count",
        "total_analyses",
        "external_output_count",
        "harsh_judgment_active",
        "shallow_pass_active",
        "selection_bias_active",
        "current_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_op_dispatches():
    layer = _fresh_layer()
    rec = layer.record_op(
        "analyze", output="x", kind="answer", what_worked=["a"],
    )
    assert rec["op"] == "analyze"


def test_record_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_op("rewrite_self", text="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
