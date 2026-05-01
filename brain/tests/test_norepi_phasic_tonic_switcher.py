"""
Behavioral tests for Build 15: NorepiPhasicTonicSwitcher (LC phasic/tonic).

Run:
    pytest brain/tests/test_norepi_phasic_tonic_switcher.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational004NorepiPhasicTonicSwitcher import (
    NorepiPhasicTonicSwitcher,
)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestModeClassification:
    """LC mode (phasic vs tonic) is classified correctly."""

    def test_low_uncertainty_low_arousal_favors_phasic(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.40},
            "PredictionErrorDrift": {"uncertainty": 0.20, "surprise_magnitude": 0.0},
            "Homeostat": {"dominant_drive": "stability"},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["lc_mode"] == "phasic"

    def test_high_uncertainty_favors_tonic(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.60},
            "PredictionErrorDrift": {"uncertainty": 0.75, "surprise_magnitude": 0.10},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        for _ in range(10):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["lc_mode"] == "tonic"

    def test_very_high_arousal_forces_tonic(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.85},
            "PredictionErrorDrift": {"uncertainty": 0.30, "surprise_magnitude": 0.0},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        for _ in range(10):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["lc_mode"] == "tonic"

    def test_very_low_arousal_forces_phasic(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.15},
            "PredictionErrorDrift": {"uncertainty": 0.50, "surprise_magnitude": 0.0},
            "Homeostat": {"dominant_drive": "rest"},
        }
        for _ in range(10):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["lc_mode"] == "phasic"


class TestGainParameters:
    """Mode-specific gain parameters differ between phasic and tonic."""

    def test_phasic_mode_high_burst_gain(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.40},
            "PredictionErrorDrift": {"uncertainty": 0.15, "surprise_magnitude": 0.50},
            "Homeostat": {"dominant_drive": "stability"},
        }
        for _ in range(5):
            _run(mech.tick({"prior_results": prior}))
        result = _run(mech.tick({"prior_results": prior}))
        if result["lc_mode"] == "phasic":
            assert result["phasic_gain"] >= 1.8

    def test_tonic_mode_reduced_burst_gain(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.80},
            "PredictionErrorDrift": {"uncertainty": 0.70, "surprise_magnitude": 0.10},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        if result["lc_mode"] == "tonic":
            assert result["phasic_gain"] < 1.5

    def test_surprise_increases_phasic_gain_within_phasic_mode(self):
        mech = NorepiPhasicTonicSwitcher()
        prior_lo = {
            "ArousalRegulator": {"arousal_level": 0.40},
            "PredictionErrorDrift": {"uncertainty": 0.20, "surprise_magnitude": 0.10},
            "Homeostat": {"dominant_drive": "stability"},
        }
        prior_hi = {
            "ArousalRegulator": {"arousal_level": 0.40},
            "PredictionErrorDrift": {"uncertainty": 0.20, "surprise_magnitude": 0.80},
            "Homeostat": {"dominant_drive": "stability"},
        }
        for _ in range(5):
            _run(mech.tick({"prior_results": prior_lo}))
        result_lo = _run(mech.tick({"prior_results": prior_lo}))
        result_hi = _run(mech.tick({"prior_results": prior_hi}))
        if result_lo["lc_mode"] == "phasic":
            assert result_hi["phasic_gain"] > result_lo["phasic_gain"]


class TestModeConfidence:
    """Mode confidence tracks certainty of current classification."""

    def test_confidence_increases_with_sustained_evidence(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.80},
            "PredictionErrorDrift": {"uncertainty": 0.75, "surprise_magnitude": 0.20},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        results = []
        for _ in range(15):
            results.append(_run(mech.tick({"prior_results": prior})))
        assert results[-1]["mode_confidence"] > results[4]["mode_confidence"]

    def test_confidence_is_bounded_0_to_1(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.50},
            "PredictionErrorDrift": {"uncertainty": 0.50, "surprise_magnitude": 0.0},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert 0.0 <= result["mode_confidence"] <= 1.0


class TestCuriosityDrive:
    """Curiosity/exploration drives tonic mode."""

    def test_curiosity_drive_favors_tonic(self):
        mech = NorepiPhasicTonicSwitcher()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.55},
            "PredictionErrorDrift": {"uncertainty": 0.40, "surprise_magnitude": 0.0},
            "Homeostat": {"dominant_drive": "curiosity"},
        }
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["lc_mode"] == "tonic"


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = NorepiPhasicTonicSwitcher()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["lc_mode", "phasic_gain", "tonic_baseline", "mode_confidence"]:
            assert key in result
