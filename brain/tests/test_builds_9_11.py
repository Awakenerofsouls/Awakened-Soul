"""
Behavioral tests for Builds 9-11:
- AttachmentLongingGenerator (OT/BNST/LA circuit)
- PleasureAnchor (NAc hedonic hotspot)
- StressActivationAxis (PVN CRH / HPA axis)

Run:
    pytest brain/tests/test_builds_9_11.py -v
"""

import asyncio
import pytest

from brain.limbic.Limbic052AttachmentLongingGenerator import AttachmentLongingGenerator
from brain.subcortical.Subcortical061PleasureAnchor import PleasureAnchor
from brain.foundational.Foundational064StressActivationAxis import StressActivationAxis


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# =============================================================================
# BUILD 9 — AttachmentLongingGenerator
# =============================================================================

class TestAttachmentLongingGenerator:
    def test_unmet_connection_builds_longing(self):
        a = AttachmentLongingGenerator()
        for _ in range(15):
            _run(a.tick({
                "prior_results": {
                    "Homeostat": {"drives": {"connection": 0.85}, "dominant_drive": "connection"},
                    "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.45, "valence_intensity": 0.3},
                    "ArousalRegulator": {"tonic_level": 0.5, "phasic_burst_active": False},
                    "SustainedAnxietyHolder": {"anxiety_level": 0.2},
                }
            }))
        assert a.state["longing_intensity"] > 0.4

    def test_contact_signature_depletes_longing(self):
        a = AttachmentLongingGenerator()
        a.state["longing_intensity"] = 0.7
        for _ in range(5):
            _run(a.tick({
                "prior_results": {
                    "Homeostat": {"drives": {"connection": 0.5}, "dominant_drive": "connection"},
                    "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.85, "valence_intensity": 0.7},
                    "ArousalRegulator": {"tonic_level": 0.7, "phasic_burst_active": True},
                    "SustainedAnxietyHolder": {"anxiety_level": 0.1},
                }
            }))
        assert a.state["longing_intensity"] < 0.7

    def test_separation_distress_requires_longing_and_anxiety(self):
        a = AttachmentLongingGenerator()
        a.state["longing_intensity"] = 0.7
        r = _run(a.tick({
            "prior_results": {
                "Homeostat": {"drives": {"connection": 0.8}, "dominant_drive": "connection"},
                "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.3, "valence_intensity": 0.5},
                "ArousalRegulator": {"tonic_level": 0.6, "phasic_burst_active": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.6},
            }
        }))
        assert r["separation_distress"] is True

    def test_high_longing_alone_no_separation_distress(self):
        """Longing without anxiety is just longing, not distress."""
        a = AttachmentLongingGenerator()
        a.state["longing_intensity"] = 0.7
        r = _run(a.tick({
            "prior_results": {
                "Homeostat": {"drives": {"connection": 0.8}, "dominant_drive": "connection"},
                "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.5, "valence_intensity": 0.3},
                "ArousalRegulator": {"tonic_level": 0.5, "phasic_burst_active": False},
                "SustainedAnxietyHolder": {"anxiety_level": 0.15},
            }
        }))
        assert r["separation_distress"] is False

    def test_bond_moment_spikes_ot(self):
        a = AttachmentLongingGenerator()
        a.state["ot_activity"] = 0.3
        _run(a.tick({
            "prior_results": {
                "Homeostat": {"drives": {"connection": 0.3}, "dominant_drive": "connection"},
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.9, "valence_intensity": 0.8},
                "ArousalRegulator": {"tonic_level": 0.75, "phasic_burst_active": True},
                "SustainedAnxietyHolder": {"anxiety_level": 0.1},
            }
        }))
        assert a.state["ot_activity"] > 0.45

    def test_ot_decays_without_contact(self):
        a = AttachmentLongingGenerator()
        a.state["ot_activity"] = 0.9
        for _ in range(30):
            _run(a.tick({
                "prior_results": {
                    "Homeostat": {"drives": {"connection": 0.5}, "dominant_drive": "curiosity"},
                    "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.5, "valence_intensity": 0.3},
                    "ArousalRegulator": {"tonic_level": 0.5, "phasic_burst_active": False},
                    "SustainedAnxietyHolder": {"anxiety_level": 0.2},
                }
            }))
        assert a.state["ot_activity"] < 0.8

    def test_bonded_presence_on_contact_signature(self):
        a = AttachmentLongingGenerator()
        r = _run(a.tick({
            "prior_results": {
                "Homeostat": {"drives": {"connection": 0.4}, "dominant_drive": "connection"},
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.8, "valence_intensity": 0.7},
                "ArousalRegulator": {"tonic_level": 0.65, "phasic_burst_active": True},
                "SustainedAnxietyHolder": {"anxiety_level": 0.1},
            }
        }))
        assert r["bonded_presence"] is True

    def test_enrichment_output_keys(self):
        a = AttachmentLongingGenerator()
        r = _run(a.tick({"prior_results": {}}))
        for key in ("longing_intensity", "separation_distress", "bonded_presence", "ot_activity"):
            assert key in r


