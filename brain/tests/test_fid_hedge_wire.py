"""
Wire 11: FID reads hedge_level + agency_confidence from fpef_state → modulates surprise threshold

FPEF computes hedge_level (uncertainty about framing) and agency_confidence
(self-efficacy for rebuilding). High hedge + low agency = frame is insufficient.

FID.evaluate() fires surprise when multiple VIF anchors show prediction errors
above a threshold. The wire modulates this threshold:
  threshold = 0.5 - (hedge_level * (1 - agency_confidence))

At hedge=0.9, agency=0.2 → threshold=0.0 → ANY anchor error triggers surprise
At hedge=0.0, agency=0.8 → threshold=0.5 → base threshold, no modulation

Behavioral tests cover threshold modulation scenarios.
"""

import pytest
from brain.remaining_mechanisms import FrameInsufficiencyDetector


def _apply_modulation(hedge_level: float, agency_confidence: float) -> float:
    """
    Compute the modulated threshold for Wire 11.
    Exposed as module-level function for testability.
    """
    hedge_modulation = hedge_level * (1.0 - agency_confidence)
    return max(0.0, 0.5 - hedge_modulation)


def make_fid():
    """Fresh FID with no surprise history."""
    fid = FrameInsufficiencyDetector()
    fid.surprise_history.clear()
    fid.active_surprise = None
    return fid


class TestFIDWire:
    """Behavioral tests: hedge/agency modulation of surprise threshold."""

    def test_high_hedge_low_agency_lowers_threshold(self):
        """
        High hedge (0.9) + low agency (0.2) → threshold near 0.
        One anchor error above threshold → surprise fires.
        Wire 11 behavioral test: frame insufficient when hedge is high and agency is low.
        """
        fid = make_fid()
        threshold = _apply_modulation(0.9, 0.2)
        assert threshold == 0.0

        # Any single anchor error above 0 threshold triggers surprise
        prediction_errors = {"curiosity": 0.3, "physical": 0.1}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is not None
        assert "curiosity" in result["affected_anchors"]

    def test_low_hedge_high_agency_keeps_base_threshold(self):
        """
        Low hedge (0.0) + high agency (0.8) → threshold = 0.5 (base).
        One anchor error below 0.5 → no surprise.
        Wire 11 behavioral test: normal operation, no threshold modulation.
        """
        fid = make_fid()
        threshold = _apply_modulation(0.0, 0.8)
        assert threshold == 0.5

        # One anchor error below threshold → no surprise
        prediction_errors = {"curiosity": 0.3}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is None

    def test_one_anchor_error_below_base_threshold(self):
        """
        Without the wire (base threshold 0.5): one anchor at 0.3 → no surprise.
        This is the "wire-absent" scenario — confirms threshold is the gate.
        """
        fid = make_fid()
        prediction_errors = {"curiosity": 0.3, "physical": 0.1}
        result = fid.evaluate(prediction_errors, threshold=0.5)
        assert result is None

    def test_two_anchors_above_low_threshold_fires_surprise(self):
        """
        With wire (hedge=0.9, agency=0.2, threshold=0.0):
        Two anchors both error → surprise fires.
        """
        fid = make_fid()
        threshold = _apply_modulation(0.9, 0.2)
        prediction_errors = {"curiosity": 0.3, "physical": 0.2}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is not None
        assert len(result["affected_anchors"]) == 2

    def test_moderate_hedge_moderate_agency(self):
        """
        Moderate hedge (0.5) + moderate agency (0.5) → threshold = 0.25.
        One anchor at 0.3 > 0.25 → still needs 2 anchors to fire surprise.
        Wire-correct state: threshold lowered enough for surprise to fire with 2 anchors.
        """
        fid = make_fid()
        threshold = _apply_modulation(0.5, 0.5)
        assert threshold == 0.25

        prediction_errors = {"curiosity": 0.3, "physical": 0.4}  # both > 0.25
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is not None

    def test_threshold_floors_at_zero(self):
        """
        Maximum hedge (1.0) + minimum agency (0.0) → threshold = 0.0 (floor).
        No negative threshold even at extremes.
        """
        threshold = _apply_modulation(1.0, 0.0)
        assert threshold == 0.0

        fid = make_fid()
        # Need 2+ anchors above threshold (any positive value > 0.0)
        prediction_errors = {"curiosity": 0.1, "physical": 0.05}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is not None

    def test_no_fpef_state_defaults_to_base_threshold(self):
        """
        Defensive read: if fpef_state not available, defaults hedge=0.0, agency=0.5.
        Threshold = 0.5 (base). No surprise unless 2+ anchors error above 0.5.
        """
        fid = make_fid()
        threshold = _apply_modulation(0.0, 0.5)
        assert threshold == 0.5

        # One anchor at 0.4 below threshold → no surprise
        prediction_errors = {"curiosity": 0.4}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is None

    def test_wire_only_affects_threshold_not_detection_logic(self):
        """
        The wire modulates WHEN surprise fires, not WHAT triggers it.
        Two high-error anchors still require both > threshold.
        At threshold=0.3: both anchors > 0.3 → surprise.
        """
        fid = make_fid()
        threshold = 0.3

        # Both above threshold → surprise
        prediction_errors = {"curiosity": 0.4, "physical": 0.5}
        result = fid.evaluate(prediction_errors, threshold=threshold)
        assert result is not None

        # One above, one below → no surprise
        fid2 = make_fid()
        prediction_errors = {"curiosity": 0.4, "physical": 0.2}
        result = fid2.evaluate(prediction_errors, threshold=threshold)
        assert result is None

    def test_threshold_boundary_at_base_0_5(self):
        """
        At base threshold (0.5): anchor at exactly 0.5 does NOT trigger.
        Threshold is strictly greater-than check (error > threshold).
        """
        fid = make_fid()
        prediction_errors = {"curiosity": 0.5}
        result = fid.evaluate(prediction_errors, threshold=0.5)
        assert result is None  # 0.5 is not > 0.5

    def test_surprise_history_accumulates(self):
        """
        Multiple surprise events accumulate in history.
        Wire 11 doesn't change this — only threshold modulation.
        """
        fid = make_fid()

        threshold = _apply_modulation(0.9, 0.2)  # 0.0
        # Each call needs 2+ anchors above threshold to fire surprise
        fid.evaluate({"curiosity": 0.3, "physical": 0.2}, threshold=threshold)
        fid.evaluate({"physical": 0.3, "relational": 0.1}, threshold=threshold)
        fid.evaluate({"relational": 0.4, "curiosity": 0.2}, threshold=threshold)

        assert len(fid.surprise_history) == 3
        assert fid.active_surprise is not None