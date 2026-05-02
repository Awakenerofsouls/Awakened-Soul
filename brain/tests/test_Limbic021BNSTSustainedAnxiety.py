"""
Behavioral tests for SustainedAnxietyHolder (BNST).
Validates the slow-varying anxiety accumulator against
BNST neuroscience: sustained anxiety to unpredictable threat.
"""

import pytest
import asyncio
from brain.mechanisms.Limbic021BNSTSustainedAnxiety import SustainedAnxietyHolder


def make_holder():
    h = SustainedAnxietyHolder()
    h.state["anxiety_level"] = 0.15
    h.state["high_anxiety_streak"] = 0
    h.state["tick_count"] = 0
    h.state["chronic_dread"] = False
    return h


def make_input(valence_polarity=0.5, threat_signal=False, tonic_level=0.5,
               hyperaroused=False, surprise=0.0, habituation_level=0.5,
               dominant_drive="curiosity"):
    return {
        "prior_results": {
            "ValenceTagger": {"valence_polarity": valence_polarity, "threat_signal": threat_signal},
            "ArousalRegulator": {"tonic_level": tonic_level, "hyperaroused": hyperaroused},
            "PredictionErrorDrift": {"surprise_magnitude": surprise, "habituation_level": habituation_level},
            "Homeostat": {"dominant_drive": dominant_drive},
        }
    }


def run_tick(h, input_data):
    return asyncio.get_event_loop().run_until_complete(h.tick(input_data))


class TestSustainedAnxietyHolder:
    """BNST sustained anxiety tests."""

    def test_neutral_state_no_anxiety_accumulation(self):
        """Baseline inputs should not accumulate anxiety."""
        h = make_holder()
        for _ in range(10):
            run_tick(h, make_input())
        assert h.state["anxiety_level"] < 0.25

    def test_sustained_negative_valence_builds_anxiety(self):
        """20 ticks with valence=0.25 should substantially climb anxiety."""
        h = make_holder()
        for _ in range(20):
            run_tick(h, make_input(valence_polarity=0.25))
        assert h.state["anxiety_level"] > 0.35

    def test_single_negative_spike_doesnt_build_chronic_anxiety(self):
        """One tick negative then neutral should NOT hit chronic dread threshold."""
        h = make_holder()
        run_tick(h, make_input(valence_polarity=0.20))
        for _ in range(20):
            run_tick(h, make_input(valence_polarity=0.50))
        assert h.state["anxiety_level"] < 0.7
        assert not h.state["high_anxiety_streak"] >= 15

    def test_hyperarousal_accumulates_anxiety(self):
        """Tonic high + hyperaroused flag should accumulate anxiety."""
        h = make_holder()
        for _ in range(15):
            run_tick(h, make_input(tonic_level=0.75, hyperaroused=True))
        assert h.state["anxiety_level"] > 0.3

    def test_failed_habituation_specifically_triggers_anxiety(self):
        """High surprise + low habituation (unpredictable environment) should accumulate anxiety."""
        h = make_holder()
        for _ in range(15):
            run_tick(h, make_input(surprise=0.6, habituation_level=0.15))
        assert h.state["anxiety_level"] > 0.3

    def test_stability_drive_adds_to_anxiety(self):
        """Dominant stability drive should add to accumulation."""
        h = make_holder()
        base_input = make_input(valence_polarity=0.38)
        for _ in range(15):
            run_tick(h, base_input)
        anxiety_with_curiosity = h.state["anxiety_level"]

        h2 = make_holder()
        stable_input = make_input(valence_polarity=0.38, dominant_drive="stability")
        for _ in range(15):
            run_tick(h2, stable_input)
        anxiety_with_stability = h2.state["anxiety_level"]

        assert anxiety_with_stability > anxiety_with_curiosity

    def test_decay_on_calm_inputs(self):
        """Start high, feed calm inputs — anxiety should decay."""
        h = make_holder()
        h.state["anxiety_level"] = 0.7
        for _ in range(20):
            run_tick(h, make_input(valence_polarity=0.70, tonic_level=0.30))
        assert h.state["anxiety_level"] < 0.7

    def test_chronic_dread_requires_sustained_high_anxiety(self):
        """chronic_dread = True only after 15+ ticks above 0.7 threshold."""
        h = make_holder()
        assert not h.state["chronic_dread"]
        # Aggressive inputs: sustained negative valence + high tonic + hyperaroused + failed habituation
        for _ in range(20):
            run_tick(h, make_input(
                valence_polarity=0.10,
                tonic_level=0.90,
                hyperaroused=True,
                surprise=0.8,
                habituation_level=0.10,
                dominant_drive="stability"
            ))
        outputs = run_tick(h, make_input(
            valence_polarity=0.10,
            tonic_level=0.90,
            hyperaroused=True,
            surprise=0.8,
            habituation_level=0.10,
            dominant_drive="stability"
        ))
        assert h.state["anxiety_level"] > 0.7, f"anxiety must reach 0.7+, got {h.state['anxiety_level']}"
        assert outputs["chronic_dread"] is True

    def test_free_floating_fires_without_threat_signal(self):
        """High anxiety + no threat_signal → free_floating_anxiety True."""
        h = make_holder()
        h.state["anxiety_level"] = 0.5
        for _ in range(10):
            run_tick(h, make_input(valence_polarity=0.25, threat_signal=False))
        outputs = run_tick(h, make_input(valence_polarity=0.25, threat_signal=False))
        assert outputs["free_floating_anxiety"] is True

    def test_free_floating_suppressed_when_threat_signal_firing(self):
        """High anxiety WITH threat_signal → free_floating_anxiety False (threat is located)."""
        h = make_holder()
        h.state["anxiety_level"] = 0.5
        for _ in range(10):
            run_tick(h, make_input(valence_polarity=0.25, threat_signal=True))
        outputs = run_tick(h, make_input(valence_polarity=0.25, threat_signal=True))
        assert outputs["free_floating_anxiety"] is False

    def test_bnst_inhibition_activates_above_threshold(self):
        """anxiety_level > 0.5 → bnst_inhibition_active True."""
        h = make_holder()
        h.state["anxiety_level"] = 0.55
        outputs = run_tick(h, make_input())
        assert outputs["bnst_inhibition_active"] is True

    def test_enrichment_output_keys_match_brain_runner(self):
        """All four required keys present."""
        h = make_holder()
        outputs = run_tick(h, make_input())
        required = ["anxiety_level", "free_floating_anxiety", "chronic_dread", "bnst_inhibition_active"]
        for key in required:
            assert key in outputs, f"Missing output key: {key}"
