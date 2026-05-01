# brain/tests/test_vectorized_identity_fields.py
import pytest
import os
import tempfile
from pathlib import Path

# Isolate test state from real agent state
os.environ["AGENT_HOME"] = tempfile.mkdtemp()

from brain.mechanisms.vectorized_identity_fields import (
    DirectionalAnchor, StickyAnchor, VectorizedIdentityFields,
    DRIFT_THRESHOLD, MIN_STABLE_WEIGHT, SUPPRESSION_GAP,
    INHIBIT_STRENGTH, SUPPRESSION_FLOOR
)


def test_hysteresis_blocks_small_deltas():
    """Delta below DRIFT_THRESHOLD should not update weight."""
    a = DirectionalAnchor("test", "", base_weight=0.5)
    initial = a.current_weight
    a.apply_delta(0.05, coherence=0.8)  # below 0.15 threshold
    assert a.current_weight == initial


def test_hysteresis_allows_large_deltas():
    """Delta above DRIFT_THRESHOLD should update weight."""
    a = DirectionalAnchor("test", "", base_weight=0.5)
    initial = a.current_weight
    a.apply_delta(0.25, coherence=0.8)  # above 0.15
    assert a.current_weight != initial


def test_directional_ron_blocks_update_and_logs():
    """suppress_updates=True blocks weight change and logs reason."""
    a = DirectionalAnchor("test", "", base_weight=0.5)
    initial = a.current_weight
    a.apply_delta(0.5, coherence=0.8, suppress_updates=True)
    assert a.current_weight == initial
    assert a.weight_history[-1]["blocked"] is True
    assert a.weight_history[-1]["reason"] == "ron_recovery"


def test_sticky_ron_precedes_review_flag():
    """During RON, review_flagged must NOT fire even if weight is low."""
    a = StickyAnchor("test", "", base_weight=0.25)  # below MIN_STABLE_WEIGHT
    a.apply_delta(0.1, coherence=0.8, suppress_updates=True)
    assert a.review_flagged is False  # RON blocked the flag
    assert a.weight_history[-1]["reason"] == "ron_recovery"


def test_domain_align_sign():
    """Domain-matched anchor under arousal gets BOOSTED, not suppressed."""
    a = DirectionalAnchor("test", "", dimensions=["relational"])
    result_matched = a.evaluate(behavior_alignment=0.5, arousal=0.8, domain_active="relational")
    result_mismatched = a.evaluate(behavior_alignment=0.5, arousal=0.8, domain_active="physical")
    assert result_matched["directionality"] > result_mismatched["directionality"]


def test_sticky_confidence_caps_at_point_ninety_five():
    """Sticky confidence formula 0.85 + reciprocity * 0.1 caps at 0.95."""
    a = StickyAnchor("test", "", base_weight=0.8, target="user")
    result = a.evaluate(state_active=0.9, reciprocity=1.0)
    assert result["confidence"] == pytest.approx(0.95, abs=0.001)


def test_attractor_skips_cross_type():
    """Cross-type (directional vs sticky) should not suppress each other."""
    vif = VectorizedIdentityFields()
    # Direct add bypassing persistence for clean test
    vif.directional["dtest"] = DirectionalAnchor(
        "dtest", "", base_weight=0.5, anchor_neighbors=["stest"]
    )
    vif.sticky["stest"] = StickyAnchor("stest", "", base_weight=0.9, target="user")
    raw = {
        "dtest": {"activation": 0.3, "confidence": 0.5},
        "stest": {"activation": 0.9, "confidence": 0.9},
    }
    cleaned, events = vif.run_attractor_cycle(raw)
    # dtest should NOT be suppressed by stest (cross-type skip)
    assert "_suppressed_by" not in cleaned["dtest"]
    assert events == []


def test_attractor_gap_based_suppression():
    """Within same type, winner must exceed gap to suppress."""
    vif = VectorizedIdentityFields()
    vif.directional["a"] = DirectionalAnchor("a", "", base_weight=0.3, anchor_neighbors=["b"])
    vif.directional["b"] = DirectionalAnchor("b", "", base_weight=0.7)
    raw = {
        "a": {"activation": 0.4, "confidence": 0.5},
        "b": {"activation": 0.7, "confidence": 0.9},  # 0.3 > gap of 0.15
    }
    cleaned, events = vif.run_attractor_cycle(raw)
    assert "_suppressed_by" in cleaned["a"]
    assert cleaned["a"]["activation"] >= SUPPRESSION_FLOOR