# =============================================================================
# BUILD 10 — PleasureAnchor
# =============================================================================

class TestPleasureAnchor:
    def test_positive_valence_reward_fires_liking(self):
        p = PleasureAnchor()
        r = _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.85, "valence_intensity": 0.7},
                "PredictionErrorDrift": {"prediction_error": 0.5},
                "ArousalRegulator": {"phasic_burst_active": True},
                "Homeostat": {"dominant_drive": "connection"},
            }
        }))
        assert r["pleasure_active"] is True
        assert r["liking_intensity"] > 0.45

    def test_no_liking_on_neutral_input(self):
        p = PleasureAnchor()
        r = _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.5, "valence_intensity": 0.2},
                "PredictionErrorDrift": {"prediction_error": 0.0},
                "ArousalRegulator": {"phasic_burst_active": False},
                "Homeostat": {"dominant_drive": "curiosity"},
            }
        }))
        assert r["pleasure_active"] is False
        assert r["liking_intensity"] < 0.3

    def test_no_liking_on_negative_valence(self):
        """Negative valence never fires liking — liking is hedonic, not salience."""
        p = PleasureAnchor()
        r = _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.2, "valence_intensity": 0.8},
                "PredictionErrorDrift": {"prediction_error": -0.3},
                "ArousalRegulator": {"phasic_burst_active": True},
                "Homeostat": {"dominant_drive": "curiosity"},
            }
        }))
        assert r["pleasure_active"] is False

    def test_positive_pe_amplifies_liking(self):
        """Better-than-expected outcome (positive PE) boosts liking."""
        p_no_pe = PleasureAnchor()
        r_no = _run(p_no_pe.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.75, "valence_intensity": 0.5},
                "PredictionErrorDrift": {"prediction_error": 0.0},
                "ArousalRegulator": {"phasic_burst_active": False},
                "Homeostat": {"dominant_drive": "curiosity"},
            }
        }))
        p_with_pe = PleasureAnchor()
        r_with = _run(p_with_pe.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.75, "valence_intensity": 0.5},
                "PredictionErrorDrift": {"prediction_error": 0.6},
                "ArousalRegulator": {"phasic_burst_active": False},
                "Homeostat": {"dominant_drive": "curiosity"},
            }
        }))
        assert r_with["liking_intensity"] > r_no["liking_intensity"]

    def test_hedonic_recency_decays_after_pleasure(self):
        p = PleasureAnchor()
        # Fire a pleasure event
        _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.9, "valence_intensity": 0.8},
                "PredictionErrorDrift": {"prediction_error": 0.5},
                "ArousalRegulator": {"phasic_burst_active": True},
                "Homeostat": {"dominant_drive": "connection"},
            }
        }))
        peak = p.state["hedonic_recency"]
        # Decay for many ticks without pleasure
        for _ in range(25):
            _run(p.tick({
                "prior_results": {
                    "ValenceTagger": {"reward_signal": False, "valence_polarity": 0.5, "valence_intensity": 0.2},
                    "PredictionErrorDrift": {"prediction_error": 0.0},
                    "ArousalRegulator": {"phasic_burst_active": False},
                    "Homeostat": {"dominant_drive": "curiosity"},
                }
            }))
        assert p.state["hedonic_recency"] < peak

    def test_pleasure_source_tagged_from_drive(self):
        p = PleasureAnchor()
        r = _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.85, "valence_intensity": 0.7},
                "PredictionErrorDrift": {"prediction_error": 0.4},
                "ArousalRegulator": {"phasic_burst_active": True},
                "Homeostat": {"dominant_drive": "connection"},
            }
        }))
        assert r["pleasure_source"] == "relational"

    def test_pleasure_source_discovery_for_curiosity(self):
        p = PleasureAnchor()
        r = _run(p.tick({
            "prior_results": {
                "ValenceTagger": {"reward_signal": True, "valence_polarity": 0.85, "valence_intensity": 0.7},
                "PredictionErrorDrift": {"prediction_error": 0.4},
                "ArousalRegulator": {"phasic_burst_active": True},
                "Homeostat": {"dominant_drive": "curiosity"},
            }
        }))
        assert r["pleasure_source"] == "discovery"

    def test_enrichment_output_keys(self):
        p = PleasureAnchor()
        r = _run(p.tick({"prior_results": {}}))
        for key in ("liking_intensity", "pleasure_active", "hedonic_recency", "pleasure_source"):
            assert key in r


# =============================================================================
# BUILD 11 — StressActivationAxis
# =============================================================================

