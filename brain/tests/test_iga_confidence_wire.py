"""
Wire 8: IGA reads self_anchor_strength from fpef_state → confidence-weighted deltas

High self_anchor_strength → confidence ~1.0 → deltas contribute fully
Low self_anchor_strength → confidence ~0.3 → deltas contribute partially
Ownership vs ambient: owned changes accumulate in the gradient, ambient ones don't
"""

import pytest
from brain.iga import IdentityGradientAccumulator


def make_iga():
    rce = IdentityGradientAccumulator()
    rce.current_session = None  # reset any existing session
    rce.begin_session()
    return rce


class TestIGAConfidenceWire:
    """Behavioral tests for self_anchor_strength → IGA confidence integration."""

    def test_high_confidence_full_delta_contribution(self):
        """confidence=1.0: delta contributes fully to session."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.1, confidence=1.0)
        iga.record_tick_delta("making_things", 0.05, confidence=1.0)
        
        session = iga.current_session
        assert session is not None
        assert session.deltas.get("wanting_user") == 0.1
        assert session.deltas.get("making_things") == 0.05

    def test_low_confidence_partial_delta_contribution(self):
        """confidence=0.3: delta contributes 30% to session."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.1, confidence=0.3)
        # 0.1 * 0.3 = 0.03
        session = iga.current_session
        assert session is not None
        assert session.deltas.get("wanting_user") == pytest.approx(0.03, abs=0.001)

    def test_zero_confidence_no_contribution(self):
        """confidence=0.0: delta doesn't contribute."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.1, confidence=0.0)
        session = iga.current_session
        assert session.deltas.get("wanting_user") == 0.0

    def test_default_confidence_is_one(self):
        """No confidence arg → defaults to 1.0 (full contribution)."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.1)  # no confidence arg
        session = iga.current_session
        assert session.deltas.get("wanting_user") == 0.1

    def test_cumulative_deltas_with_mixed_confidence(self):
        """Same anchor recorded with different confidences → weighted sum."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.1, confidence=1.0)  # +0.1
        iga.record_tick_delta("wanting_user", 0.1, confidence=0.5)  # +0.05
        iga.record_tick_delta("wanting_user", 0.1, confidence=0.2)  # +0.02
        session = iga.current_session
        # 0.1 + 0.05 + 0.02 = 0.17
        assert session.deltas.get("wanting_user") == pytest.approx(0.17, abs=0.001)

    def test_multiple_anchors_mixed_confidence(self):
        """Different anchors with different confidences all tracked correctly."""
        iga = make_iga()
        iga.record_tick_delta("wanting_user", 0.2, confidence=0.9)   # +0.18
        iga.record_tick_delta("making_things", 0.1, confidence=0.4)    # +0.04
        iga.record_tick_delta("wanting_user", 0.05, confidence=0.3)   # +0.015
        session = iga.current_session
        assert session.deltas.get("wanting_user") == pytest.approx(0.195, abs=0.001)
        assert session.deltas.get("making_things") == pytest.approx(0.04, abs=0.001)

    def test_confidence_param_available(self):
        """record_tick_delta accepts confidence parameter."""
        iga = make_iga()
        # Should not raise TypeError
        iga.record_tick_delta("test_anchor", 0.05, confidence=0.75)
        assert iga.current_session.deltas.get("test_anchor") == pytest.approx(0.0375, abs=0.001)
