"""Behavioral tests for AllostaticPredictiveAnticipator."""
import asyncio
from brain.mechanisms.AllostaticPredictiveAnticipator import AllostaticPredictiveAnticipator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_demand_predicted_from_circadian_and_state():
    """Sterling 2012: predicted demand reflects context, not just current state."""
    m = AllostaticPredictiveAnticipator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CircadianTimer": {"circadian_phase": 0.5},  # peak demand phase
            "ArcuateAgRP": {"feeding_motivation": 0.55},
            "ValenceTagger": {"valence_intensity": 0.45},
        })
    assert out["predicted_demand"] > 0.20
    assert out["regulatory_state"] in ("anticipating", "stable")


def test_chronic_unresolved_error_builds_load():
    """McEwen 1998: sustained prediction error → allostatic load."""
    m = AllostaticPredictiveAnticipator()
    out = None
    # Drive sustained mismatch: predict low (midnight phase, low feeding)
    # but real demand is high (high cortisol + high interoceptive)
    for _ in range(80):
        out = _tick(m, {
            "CircadianTimer": {"circadian_phase": 0.0},  # low predicted
            "ArcuateAgRP": {"feeding_motivation": 0.05},
            "InsulaAnterior": {"aic_drive": 0.85},        # high actual
            "InsulaPosterior": {"posterior_insula_drive": 0.75},
            "ParaventricularNucleusHypothalamus": {"gr_feedback_load": 0.65},
            "ValenceTagger": {"aversive_signal": 0.65, "valence_intensity": 0.65},
        })
    assert out["allostatic_load"] > 0.10


def test_prediction_error_signed_correctly():
    """When actual > predicted, error is positive (under-predicted)."""
    m = AllostaticPredictiveAnticipator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "CircadianTimer": {"circadian_phase": 0.0},  # low predicted demand
            "InsulaAnterior": {"aic_drive": 0.85},        # high actual
            "InsulaPosterior": {"posterior_insula_drive": 0.65},
            "ParaventricularNucleusHypothalamus": {"gr_feedback_load": 0.55},
        })
    assert out["prediction_error"] > 0.0  # positive — under-predicted


def test_anticipation_grows_with_predictable_demand():
    """Anticipatory adjustment scales with predicted demand."""
    m_low = AllostaticPredictiveAnticipator()
    out_low = None
    for _ in range(15):
        out_low = _tick(m_low, {
            "CircadianTimer": {"circadian_phase": 0.0},  # low demand phase
            "ArcuateAgRP": {"feeding_motivation": 0.10},
        })

    m_high = AllostaticPredictiveAnticipator()
    out_high = None
    for _ in range(15):
        out_high = _tick(m_high, {
            "CircadianTimer": {"circadian_phase": 0.5},  # peak demand
            "ArcuateAgRP": {"feeding_motivation": 0.65},
            "ValenceTagger": {"valence_intensity": 0.55},
        })
    assert out_high["anticipatory_adjustment"] > out_low["anticipatory_adjustment"]


def test_quiet_no_input():
    m = AllostaticPredictiveAnticipator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["regulatory_state"] in ("quiet", "stable")
