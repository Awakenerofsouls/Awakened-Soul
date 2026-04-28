"""
Wire 7: RCE → FPEF agency_confidence integration
Tests behavioral effect of agency_confidence on RCE classification.

A1 — Bidirectional threshold adjustment (multiplier 0.5):
  High agency (0.85) → threshold 0.575, score 0.63 clears → growth
  Low agency (0.15) → threshold 0.925, score 0.63 doesn't clear → second branch → drift
  Neutral agency (0.5) → threshold 0.75, score 0.63 doesn't clear → second branch → drift

Same input, different classification based on agency.
"""

import pytest
from brain.rce import ReflectiveConsistencyEngine


def make_rce():
    """Fresh RCE with 5-reading upward trend for growth/stable detection."""
    rce = ReflectiveConsistencyEngine()
    rce.readings.clear()
    rce.coherence_trend = [0.70] * 5  # avg below score → improving
    return rce


# Canonical fixture: score ~0.63, changes classification based on agency
CANONICAL_VIF_CURRENT = {
    "a": {"tension": 0.8, "directionality": 0.85},
    "b": {"tension": 0.65, "directionality": 0.70},
}
CANONICAL_VIF_PREVIOUS = {
    "a": {"tension": 0.6, "directionality": 0.50},  # dir_coh=0.65, tension_coh=0.6
    "b": {"tension": 0.45, "directionality": 0.35},  # dir_coh=0.65, tension_coh=0.6
}
# Both anchors score: 0.65*0.6 + 0.6*0.4 = 0.63
# avg coherence = 0.63


class TestRCEAgencyWire:
    """Behavioral tests: same input, different classification based on agency."""

    def test_high_agency_classifies_as_growth(self):
        """
        Score 0.63 at agency 0.85.
        Threshold = 0.75 - (0.85-0.5)*0.5 = 0.575.
        0.63 > 0.575 → first branch → growth.
        """
        rce = make_rce()
        result = rce.evaluate(
            vif_current=CANONICAL_VIF_CURRENT,
            vif_previous=CANONICAL_VIF_PREVIOUS,
            agency_confidence=0.85,
        )
        assert result.score == pytest.approx(0.63, abs=0.02)
        assert result.classification == "growth", (
            f"Score {result.score} > threshold 0.575 with agency 0.85 → growth, got {result.classification}"
        )

    def test_low_agency_demotes_to_drift(self):
        """
        Same score 0.63 at agency 0.15.
        Threshold = 0.75 - (0.15-0.5)*0.5 = 0.925.
        0.63 < 0.925 → doesn't clear first branch → second branch.
        Second branch: 0.63 > 0.5875 → in range.
        Trend avg 0.70, score 0.63 < 0.70 → drift.
        WITHOUT wire: score would clear first branch (static threshold 0.75) → growth.
        WITH wire: drift. THIS is the behavioral change.
        """
        rce = make_rce()
        result = rce.evaluate(
            vif_current=CANONICAL_VIF_CURRENT,
            vif_previous=CANONICAL_VIF_PREVIOUS,
            agency_confidence=0.15,
        )
        assert result.score == pytest.approx(0.63, abs=0.02)
        thresh = 0.75 - (0.15 - 0.5) * 0.5  # 0.925
        assert result.score < thresh
        assert result.classification == "drift", (
            f"Score {result.score} < threshold {thresh:.3f} with agency 0.15 → drift, got {result.classification}"
        )

    def test_neutral_agency_matches_low_agency_result(self):
        """
        agency=0.5 → threshold 0.75.
        0.63 < 0.75 → doesn't clear first branch → second branch → drift.
        Same as low agency. Neutral agency doesn't lift the threshold.
        """
        rce = make_rce()
        result = rce.evaluate(
            vif_current=CANONICAL_VIF_CURRENT,
            vif_previous=CANONICAL_VIF_PREVIOUS,
            agency_confidence=0.5,
        )
        assert result.score == pytest.approx(0.63, abs=0.02)
        assert result.classification == "drift"

    def test_clear_high_score_growth_regardless_of_agency(self):
        """
        High coherence score (0.85) is above all thresholds.
        Agency doesn't change classification for unambiguous growth.
        """
        rce = make_rce()
        result = rce.evaluate(
            vif_current={"anch": {"tension": 0.9, "directionality": 0.98}},
            vif_previous={"anch": {"tension": 0.8, "directionality": 0.95}},
            agency_confidence=0.1,  # even very low agency
        )
        assert result.classification == "growth"

    def test_clear_low_score_drift_regardless_of_agency(self):
        """
        Low coherence score (0.39) is below all thresholds.
        Agency doesn't change classification for unambiguous drift.
        """
        rce = make_rce()
        result = rce.evaluate(
            vif_current={"anch": {"tension": 0.7, "directionality": 0.9}},
            vif_previous={"anch": {"tension": 0.6, "directionality": 0.2}},
            agency_confidence=0.9,  # even very high agency
        )
        assert result.classification == "drift"

    def test_agency_confidence_default_is_neutral(self):
        """No agency arg → defaults to 0.5 → same behavior as explicit 0.5."""
        rce1 = make_rce()
        r1 = rce1.evaluate(
            vif_current=CANONICAL_VIF_CURRENT,
            vif_previous=CANONICAL_VIF_PREVIOUS,
        )
        rce2 = make_rce()
        r2 = rce2.evaluate(
            vif_current=CANONICAL_VIF_CURRENT,
            vif_previous=CANONICAL_VIF_PREVIOUS,
            agency_confidence=0.5,
        )
        assert r1.classification == r2.classification
        assert r1.score == r2.score