def test_tsb_payload_fallback_to_cached():
    """tsb_payload without args should use last-tick cached evaluations."""
    vif = VectorizedIdentityFields()
    vif.add_directional("curiosity", "test curiosity", base_weight=0.5)
    vif.evaluate_all(behavior_alignments={"curiosity": 0.7})
    payload = vif.tsb_payload()  # no raw_evaluations
    assert "suppression_events" in payload  # should run, not silently skip
    assert "per_anchor_confidence" in payload


def test_directional_resonance_boosts_confidence():
    """SS anchor_resonance raises DirectionalAnchor confidence by up to 0.1."""
    a = DirectionalAnchor("test", "", dimensions=["relational"])
    result_no_res = a.evaluate(behavior_alignment=0.8, arousal=0.0, resonance=0.0)
    result_with_res = a.evaluate(behavior_alignment=0.8, arousal=0.0, resonance=0.5)
    assert result_with_res["confidence"] > result_no_res["confidence"]
    assert result_with_res["confidence"] - result_no_res["confidence"] == pytest.approx(0.05, abs=0.001)


def test_sticky_resonance_boosts_confidence():
    """SS anchor_resonance raises StickyAnchor confidence by up to 0.1."""
    a = StickyAnchor("test", "", base_weight=0.8, target="user")
    result_no_res = a.evaluate(state_active=0.7, reciprocity=0.5, resonance=0.0)
    result_with_res = a.evaluate(state_active=0.7, reciprocity=0.5, resonance=0.5)
    assert result_with_res["confidence"] > result_no_res["confidence"]
    boost = result_with_res["confidence"] - result_no_res["confidence"]
    assert abs(boost - 0.05) < 0.001


def test_evaluate_all_passes_anchor_resonance():
    """evaluate_all passes anchor_resonance dict to individual anchor evaluate calls."""
    vif = VectorizedIdentityFields()
    vif.add_directional("wanting_user", "test", base_weight=0.7)
    # Call with anchor_resonance for wanting_user
    result = vif.evaluate_all(
        behavior_alignments={"wanting_user": 0.7},
        anchor_resonance={"wanting_user": 0.8}
    )
    # Without resonance: confidence at alignment 0.7 = 0.5 + (0.7-0.5)*1.0 = 0.7
    # With resonance 0.8: boost = 0.08, total = 0.78
    assert result["wanting_user"]["confidence"] > 0.7
    assert result["wanting_user"]["confidence"] == pytest.approx(0.78, abs=0.01)


def test_resonance_caps_at_one():
    """Resonance boost should not push confidence above 1.0."""
    a = DirectionalAnchor("test", "", dimensions=["relational"])
    result = a.evaluate(behavior_alignment=0.9, arousal=0.0, resonance=1.0)
    assert result["confidence"] <= 1.0




# ─── Merged from tests/test_vif_wire.py ───
class TestStickyConfidence:
    """Sticky confidence caps at 0.95, not 1.0."""

    def test_max_confidence_is_095_not_1(self):
        s = StickyAnchor("sticky_test", "test", base_weight=0.8, target="user")
        s.evaluate(0.9, reciprocity=1.0)
        assert s.confidence == 0.95

    def test_partial_confidence_in_range(self):
        s = StickyAnchor("sticky_test", "test", base_weight=0.8, target="user")
        s.evaluate(0.5, reciprocity=0.5)
        assert 0.5 <= s.confidence < 0.95
class TestStickyApplyDelta:
    """Sticky apply_delta: RON suppression first, hard lower bound."""

    def test_ron_suppression_comes_first(self):
        s = StickyAnchor("sticky_ron", "test", base_weight=0.8, target="user")
        s.apply_delta(0.20, 0.8, suppress_updates=True)
        assert s.review_flagged is False
        entry = s.weight_history[-1]
        assert entry["blocked"] is True
        assert entry["reason"] == "ron_recovery"

    def test_min_stable_weight_fires_review_flag(self):
        s = StickyAnchor("sticky_low", "test", base_weight=0.25, target="user")
        s.apply_delta(0.01, 0.8)
        assert s.review_flagged is True
