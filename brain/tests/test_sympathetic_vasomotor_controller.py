"""
Behavioral tests for Build 12: SympatheticVasomotorController (RVLM).

Run:
    pytest brain/tests/test_sympathetic_vasomotor_controller.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational001SympatheticVasomotorController import (
    SympatheticVasomotorController,
)


def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestBaselineTone:
    """Baseline resting sympathetic tone (no inputs)."""

    def test_baseline_tone_in_normal_range(self):
        """At rest with no inputs, tone should settle near resting value 0.52."""
        mech = SympatheticVasomotorController()
        for _ in range(50):
            result = _run(mech.tick({"prior_results": {}}))
        # After settling, should be near resting tone
        assert 0.40 <= result["sympathetic_tone"] <= 0.65

    def test_mean_arterial_pressure_index_initializes(self):
        """MAP index initializes to a sensible resting value."""
        mech = SympatheticVasomotorController()
        result = _run(mech.tick({"prior_results": {}}))
        assert 0.0 <= result["mean_arterial_pressure_index"] <= 1.0
        assert isinstance(result["threat_activated"], bool)


class TestBaroreflexModulation:
    """Baroreceptor feedback suppresses or activates RVLM tone."""

    def test_baroreceptor_suppressed_reduces_tone(self):
        """When baroreceptor is suppressed (BP high), tone drops."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {
                "baroreceptor_suppressed": True,
                "baroreflex_intensity": 0.8,
            }
        }
        result = _run(mech.tick({"prior_results": prior}))
        # Suppression should be negative (vasodilation signal)
        assert result["baroreflex_modulation"] < 0
        # Tone should trend below resting baseline
        assert result["sympathetic_tone"] < 0.52

    def test_baroreceptor_active_maintains_tone(self):
        """When baroreceptor is active (BP normal), modulation is neutral."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {
                "baroreceptor_suppressed": False,
                "baroreflex_intensity": 0.0,
            }
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["baroreflex_modulation"] == 0.0
        assert result["sympathetic_tone"] >= 0.40

    def test_baroreflex_modulation_is_negative_when_suppressed(self):
        """Explicitly: suppressed baroreceptor → negative modulation."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {
                "baroreceptor_suppressed": True,
                "baroreflex_intensity": 1.0,
            }
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["baroreflex_modulation"] < 0


class TestThreatOverride:
    """CRH/stress overrides baroreflex to maintain BP for defense."""

    def test_high_crh_activates_threat_override(self):
        """CRH above threshold activates threat override."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {"baroreceptor_suppressed": True, "baroreflex_intensity": 0.9},
            "StressActivationAxis": {"crh_level": 0.75},
            "GutSignalRelay": {"gut_distress": 0.0},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["threat_activated"] is True

    def test_gut_distress_activates_threat_override(self):
        """Gut distress above threshold also triggers override."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {"baroreceptor_suppressed": False, "baroreflex_intensity": 0.0},
            "StressActivationAxis": {"crh_level": 0.0},
            "GutSignalRelay": {"gut_distress": 0.70},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["threat_activated"] is True

    def test_subthreshold_stress_no_override(self):
        """Low-level stress does not trigger override."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {"baroreceptor_suppressed": True, "baroreflex_intensity": 0.5},
            "StressActivationAxis": {"crh_level": 0.20},
            "GutSignalRelay": {"gut_distress": 0.10},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["threat_activated"] is False

    def test_threat_restores_tone_against_baroreflex(self):
        """Threat override should keep tone elevated even if baroreflex tried to suppress."""
        mech = SympatheticVasomotorController()
        prior = {
            "BaroreflexBalancer": {"baroreceptor_suppressed": True, "baroreflex_intensity": 0.9},
            "StressActivationAxis": {"crh_level": 0.80},
            "GutSignalRelay": {"gut_distress": 0.0},
        }
        result = _run(mech.tick({"prior_results": prior}))
        # Threat should win — tone should be high
        assert result["sympathetic_tone"] > 0.55


class TestArousalCoupling:
    """High arousal elevates sympathetic tone via LC-NE → RVLM coupling."""

    def test_high_arousal_elevates_tone(self):
        """High arousal level should increase sympathetic tone above resting."""
        mech = SympatheticVasomotorController()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.90},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["sympathetic_tone"] > 0.52

    def test_low_arousal_lowers_tone(self):
        """Low arousal should decrease tone below resting baseline."""
        mech = SympatheticVasomotorController()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.10},
        }
        result = _run(mech.tick({"prior_results": prior}))
        assert result["sympathetic_tone"] < 0.52


class TestConvergenceDynamics:
    """Tone converges smoothly toward target — doesn't jump."""

    def test_tone_changes_gradually(self):
        """Sympathetic tone should not jump more than 0.1 in a single tick."""
        mech = SympatheticVasomotorController()
        _run(mech.tick({"prior_results": {}}))  # settle
        prev_tone = mech.state["sympathetic_tone"]
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BaroreflexBalancer": {
                            "baroreceptor_suppressed": True,
                            "baroreflex_intensity": 1.0,
                        }
                    }
                }
            )
        )
        delta = abs(result["sympathetic_tone"] - prev_tone)
        assert delta < 0.10, f"Tone jumped {delta}, expected gradual convergence"


class TestOutputEnrichmentKeys:
    """All required output keys are present."""

    def test_required_keys_present(self):
        """Every output key required by brain_runner enrichment is present."""
        mech = SympatheticVasomotorController()
        result = _run(mech.tick({"prior_results": {}}))
        required = [
            "sympathetic_tone",
            "vasoconstrictor_bp_contribution",
            "baroreflex_modulation",
            "threat_activated",
            "mean_arterial_pressure_index",
        ]
        for key in required:
            assert key in result, f"Missing output key: {key}"

    def test_all_values_are_numeric(self):
        """All output values should be numeric (float or bool)."""
        mech = SympatheticVasomotorController()
        result = _run(mech.tick({"prior_results": {}}))
        for key, value in result.items():
            assert isinstance(value, (float, bool)), f"Key {key} has non-numeric value: {value}"
