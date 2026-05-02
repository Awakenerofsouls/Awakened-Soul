"""
Tests for brain.mechanisms.inference_integrity_layer.InferenceIntegrityLayer.

Covers:
  - Empty tick is a safe no-op
  - record_analysis updates intent_state and stores analysis
  - Untagged analysis is recorded but not credited to valid intents
  - Confidence-vs-sample heuristic flags overconfidence
  - Different intents have different confidence budgets (predict stricter than describe)
  - should_block: invalid intent, low-n predict, high-confidence-low-n, single-hypothesis-streak
  - Single hypothesis streak detected on N analyses with same hypothesis + no alternatives
  - Streak NOT triggered if alternatives are considered
  - Shrinking samples detected on downward trend
  - record_outcome updates calibration window
  - calibration_score requires CALIBRATION_MIN_N samples to be meaningful
  - Miscalibration detected when claimed_confidence consistently ≠ hit_rate
  - inference_state classification (idle / inferring / well_calibrated / overconfident / miscalibrated)
  - State persists across instances
  - IPW handshake throttle
  - reset_calibration clears state
  - get_state shape consistent
  - tick with analysis dict + analysis_outcome dict

Same isolation pattern as test_outward_reach_layer / test_making_layer.
"""
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Fresh AGENT_HOME + per-test state dir."""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    import importlib
    import brain.mechanisms.inference_integrity_layer as mod
    importlib.reload(mod)
    return mod.InferenceIntegrityLayer()


def test_empty_tick_is_noop():
    layer = _fresh_layer()
    out = layer.tick({})
    assert out["_fired_tick"] is False
    assert out["analysis_count"] == 0
    assert out["inference_state"] == "idle"


def test_record_analysis_basic():
    layer = _fresh_layer()
    rec = layer.record_analysis(
        intent="describe",
        hypothesis="distribution is approximately normal",
        claim="mean=5, std=2",
        confidence=0.8,
        sample_size=200,
        dimensions=1,
    )
    assert rec["intent"] == "describe"
    assert rec["confidence"] == 0.8
    assert rec["sample_size"] == 200
    assert rec["overconfident"] is False  # 0.8 ≤ 0.6 + min(0.4, 200/50) = 1.0
    assert layer.intent_state["describe"]["total"] == 1
    assert layer.intent_state["describe"]["overconfident"] == 0


def test_untagged_analysis_recorded_not_credited():
    layer = _fresh_layer()
    layer.record_analysis(
        intent="banana", claim="x", confidence=0.5, sample_size=10
    )
    for k in ("describe", "compare", "predict", "explain"):
        assert layer.intent_state[k]["total"] == 0
    assert layer.analyses[-1]["intent"] == "__untagged__"


def test_overconfidence_detected_on_small_sample():
    layer = _fresh_layer()
    # predict on n=10 with confidence=0.9: budget = 0.4 + min(0.4, 10/100) = 0.5
    rec = layer.record_analysis(
        intent="predict",
        hypothesis="X happens",
        claim="X will happen",
        confidence=0.9,
        sample_size=10,
    )
    assert rec["overconfident"] is True
    assert layer.consecutive_overconfident == 1


def test_describe_more_lenient_than_predict():
    """Same confidence + sample size: describe should pass while predict overconfident."""
    layer = _fresh_layer()
    desc = layer.record_analysis(intent="describe", confidence=0.7, sample_size=20)
    pred = layer.record_analysis(intent="predict", confidence=0.7, sample_size=20)
    # describe budget at n=20: 0.6 + min(0.4, 20/50) = 1.0 → 0.7 OK
    # predict budget at n=20: 0.4 + min(0.4, 20/100) = 0.6 → 0.7 over
    assert desc["overconfident"] is False
    assert pred["overconfident"] is True


def test_should_block_invalid_intent():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="banana", sample_size=100, claimed_confidence=0.5)
    assert block is True
    assert "invalid intent" in reason


def test_should_block_low_n_predict():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="predict", sample_size=5, claimed_confidence=0.5)
    assert block is True
    assert "sample-size floor" in reason


def test_should_block_high_confidence_low_sample():
    layer = _fresh_layer()
    block, reason = layer.should_block(
        intent="compare", sample_size=15, claimed_confidence=0.85
    )
    assert block is True
    assert "0.85" in reason or "unsupported" in reason


def test_should_block_clean_passes():
    layer = _fresh_layer()
    block, reason = layer.should_block(
        intent="describe", sample_size=100, claimed_confidence=0.7
    )
    assert block is False
    assert reason == ""


def test_single_hypothesis_streak_detected():
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.SINGLE_HYPOTHESIS_STREAK_LEN):
        layer.record_analysis(
            intent="compare",
            hypothesis="A is bigger than B",
            claim="A > B",
            confidence=0.6,
            sample_size=100,
        )
    assert layer.detect_single_hypothesis_streak() is True


def test_streak_broken_by_alternatives():
    """Same hypothesis but alternatives_considered breaks the streak detection."""
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.SINGLE_HYPOTHESIS_STREAK_LEN):
        layer.record_analysis(
            intent="compare",
            hypothesis="A is bigger than B",
            claim="A > B",
            confidence=0.6,
            sample_size=100,
            alternatives=["A and B are similar; observed difference is noise"],
        )
    assert layer.detect_single_hypothesis_streak() is False


def test_should_block_on_streak():
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.SINGLE_HYPOTHESIS_STREAK_LEN):
        layer.record_analysis(
            intent="compare",
            hypothesis="A > B",
            confidence=0.5,
            sample_size=100,
        )
    block, reason = layer.should_block("compare", sample_size=100, claimed_confidence=0.5)
    assert block is True
    assert "single-hypothesis" in reason


def test_shrinking_samples_detected():
    layer = _fresh_layer()
    # Sample sizes trending down: 200, 180, 100, 30, 20
    for n in [200, 180, 100, 30, 20]:
        layer.record_analysis(
            intent="describe", hypothesis=f"about set {n}",
            claim="x", confidence=0.5, sample_size=n,
        )
    assert layer.detect_shrinking_samples() is True


def test_shrinking_samples_not_triggered_on_stable():
    layer = _fresh_layer()
    for n in [100, 100, 100, 100, 100]:
        layer.record_analysis(
            intent="describe", hypothesis=f"set {n}",
            claim="x", confidence=0.5, sample_size=n,
        )
    assert layer.detect_shrinking_samples() is False


def test_record_outcome_updates_calibration():
    layer = _fresh_layer()
    rec = layer.record_analysis(
        intent="predict", hypothesis="X", claim="X happens",
        confidence=0.7, sample_size=100,
    )
    assert layer.record_outcome(rec["id"], True) is True
    assert len(layer.calibration_window) == 1
    assert layer.calibration_window[0] == (0.7, True)
    # Unknown id returns False.
    assert layer.record_outcome("does_not_exist", True) is False


def test_calibration_needs_min_n():
    """calibration_score returns 0 below CALIBRATION_MIN_N."""
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    for i in range(mod.CALIBRATION_MIN_N - 1):
        rec = layer.record_analysis(
            intent="predict", hypothesis=f"H{i}", confidence=0.9, sample_size=100
        )
        layer.record_outcome(rec["id"], False)  # always wrong despite high conf
    assert layer.calibration_score() == 0.0  # not enough data
    assert layer.is_miscalibrated() is False


def test_miscalibration_detected_when_overconfident_outcomes():
    """Claim 90% confident, get it right 30% of the time → miscalibrated."""
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    # Record more than CALIBRATION_MIN_N to get a real score.
    for i in range(15):
        rec = layer.record_analysis(
            intent="predict", hypothesis=f"H{i}", confidence=0.9, sample_size=100
        )
        # Right 30% of the time.
        was_right = (i % 10) < 3
        layer.record_outcome(rec["id"], was_right)
    score = layer.calibration_score()
    assert score > mod.MISCALIBRATION_DELTA, f"got score {score}"
    assert layer.is_miscalibrated() is True


def test_well_calibrated_when_outcomes_match_claims():
    layer = _fresh_layer()
    # Claim 70% confidence; right exactly 7 / 10 of the time.
    for i in range(10):
        rec = layer.record_analysis(
            intent="predict", hypothesis=f"H{i}", confidence=0.7, sample_size=100
        )
        was_right = i < 7  # 7/10 = 0.7 exactly
        layer.record_outcome(rec["id"], was_right)
    # mean_conf = 0.7, hit_rate = 0.7, score = 0
    assert layer.calibration_score() == 0.0
    assert layer.is_well_calibrated() is True
    assert layer.is_miscalibrated() is False


def test_inference_state_priority():
    from brain.mechanisms import inference_integrity_layer as mod

    # Idle initially.
    layer = _fresh_layer()
    assert layer.inference_state() == "idle"

    # Recent analysis → inferring.
    layer.record_analysis(intent="describe", confidence=0.7, sample_size=100)
    assert layer.inference_state() == "inferring"

    # Drive overconfidence streak.
    layer = _fresh_layer()
    for i in range(3):
        layer.record_analysis(
            intent="predict", hypothesis=f"H{i}",
            confidence=0.95, sample_size=10,  # over budget
        )
    assert layer.inference_state() == "overconfident"


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    rec = layer1.record_analysis(
        intent="describe", confidence=0.7, sample_size=100
    )
    layer1.record_outcome(rec["id"], True)

    from brain.mechanisms.inference_integrity_layer import InferenceIntegrityLayer
    layer2 = InferenceIntegrityLayer()
    assert layer2.intent_state["describe"]["total"] == 1
    assert len(layer2.calibration_window) == 1
    assert layer2.calibration_window[0] == (0.7, True)


def test_ipw_handshake_throttled():
    from brain.mechanisms import inference_integrity_layer as mod
    layer = _fresh_layer()
    # Drive miscalibration: 15 samples claiming 0.9, only 30% right.
    for i in range(15):
        rec = layer.record_analysis(
            intent="predict", hypothesis=f"H{i}", confidence=0.9, sample_size=100
        )
        layer.record_outcome(rec["id"], (i % 10) < 3)
    # Plus drive consecutive_overconfident streak.
    for i in range(5):
        layer.record_analysis(
            intent="predict", hypothesis=f"K{i}",
            confidence=0.95, sample_size=10,
        )
    assert layer.is_miscalibrated() is True
    # Now should propose.
    assert layer.should_propose_identity_update() is True

    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False

    # Need IPW_REPORT_EVERY more overconfident analyses to re-fire.
    for i in range(mod.IPW_REPORT_EVERY):
        layer.record_analysis(
            intent="predict", hypothesis=f"M{i}",
            confidence=0.95, sample_size=10,
        )
    assert layer.should_propose_identity_update() is True


def test_proposed_identity_signal_shape():
    layer = _fresh_layer()
    for i in range(15):
        rec = layer.record_analysis(
            intent="predict", hypothesis=f"H{i}", confidence=0.9, sample_size=100
        )
        layer.record_outcome(rec["id"], (i % 10) < 3)
    sig = layer.proposed_identity_signal()
    for key in ("source", "kind", "calibration_score", "calibration_n",
                "consecutive_overconfident", "intent_overconfidence_rates"):
        assert key in sig
    assert sig["source"] == "InferenceIntegrityLayer"
    assert sig["kind"] in ("miscalibration", "sustained_overconfidence")


def test_reset_calibration():
    layer = _fresh_layer()
    for i in range(10):
        rec = layer.record_analysis(
            intent="predict", confidence=0.9, sample_size=10
        )
        layer.record_outcome(rec["id"], False)
    assert len(layer.calibration_window) == 10
    layer.reset_calibration()
    assert len(layer.calibration_window) == 0
    assert layer.consecutive_overconfident == 0


def test_get_state_shape_consistent():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "inference_state", "consecutive_overconfident", "is_miscalibrated",
        "is_well_calibrated", "calibration_score", "calibration_n",
        "single_hypothesis_streak", "shrinking_samples", "intent_distribution",
        "analysis_count", "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), (
        f"missing: {expected - set(state.keys())}"
    )


def test_tick_with_analysis_records_it():
    layer = _fresh_layer()
    out = layer.tick({
        "analysis": {
            "intent": "compare",
            "hypothesis": "groups differ",
            "claim": "A > B",
            "confidence": 0.7,
            "sample_size": 80,
            "dimensions": 2,
            "alternatives": ["A and B are equal"],
            "conclusion": "evidence supports A > B",
        }
    })
    assert out["_fired_tick"] is True
    assert out["analysis_count"] == 1
    assert layer.intent_state["compare"]["total"] == 1
    assert layer.intent_state["compare"]["with_alternatives"] == 1


def test_tick_with_outcome_updates_calibration():
    layer = _fresh_layer()
    rec = layer.record_analysis(
        intent="predict", hypothesis="X", confidence=0.6, sample_size=100
    )
    out = layer.tick({"analysis_outcome": {"analysis_id": rec["id"], "was_right": True}})
    assert out["_fired_tick"] is True
    assert len(layer.calibration_window) == 1
    assert layer.calibration_window[0] == (0.6, True)
