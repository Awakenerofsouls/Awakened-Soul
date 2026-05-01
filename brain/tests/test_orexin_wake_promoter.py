"""
Behavioral tests for Build 17: OrexinWakePromoter (LHA orexin).

Run:
    pytest brain/tests/test_orexin_wake_promoter.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational008OrexinWakePromoter import OrexinWakePromoter


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOrexinTone:
    """Orexin tone tracks arousal and behavioral state."""

    def test_baseline_tone_is_nonzero(self):
        mech = OrexinWakePromoter()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["orexin_tone"] > 0

    def test_alert_mode_elevates_tone(self):
        mech = OrexinWakePromoter()
        prior = {"ArousalRegulator": {"arousal_level": 0.80, "mode": "alert"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] > 0.50

    def test_hypoaroused_mode_suppresses_tone(self):
        mech = OrexinWakePromoter()
        prior = {"ArousalRegulator": {"arousal_level": 0.15, "mode": "hypoaroused"}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] < 0.40

    def test_hyperaroused_elevates_above_alert(self):
        mech = OrexinWakePromoter()
        prior = {"ArousalRegulator": {"arousal_level": 0.90, "mode": "hyperaroused"}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] > 0.70


class TestDriveModulation:
    """Orexin tracks active exploration drives."""

    def test_curiosity_drive_elevates_tone(self):
        mech = OrexinWakePromoter()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.60, "mode": "alert"},
            "Homeostat": {"dominant_drive": "curiosity", "metabolic_state": "fed"},
        }
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] > 0.55

    def test_rest_drive_suppresses_tone(self):
        mech = OrexinWakePromoter()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.50, "mode": "reflective"},
            "Homeostat": {"dominant_drive": "rest", "metabolic_state": "fed"},
        }
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] < 0.45


class TestMetabolicModulation:
    """Hunger activates orexin (food-seeking wakefulness)."""

    def test_hungry_metabolic_state_elevates_tone(self):
        mech = OrexinWakePromoter()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.50, "mode": "alert"},
            "Homeostat": {"dominant_drive": "curiosity", "metabolic_state": "hungry"},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["orexin_tone"] > 0.55


class TestWakeStabilityAndSleepPressure:
    """Inverse relationship between orexin tone and sleep pressure."""

    def test_high_tone_produces_high_wake_stability(self):
        mech = OrexinWakePromoter()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.85, "mode": "alert"},
            "Homeostat": {"dominant_drive": "curiosity", "metabolic_state": "fed"},
        }
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["wake_stability"] > 0.60

    def test_wake_stability_and_sleep_pressure_are_inversely_related(self):
        mech = OrexinWakePromoter()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.80, "mode": "alert"},
            "Homeostat": {"dominant_drive": "curiosity", "metabolic_state": "fed"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        # Both should not be high simultaneously
        assert not (result["wake_stability"] > 0.70 and result["sleep_pressure"] > 0.70)


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = OrexinWakePromoter()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["orexin_tone", "wake_stability", "sleep_pressure", "metabolic_modulation"]:
            assert key in result
