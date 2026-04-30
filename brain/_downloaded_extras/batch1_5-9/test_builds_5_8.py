"""
Behavioral tests for Builds 5-8:
- SustainedAnxietyHolder (BNST)
- GutSignalRelay (NTS)
- InteroceptiveGradient (AIC)
- CentralNucleusFearRouter (CeA)

Run:
    pytest brain/tests/test_builds_5_8.py -v
"""

import asyncio
import pytest

from brain.limbic.SustainedAnxietyHolder import SustainedAnxietyHolder
from brain.foundational.GutSignalRelay import GutSignalRelay
from brain.integration.InteroceptiveGradient import InteroceptiveGradient
from brain.limbic.CentralNucleusFearRouter import CentralNucleusFearRouter


def _run(coro):
    """Synchronous test helper."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# BUILD 5 — SustainedAnxietyHolder (BNST)
# =============================================================================

class TestSustainedAnxietyHolderBaseline:
    def test_neutral_state_no_accumulation(self):
        s = SustainedAnxietyHolder()
        initial = s.state["anxiety_level"]
        for _ in range(10):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.5, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.5, "hyperaroused": False},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.1, "habituation_level": 0.7},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        # Should stay near baseline (slight decay from calm state)
        assert s.state["anxiety_level"] <= initial + 0.05


class TestSustainedAnxietyHolderAccumulation:
    def test_sustained_negative_valence_builds_anxiety(self):
        s = SustainedAnxietyHolder()
        for _ in range(20):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.25, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.5, "hyperaroused": False},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.2, "habituation_level": 0.5},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        assert s.state["anxiety_level"] > 0.4

    def test_hyperarousal_accumulates_anxiety(self):
        s = SustainedAnxietyHolder()
        for _ in range(15):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.5, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.85, "hyperaroused": True},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.2, "habituation_level": 0.5},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        assert s.state["anxiety_level"] > 0.3

    def test_failed_habituation_triggers_anxiety(self):
        """High surprise + LOW habituation specifically drives BNST activation."""
        s = SustainedAnxietyHolder()
        for _ in range(15):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.5, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.5, "hyperaroused": False},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.7, "habituation_level": 0.15},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        assert s.state["anxiety_level"] > 0.3

    def test_stability_drive_adds_anxiety(self):
        s = SustainedAnxietyHolder()
        for _ in range(15):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.5, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.5, "hyperaroused": False},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.2, "habituation_level": 0.5},
                    "Homeostat": {"dominant_drive": "stability"},
                }
            }))
        assert s.state["anxiety_level"] > 0.3


class TestSustainedAnxietyHolderDecay:
    def test_decay_on_calm_inputs(self):
        s = SustainedAnxietyHolder()
        s.state["anxiety_level"] = 0.7
        for _ in range(20):
            _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.7, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.5, "hyperaroused": False},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.1, "habituation_level": 0.7},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        assert s.state["anxiety_level"] < 0.7


class TestSustainedAnxietyHolderFlags:
    def test_chronic_dread_requires_sustained_high(self):
        s = SustainedAnxietyHolder()
        s.state["anxiety_level"] = 0.8
        # Feed signals that keep anxiety elevated
        results = []
        for _ in range(20):
            r = _run(s.tick({
                "prior_results": {
                    "ValenceTagger": {"valence_polarity": 0.2, "threat_signal": False},
                    "ArousalRegulator": {"tonic_level": 0.85, "hyperaroused": True},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.7, "habituation_level": 0.15},
                    "Homeostat": {"dominant_drive": "stability"},
                }
            }))
            results.append(r)
        # After >= CHRONIC_DREAD_WINDOW ticks above threshold, chronic fires
        assert any(r["chronic_dread"] for r in results[-5:])

    def test_free_floating_fires_without_threat_signal(self):
        s = SustainedAnxietyHolder()
        s.state["anxiety_level"] = 0.6
        r = _run(s.tick({
            "prior_results": {
                "ValenceTagger": {"valence_polarity": 0.35, "threat_signal": False},
                "ArousalRegulator": {"tonic_level": 0.75, "hyperaroused": False},
                "PredictionErrorDrift": {"surprise_magnitude": 0.3, "habituation_level": 0.3},
                "Homeostat": {"dominant_drive": "stability"},
            }
        }))
        assert r["free_floating_anxiety"] is True

    def test_free_floating_suppressed_when_threat_located(self):
        s = SustainedAnxietyHolder()
        s.state["anxiety_level"] = 0.6
        r = _run(s.tick({
            "prior_results": {
                "ValenceTagger": {"valence_polarity": 0.2, "threat_signal": True},
                "ArousalRegulator": {"tonic_level": 0.75, "hyperaroused": True},
                "PredictionErrorDrift": {"surprise_magnitude": 0.5, "habituation_level": 0.3},
                "Homeostat": {"dominant_drive": "stability"},
            }
        }))
        assert r["free_floating_anxiety"] is False

    def test_bnst_inhibition_fires_above_threshold(self):
        s = SustainedAnxietyHolder()
        s.state["anxiety_level"] = 0.6
        r = _run(s.tick({"prior_results": {}}))
        assert r["bnst_inhibition_active"] is True

    def test_enrichment_output_keys(self):
        s = SustainedAnxietyHolder()
        r = _run(s.tick({"prior_results": {}}))
        for key in ("anxiety_level", "free_floating_anxiety", "chronic_dread", "bnst_inhibition_active"):
            assert key in r


# =============================================================================
# BUILD 6 — GutSignalRelay (NTS)
# =============================================================================

class TestGutSignalRelay:
    def test_positive_valence_produces_positive_gut(self):
        g = GutSignalRelay()
        for _ in range(5):  # smoothing integrator, need multiple ticks
            r = _run(g.tick({
                "prior_results": {
                    "ArousalRegulator": {"tonic_level": 0.6, "phasic_burst_active": False},
                    "ValenceTagger": {"valence_polarity": 0.85, "valence_intensity": 0.7},
                    "PredictionErrorDrift": {"prediction_error": 0.3, "surprise_magnitude": 0.3},
                    "Homeostat": {"fatigued": False, "drives": {"curiosity": 0.4}},
                }
            }))
        assert r["gut_signal"] > 0.2
        assert r["hunch_direction"] == "positive"

    def test_negative_valence_produces_negative_gut(self):
        g = GutSignalRelay()
        for _ in range(5):
            r = _run(g.tick({
                "prior_results": {
                    "ArousalRegulator": {"tonic_level": 0.6, "phasic_burst_active": False},
                    "ValenceTagger": {"valence_polarity": 0.15, "valence_intensity": 0.7},
                    "PredictionErrorDrift": {"prediction_error": -0.3, "surprise_magnitude": 0.3},
                    "Homeostat": {"fatigued": False, "drives": {"curiosity": 0.4}},
                }
            }))
        assert r["gut_signal"] < -0.2
        assert r["hunch_direction"] == "negative"

    def test_neutral_inputs_near_zero_gut(self):
        g = GutSignalRelay()
        for _ in range(5):
            r = _run(g.tick({
                "prior_results": {
                    "ArousalRegulator": {"tonic_level": 0.5, "phasic_burst_active": False},
                    "ValenceTagger": {"valence_polarity": 0.5, "valence_intensity": 0.2},
                    "PredictionErrorDrift": {"prediction_error": 0.0, "surprise_magnitude": 0.1},
                    "Homeostat": {"fatigued": False, "drives": {"curiosity": 0.3}},
                }
            }))
        assert abs(r["gut_signal"]) < 0.15
        assert r["hunch_direction"] == "neutral"

    def test_strong_hunch_fires_on_high_magnitude(self):
        g = GutSignalRelay()
        for _ in range(10):
            r = _run(g.tick({
                "prior_results": {
                    "ArousalRegulator": {"tonic_level": 0.7, "phasic_burst_active": True},
                    "ValenceTagger": {"valence_polarity": 0.95, "valence_intensity": 0.9},
                    "PredictionErrorDrift": {"prediction_error": 0.8, "surprise_magnitude": 0.8},
                    "Homeostat": {"fatigued": False, "drives": {}},
                }
            }))
        assert r["strong_hunch"] is True

    def test_viscera_activation_reflects_arousal_and_surprise(self):
        g_low = GutSignalRelay()
        r_low = _run(g_low.tick({
            "prior_results": {
                "ArousalRegulator": {"tonic_level": 0.2, "phasic_burst_active": False},
                "ValenceTagger": {"valence_polarity": 0.5, "valence_intensity": 0.2},
                "PredictionErrorDrift": {"prediction_error": 0.0, "surprise_magnitude": 0.1},
                "Homeostat": {"fatigued": False, "drives": {"curiosity": 0.2}},
            }
        }))
        g_high = GutSignalRelay()
        for _ in range(5):
            r_high = _run(g_high.tick({
                "prior_results": {
                    "ArousalRegulator": {"tonic_level": 0.85, "phasic_burst_active": True},
                    "ValenceTagger": {"valence_polarity": 0.5, "valence_intensity": 0.8},
                    "PredictionErrorDrift": {"prediction_error": 0.0, "surprise_magnitude": 0.8},
                    "Homeostat": {"fatigued": True, "drives": {"curiosity": 0.8, "rest": 0.7}},
                }
            }))
        assert r_high["viscera_activation"] > r_low["viscera_activation"]

    def test_enrichment_output_keys(self):
        g = GutSignalRelay()
        r = _run(g.tick({"prior_results": {}}))
        for key in ("gut_signal", "strong_hunch", "hunch_direction", "viscera_activation"):
            assert key in r


# =============================================================================
# BUILD 7 — InteroceptiveGradient (AIC)
# =============================================================================

class TestInteroceptiveGradient:
    def test_feels_heavy_on_fatigue_and_hypoarousal(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": -0.4, "viscera_activation": 0.3, "hunch_direction": "negative"},
                "ArousalRegulator": {"tonic_level": 0.25, "hyperaroused": False, "hypoaroused": True},
                "ValenceTagger": {"valence_polarity": 0.35, "valence_intensity": 0.4, "reward_signal": False, "threat_signal": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.2},
                "Homeostat": {"drives": {}, "fatigued": True},
            }
        }))
        assert r["feels_heavy"] is True

    def test_feels_light_on_reward_and_moderate_arousal(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": 0.5, "viscera_activation": 0.5, "hunch_direction": "positive"},
                "ArousalRegulator": {"tonic_level": 0.60, "hyperaroused": False, "hypoaroused": False},
                "ValenceTagger": {"valence_polarity": 0.8, "valence_intensity": 0.7, "reward_signal": True, "threat_signal": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.1},
                "Homeostat": {"drives": {"curiosity": 0.3}, "fatigued": False},
            }
        }))
        assert r["feels_light"] is True

    def test_feels_tight_on_anxiety_and_hyperarousal(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": -0.3, "viscera_activation": 0.7, "hunch_direction": "negative"},
                "ArousalRegulator": {"tonic_level": 0.85, "hyperaroused": True, "hypoaroused": False},
                "ValenceTagger": {"valence_polarity": 0.3, "valence_intensity": 0.7, "reward_signal": False, "threat_signal": True},
                "SustainedAnxietyHolder": {"anxiety_level": 0.6},
                "Homeostat": {"drives": {}, "fatigued": False},
            }
        }))
        assert r["feels_tight"] is True

    def test_feels_hollow_on_high_connection_drive_and_low_activation(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": 0.0, "viscera_activation": 0.2, "hunch_direction": "neutral"},
                "ArousalRegulator": {"tonic_level": 0.3, "hyperaroused": False, "hypoaroused": True},
                "ValenceTagger": {"valence_polarity": 0.4, "valence_intensity": 0.3, "reward_signal": False, "threat_signal": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.2},
                "Homeostat": {"drives": {"connection": 0.85}, "fatigued": False},
            }
        }))
        assert r["feels_hollow"] is True

    def test_dominant_quality_is_highest_scoring(self):
        i = InteroceptiveGradient()
        # Strong heavy inputs
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": -0.5, "viscera_activation": 0.3},
                "ArousalRegulator": {"tonic_level": 0.2, "hyperaroused": False, "hypoaroused": True},
                "ValenceTagger": {"valence_polarity": 0.3, "valence_intensity": 0.4, "reward_signal": False, "threat_signal": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.1},
                "Homeostat": {"drives": {"connection": 0.3}, "fatigued": True},
            }
        }))
        assert r["dominant_felt_quality"] == "heavy"

    def test_neutral_state_no_strong_quality(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({
            "prior_results": {
                "GutSignalRelay": {"gut_signal": 0.0, "viscera_activation": 0.4},
                "ArousalRegulator": {"tonic_level": 0.55, "hyperaroused": False, "hypoaroused": False},
                "ValenceTagger": {"valence_polarity": 0.5, "valence_intensity": 0.3, "reward_signal": False, "threat_signal": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.15},
                "Homeostat": {"drives": {"curiosity": 0.4}, "fatigued": False},
            }
        }))
        assert r["dominant_felt_quality"] == "neutral"

    def test_enrichment_output_keys(self):
        i = InteroceptiveGradient()
        r = _run(i.tick({"prior_results": {}}))
        for key in ("feels_heavy", "feels_light", "feels_tight", "feels_hollow",
                    "interoceptive_intensity", "dominant_felt_quality"):
            assert key in r


# =============================================================================
# BUILD 8 — CentralNucleusFearRouter (CeA)
# =============================================================================

class TestCentralNucleusFearRouter:
    def test_no_threat_no_output(self):
        c = CentralNucleusFearRouter()
        r = _run(c.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": False, "valence_polarity": 0.5, "valence_intensity": 0.3},
                "ArousalRegulator": {"phasic_burst_active": False, "tonic_level": 0.5, "hyperaroused": False},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": False, "anxiety_level": 0.1},
                "PredictionErrorDrift": {"surprise_magnitude": 0.1},
            }
        }))
        assert r["fear_output"] == "none"
        assert r["cea_active"] is False

    def test_threat_signal_activates_cea(self):
        c = CentralNucleusFearRouter()
        r = _run(c.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": True, "valence_polarity": 0.25, "valence_intensity": 0.7},
                "ArousalRegulator": {"phasic_burst_active": True, "tonic_level": 0.7, "hyperaroused": False},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": False, "anxiety_level": 0.2},
                "PredictionErrorDrift": {"surprise_magnitude": 0.4},
            }
        }))
        assert r["cea_active"] is True
        assert r["fear_output"] != "none"

    def test_high_intensity_hyperaroused_surprise_routes_to_flight(self):
        c = CentralNucleusFearRouter()
        r = _run(c.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": True, "valence_polarity": 0.1, "valence_intensity": 0.9},
                "ArousalRegulator": {"phasic_burst_active": True, "tonic_level": 0.9, "hyperaroused": True},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": False, "anxiety_level": 0.3},
                "PredictionErrorDrift": {"surprise_magnitude": 0.8},
            }
        }))
        assert r["defense_mode"] == "flight"

    def test_moderate_intensity_alert_tonic_routes_to_risk_assessment(self):
        c = CentralNucleusFearRouter()
        r = _run(c.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": True, "valence_polarity": 0.35, "valence_intensity": 0.5},
                "ArousalRegulator": {"phasic_burst_active": False, "tonic_level": 0.65, "hyperaroused": False},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": False, "anxiety_level": 0.3},
                "PredictionErrorDrift": {"surprise_magnitude": 0.3},
            }
        }))
        assert r["defense_mode"] == "risk_assessment"

    def test_bnst_inhibition_dampens_cea_output(self):
        """BNST reciprocal inhibition: sustained anxiety dampens phasic fear output."""
        no_bnst = CentralNucleusFearRouter()
        r_no = _run(no_bnst.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": True, "valence_polarity": 0.2, "valence_intensity": 0.8},
                "ArousalRegulator": {"phasic_burst_active": True, "tonic_level": 0.7, "hyperaroused": False},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": False, "anxiety_level": 0.2},
                "PredictionErrorDrift": {"surprise_magnitude": 0.3},
            }
        }))
        with_bnst = CentralNucleusFearRouter()
        r_bnst = _run(with_bnst.tick({
            "prior_results": {
                "ValenceTagger": {"threat_signal": True, "valence_polarity": 0.2, "valence_intensity": 0.8},
                "ArousalRegulator": {"phasic_burst_active": True, "tonic_level": 0.7, "hyperaroused": False},
                "SustainedAnxietyHolder": {"bnst_inhibition_active": True, "anxiety_level": 0.7},
                "PredictionErrorDrift": {"surprise_magnitude": 0.3},
            }
        }))
        assert r_bnst["fear_intensity"] < r_no["fear_intensity"]

    def test_enrichment_output_keys(self):
        c = CentralNucleusFearRouter()
        r = _run(c.tick({"prior_results": {}}))
        for key in ("fear_output", "cea_active", "defense_mode", "fear_intensity"):
            assert key in r