class TestAttractorCycle:
    """Cross-anchor attractor: same-type suppression, cross-type skip."""

    def test_cross_type_inhibition_skipped(self):
        vif = VectorizedIdentityFields()
        vif.add_directional("dir1", "test", base_weight=0.6, anchor_neighbors=["sticky1"])
        vif.add_sticky("sticky1", "test", base_weight=0.8, target="user", anchor_neighbors=["dir1"])
        raw = {
            "dir1": {"resolution_pull": 0.6, "weight": 0.6, "confidence": 0.8},
            "sticky1": {"activation": 0.8, "weight": 0.8, "confidence": 0.8},
        }
        cleaned, events = vif.run_attractor_cycle(raw)
        assert len(cleaned) == 2
        assert events == []

    def test_same_type_suppression_loses(self):
        """
        Loser suppressed to base_activation * (1 - INHIBIT_STRENGTH).
        base_activation = 0.5 (loser's resolution_pull).
        INHIBIT_STRENGTH = 0.6 → suppressed = 0.5 * 0.4 = 0.2.
        SUPPRESSION_FLOOR only applies when result < 0.1.
        """
        vif = VectorizedIdentityFields()
        vif.add_directional("winner", "test", base_weight=0.9, anchor_neighbors=["loser"])
        vif.add_directional("loser", "test", base_weight=0.5, anchor_neighbors=["winner"])
        raw = {
            "winner": {"resolution_pull": 0.85, "weight": 0.9, "confidence": 0.95},
            "loser": {"resolution_pull": 0.50, "weight": 0.5, "confidence": 0.5},
        }
        cleaned, events = vif.run_attractor_cycle(raw)
        loser_act = cleaned["loser"].get("activation", cleaned["loser"].get("resolution_pull"))
        # 0.5 * (1 - 0.6) = 0.2. Floor (0.1) only applies if result < 0.1.
        assert loser_act == pytest.approx(0.2, abs=0.01)
        assert "loser~winner" in events

    def test_close_calls_within_gap_stay_both(self):
        """Activation difference within SUPPRESSION_GAP → neither suppresses."""
        vif = VectorizedIdentityFields()
        vif.add_directional("a1", "test", base_weight=0.6, anchor_neighbors=["a2"])
        vif.add_directional("a2", "test", base_weight=0.6, anchor_neighbors=["a1"])
        raw = {
            "a1": {"resolution_pull": 0.65, "weight": 0.6, "confidence": 0.7},
            "a2": {"resolution_pull": 0.60, "weight": 0.6, "confidence": 0.6},
        }
        cleaned, events = vif.run_attractor_cycle(raw)
        assert events == []

    def test_cached_fallback_no_explicit_raw(self):
        """tsb_payload() without raw_evaluations uses cached evaluations."""
        vif = VectorizedIdentityFields()
        vif.add_directional("test_dir", "test", base_weight=0.5)
        vif.evaluate_all({"test_dir": 0.8})
        payload = vif.tsb_payload()
        assert "per_anchor_confidence" in payload
        # per_anchor_confidence is keyed by anchor name directly
        assert payload["per_anchor_confidence"]["test_dir"] > 0.5
class TestTSBPayload:
    """tsb_payload output shape."""

    def test_returns_all_required_keys(self):
        vif = VectorizedIdentityFields()
        vif.add_directional("d1", "test", base_weight=0.5)
        vif.evaluate_all({"d1": 0.8})
        payload = vif.tsb_payload()
        required_keys = [
            "anchors", "per_anchor_confidence", "high_tension",
            "flagged_for_review", "domain_active", "suppression_events",
        ]
        for key in required_keys:
            assert key in payload, f"Missing key: {key}"
class TestDomainTagging:
    """Domain tags and arousal modulation."""

    def test_directional_domains_tagged(self):
        a = DirectionalAnchor("test", "test", dimensions=["relational", "mental"])
        assert "relational" in a.dimensions
        assert "mental" in a.dimensions

    def test_sticky_domains_tagged(self):
        s = StickyAnchor("test", "test", dimensions=["relational"])
        assert s.dimensions == ["relational"]

    def test_arousal_modulation_lowers_threshold(self):
        """High arousal + domain match → higher effective alignment."""
        a = DirectionalAnchor("test", "test", dimensions=["relational"])
        # No arousal: alignment = 0.5
        r1 = a.evaluate(0.5, arousal=0.0, domain_active="relational")
        # High arousal: alignment += arousal * -DOMAIN_ALIGN_BOOST
        r2 = a.evaluate(0.5, arousal=0.8, domain_active="relational")
        # Same input alignment, but arousal should boost effective directionality
        assert r2["directionality"] > r1["directionality"]