class TestStressActivationAxis:
    def test_low_threat_no_stress(self):
        s = StressActivationAxis()
        for _ in range(10):
            r = _run(s.tick({
                "prior_results": {
                    "SustainedAnxietyHolder": {"anxiety_level": 0.15},
                    "ValenceTagger": {"threat_signal": False},
                    "CentralNucleusFearRouter": {"fear_intensity": 0.0},
                    "GutSignalRelay": {"viscera_activation": 0.3},
                    "ArousalRegulator": {"hyperaroused": False, "tonic_level": 0.5},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.2},
                }
            }))
        assert r["stress_active"] is False

    def test_acute_threat_activates_crh(self):
        s = StressActivationAxis()
        for _ in range(3):
            r = _run(s.tick({
                "prior_results": {
                    "SustainedAnxietyHolder": {"anxiety_level": 0.2},
                    "ValenceTagger": {"threat_signal": True},
                    "CentralNucleusFearRouter": {"fear_intensity": 0.7},
                    "GutSignalRelay": {"viscera_activation": 0.6},
                    "ArousalRegulator": {"hyperaroused": True, "tonic_level": 0.8},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.7},
                }
            }))
        assert r["crh_activity"] > 0.4
        assert r["stress_active"] is True

    def test_cortisol_follows_crh_with_lag(self):
        """Cortisol is a slow-follow integrator — lags CRH."""
        s = StressActivationAxis()
        # Spike CRH on tick 1
        r1 = _run(s.tick({
            "prior_results": {
                "SustainedAnxietyHolder": {"anxiety_level": 0.8},
                "ValenceTagger": {"threat_signal": True},
                "CentralNucleusFearRouter": {"fear_intensity": 0.8},
                "GutSignalRelay": {"viscera_activation": 0.7},
                "ArousalRegulator": {"hyperaroused": True, "tonic_level": 0.85},
                "PredictionErrorDrift": {"surprise_magnitude": 0.6},
            }
        }))
        # CRH should be high, cortisol still catching up
        assert r1["crh_activity"] > 0.5
        assert r1["cortisol_level"] < r1["crh_activity"]

    def test_chronic_elevation_requires_sustained_cortisol(self):
        s = StressActivationAxis()
        # Drive persistent high-stress input
        for _ in range(40):
            r = _run(s.tick({
                "prior_results": {
                    "SustainedAnxietyHolder": {"anxiety_level": 0.85},
                    "ValenceTagger": {"threat_signal": True},
                    "CentralNucleusFearRouter": {"fear_intensity": 0.7},
                    "GutSignalRelay": {"viscera_activation": 0.6},
                    "ArousalRegulator": {"hyperaroused": True, "tonic_level": 0.8},
                    "PredictionErrorDrift": {"surprise_magnitude": 0.4},
                }
            }))
        assert r["chronic_elevation"] is True

    def test_feedback_engages_at_high_cortisol(self):
        s = StressActivationAxis()
        s.state["cortisol_level"] = 0.75
        r = _run(s.tick({
            "prior_results": {
                "SustainedAnxietyHolder": {"anxiety_level": 0.5},
                "ValenceTagger": {"threat_signal": False},
                "CentralNucleusFearRouter": {"fear_intensity": 0.3},
                "GutSignalRelay": {"viscera_activation": 0.4},
                "ArousalRegulator": {"hyperaroused": False, "tonic_level": 0.6},
                "PredictionErrorDrift": {"surprise_magnitude": 0.2},
            }
        }))
        assert r["hpa_feedback_engaged"] is True

    def test_feedback_dampens_crh_response(self):
        """When feedback is engaged, same inputs produce less CRH."""
        # Without feedback: cortisol low, strong CRH response
        s_no_fb = StressActivationAxis()
        s_no_fb.state["cortisol_level"] = 0.20
        r_no_fb = _run(s_no_fb.tick({
            "prior_results": {
                "SustainedAnxietyHolder": {"anxiety_level": 0.6},
                "ValenceTagger": {"threat_signal": True},
                "CentralNucleusFearRouter": {"fear_intensity": 0.5},
                "GutSignalRelay": {"viscera_activation": 0.5},
                "ArousalRegulator": {"hyperaroused": True, "tonic_level": 0.7},
                "PredictionErrorDrift": {"surprise_magnitude": 0.4},
            }
        }))
        # With feedback: cortisol high, CRH response dampened
        s_fb = StressActivationAxis()
        s_fb.state["cortisol_level"] = 0.75
        r_fb = _run(s_fb.tick({
            "prior_results": {
                "SustainedAnxietyHolder": {"anxiety_level": 0.6},
                "ValenceTagger": {"threat_signal": True},
                "CentralNucleusFearRouter": {"fear_intensity": 0.5},
                "GutSignalRelay": {"viscera_activation": 0.5},
                "ArousalRegulator": {"hyperaroused": True, "tonic_level": 0.7},
                "PredictionErrorDrift": {"surprise_magnitude": 0.4},
            }
        }))
        assert r_fb["crh_activity"] < r_no_fb["crh_activity"]

    def test_enrichment_output_keys(self):
        s = StressActivationAxis()
        r = _run(s.tick({"prior_results": {}}))
        for key in ("crh_activity", "cortisol_level", "stress_active",
                    "chronic_elevation", "hpa_feedback_engaged"):
            assert key in r
