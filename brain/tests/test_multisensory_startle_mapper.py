"""
Behavioral tests for Build 14: MultisensoryStartleMapper (LC-PnC startle).

Run:
    pytest brain/tests/test_multisensory_startle_mapper.py -v
"""

import asyncio
import pytest

from brain.foundational.Foundational003MultisensoryStartleMapper import (
    MultisensoryStartleMapper,
)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestBaselineStartle:
    """Baseline startle amplitude (no startling event)."""

    def test_baseline_amplitude_is_non_zero(self):
        mech = MultisensoryStartleMapper()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["startle_amplitude"] > 0

    def test_baseline_gain_is_always_positive(self):
        mech = MultisensoryStartleMapper()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["startle_gain"] > 0


class TestLCGainModulation:
    """LC-NE activity modulates startle gain."""

    def test_high_arousal_increases_gain(self):
        mech = MultisensoryStartleMapper()
        result_lo = _run(
            mech.tick({"prior_results": {"ArousalRegulator": {"arousal_level": 0.10}}})
        )
        result_hi = _run(
            mech.tick({"prior_results": {"ArousalRegulator": {"arousal_level": 0.90}}})
        )
        assert result_hi["startle_gain"] > result_lo["startle_gain"]

    def test_high_arousal_increases_amplitude(self):
        mech = MultisensoryStartleMapper()
        result = _run(
            mech.tick(
                {
                    "prior_results": {"ArousalRegulator": {"arousal_level": 0.90}},
                    "startling_event": True,
                }
            )
        )
        # High arousal should amplify startle
        assert result["startle_amplitude"] > 0.25


class TestFearPotentiation:
    """Negative valence (fear) potentiates startle amplitude."""

    def test_negative_valence_increases_amplitude(self):
        mech = MultisensoryStartleMapper()
        result = _run(
            mech.tick(
                {
                    "prior_results": {"ValenceTagger": {"valence_polarity": -0.70}},
                    "startling_event": True,
                }
            )
        )
        assert result["startle_amplitude"] > 0.15

    def test_positive_valence_does_not_potentiate(self):
        mech = MultisensoryStartleMapper()
        result = _run(
            mech.tick(
                {
                    "prior_results": {"ValenceTagger": {"valence_polarity": 0.70}},
                    "startling_event": True,
                }
            )
        )
        # Positive valence should not potentiate beyond baseline
        assert result["startle_amplitude"] < 0.35


class TestAnticipatoryAmplification:
    """Anticipatory anxiety pre-activates LC, amplifying subsequent startle."""

    def test_negative_valence_plus_high_arousal_triggers_anticipatory(self):
        """Anticipatory amplification fires after 3+ ticks of negative valence + high arousal."""
        mech = MultisensoryStartleMapper()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.75},
            "ValenceTagger": {"valence_polarity": -0.50},
        }
        # Tick 3+: should activate
        for _ in range(2):
            _run(mech.tick({"prior_results": prior}))
        result = _run(mech.tick({"prior_results": prior}))
        assert result["anticipatory_amplification"] is True

    def test_anticipatory_increases_amplitude(self):
        mech = MultisensoryStartleMapper()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.75},
            "ValenceTagger": {"valence_polarity": -0.50},
        }
        for _ in range(3):
            _run(mech.tick({"prior_results": prior}))
        result = _run(
            mech.tick({"prior_results": prior, "startling_event": True})
        )
        assert result["startle_amplitude"] > 0.20


class TestMultimodalFusion:
    """High arousal + negative valence = multimodal fusion signal."""

    def test_multimodal_fusion_flag_set(self):
        mech = MultisensoryStartleMapper()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.75},
            "ValenceTagger": {"valence_polarity": -0.50},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["multimodal_fusion"] is True

    def test_calm_positive_state_no_multimodal_fusion(self):
        mech = MultisensoryStartleMapper()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.30},
            "ValenceTagger": {"valence_polarity": 0.60},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["multimodal_fusion"] is False


class TestStartlingEvent:
    """Startling event triggers acute startle response."""

    def test_startling_event_fires_response(self):
        mech = MultisensoryStartleMapper()
        result = _run(
            mech.tick({"prior_results": {}, "startling_event": True})
        )
        assert result["startle_amplitude"] > 0.05

    def test_no_startling_event_reduces_amplitude(self):
        mech = MultisensoryStartleMapper()
        with_event = _run(
            mech.tick({"prior_results": {}, "startling_event": True})
        )
        # Reset and run without
        mech2 = MultisensoryStartleMapper()
        without_event = _run(
            mech2.tick({"prior_results": {}, "startling_event": False})
        )
        # With event should be larger than without
        assert with_event["startle_amplitude"] > without_event["startle_amplitude"]


class TestOutputKeys:
    """All required output keys present."""

    def test_required_keys(self):
        mech = MultisensoryStartleMapper()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["startle_amplitude", "startle_gain",
                    "anticipatory_amplification", "multimodal_fusion"]:
            assert key in result
