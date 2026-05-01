"""
Behavioral tests for Build 18: CRHStressDispatcher (CeA CRH).

Run:
    pytest brain/tests/test_crh_stress_dispatcher.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational009CRHStressDispatcher import CRHStressDispatcher


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestAnxietyBehavioralOutput:
    """CeA → PAG anxiety behavior (freezing, vigilance)."""

    def test_baseline_anxiety_is_low(self):
        """No threat → minimal anxiety output."""
        mech = CRHStressDispatcher()
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "StressActivationAxis": {"crh_level": 0.0},
                        "ValenceTagger": {"valence_polarity": 0.0},
                        "ArousalRegulator": {"arousal_level": 0.5},
                    }
                }
            )
        )
        assert result["anxiety_behavioral_output"] < 0.40

    def test_negative_valence_activates_anxiety_output(self):
        """Threat (negative valence) activates CeA anxiety output."""
        mech = CRHStressDispatcher()
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "StressActivationAxis": {"crh_level": 0.0},
                        "ValenceTagger": {"valence_polarity": -0.70},
                        "ArousalRegulator": {"arousal_level": 0.60},
                    }
                }
            )
        )
        assert result["anxiety_behavioral_output"] > 0.30

    def test_pvn_crh_amplifies_anxiety_output(self):
        """PVN CRH (systemic stress) amplifies CeA behavioral anxiety."""
        mech = CRHStressDispatcher()
        prior_no_crh = {
            "StressActivationAxis": {"crh_level": 0.0},
            "ValenceTagger": {"valence_polarity": -0.50},
            "ArousalRegulator": {"arousal_level": 0.60},
        }
        prior_with_crh = {
            "StressActivationAxis": {"crh_level": 0.70},
            "ValenceTagger": {"valence_polarity": -0.50},
            "ArousalRegulator": {"arousal_level": 0.60},
        }
        result_no = _run(mech.tick({"prior_results": prior_no_crh}))
        result_with = _run(mech.tick({"prior_results": prior_with_crh}))
        assert result_with["anxiety_behavioral_output"] > result_no["anxiety_behavioral_output"]


class TestBrainstemArousal:
    """CeA → LC arousal modulation (independent of PVN)."""

    def test_negative_valence_elevates_brainstem_arousal(self):
        """CeA CRH activates LC → arousal elevation."""
        mech = CRHStressDispatcher()
        prior = {
            "StressActivationAxis": {"crh_level": 0.0},
            "ValenceTagger": {"valence_polarity": -0.60},
            "ArousalRegulator": {"arousal_level": 0.50},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["brainstem_arousal_modulation"] > 0.0


class TestAttentionSignal:
    """CRH-R1 basal forebrain attention sharpening."""

    def test_threat_activates_attention_signal(self):
        """Threat elevates CRH-R1 attention signal."""
        mech = CRHStressDispatcher()
        prior = {
            "StressActivationAxis": {"crh_level": 0.50},
            "ValenceTagger": {"valence_polarity": -0.60},
            "ArousalRegulator": {"arousal_level": 0.60},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["crh_r1_attention_signal"] > 0.20


class TestThreatPotency:
    """Overall CeA threat output strength."""

    def test_threat_potency_increases_with_threat_signals(self):
        mech = CRHStressDispatcher()
        prior = {
            "StressActivationAxis": {"crh_level": 0.70},
            "ValenceTagger": {"valence_polarity": -0.70},
            "ArousalRegulator": {"arousal_level": 0.75},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["threat_potency"] > 0.30

    def test_threat_potency_bounded_0_to_1(self):
        mech = CRHStressDispatcher()
        prior = {
            "StressActivationAxis": {"crh_level": 1.0},
            "ValenceTagger": {"valence_polarity": -1.0},
            "ArousalRegulator": {"arousal_level": 1.0},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert 0.0 <= result["threat_potency"] <= 1.0


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = CRHStressDispatcher()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["anxiety_behavioral_output", "brainstem_arousal_modulation",
                    "crh_r1_attention_signal", "threat_potency"]:
            assert key in result
