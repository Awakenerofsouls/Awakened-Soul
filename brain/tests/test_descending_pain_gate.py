"""
Behavioral tests for Build 16: DescendingPainGate (PAG analgesia).

Run:
    pytest brain/tests/test_descending_pain_gate.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational005DescendingPainGate import (
    DescendingPainGate,
)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestGateStatus:
    """Gate status correctly classifies pain gate state."""

    def test_baseline_gate_is_open(self):
        """With no inputs, gate defaults to open (no analgesic tone)."""
        mech = DescendingPainGate()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["gate_status"] == "open"

    def test_high_valence_closes_gate(self):
        """Positive valence (safety) activates PAG → gate closes."""
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.0},
            "ValenceTagger": {"valence_polarity": 0.80},
            "ArousalRegulator": {"arousal_level": 0.50},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["gate_status"] in ("partially_gated", "closed")

    def test_negative_valence_opens_gate(self):
        """Negative valence (distress) suppresses PAG → gate opens."""
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.0},
            "ValenceTagger": {"valence_polarity": -0.70},
            "ArousalRegulator": {"arousal_level": 0.50},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["gate_status"] == "open"

    def test_strong_crh_can_close_gate(self):
        """CRH activation (stress) can activate PAG analgesia."""
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.80},
            "ValenceTagger": {"valence_polarity": 0.30},
            "ArousalRegulator": {"arousal_level": 0.60},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["gate_status"] != "open"


class TestActiveCopingMode:
    """Active coping drives (curiosity, expression, connection) boost PAG."""

    def test_active_coping_drive_activates_coping_mode(self):
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.30},
            "ValenceTagger": {"valence_polarity": 0.50},
            "ArousalRegulator": {"arousal_level": 0.60},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["active_coping_mode"] is True

    def test_rest_drive_not_active_coping(self):
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.30},
            "ValenceTagger": {"valence_polarity": 0.50},
            "ArousalRegulator": {"arousal_level": 0.60},
            "Homeostat": {"dominant_drive": "rest"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["active_coping_mode"] is False


class TestDescendingInhibition:
    """Desc analgesic signal is proportional to PAG activation."""

    def test_descending_inhibition_bounded_0_to_1(self):
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.90},
            "ValenceTagger": {"valence_polarity": 0.90},
            "ArousalRegulator": {"arousal_level": 0.90},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert 0.0 <= result["descending_inhibition"] <= 1.0

    def test_positive_valence_increases_inhibition(self):
        mech = DescendingPainGate()
        result_neutral = _run(
            mech.tick(
                {
                    "prior_results": {
                        "StressActivationAxis": {"crh_level": 0.0},
                        "ValenceTagger": {"valence_polarity": 0.0},
                        "ArousalRegulator": {"arousal_level": 0.5},
                        "Homeostat": {"dominant_drive": "stability"},
                    }
                }
            )
        )
        result_pos = _run(
            mech.tick(
                {
                    "prior_results": {
                        "StressActivationAxis": {"crh_level": 0.0},
                        "ValenceTagger": {"valence_polarity": 0.70},
                        "ArousalRegulator": {"arousal_level": 0.5},
                        "Homeostat": {"dominant_drive": "curiosity"},
                    }
                }
            )
        )
        assert result_pos["descending_inhibition"] > result_neutral["descending_inhibition"]


class TestPainSuppressionEfficacy:
    """Real-world analgesic efficacy is a fraction of theoretical maximum."""

    def test_efficacy_bounded_0_to_0_8(self):
        """Max efficacy of PAG analgesia is ~80% (research literature)."""
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 0.90},
            "ValenceTagger": {"valence_polarity": 0.90},
            "ArousalRegulator": {"arousal_level": 0.90},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["pain_suppression_efficacy"] <= 0.80

    def test_max_efficacy_at_max_inhibition(self):
        mech = DescendingPainGate()
        prior = {
            "StressActivationAxis": {"crh_level": 1.0},
            "ValenceTagger": {"valence_polarity": 1.0},
            "ArousalRegulator": {"arousal_level": 1.0},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        # Should approach but not exceed 0.80
        assert result["pain_suppression_efficacy"] > 0.50


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = DescendingPainGate()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["descending_inhibition", "gate_status",
                    "active_coping_mode", "pain_suppression_efficacy"]:
            assert key in result

    def test_gate_status_values_valid(self):
        mech = DescendingPainGate()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["gate_status"] in ("open", "partially_gated", "closed")
