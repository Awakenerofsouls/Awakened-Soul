"""Behavioral tests for RewardPredictionErrorIntegrator."""
import asyncio
from brain.integration.RewardPredictionErrorIntegrator import RewardPredictionErrorIntegrator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_unexpected_reward_burst():
    """Schultz 1997: unexpected reward → positive RPE burst."""
    m = RewardPredictionErrorIntegrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "VentralTegmentalDopamine": {"da_release": 0.75},
            "SubstantiaNigraCompacta": {"prediction_error": 0.65},
            "ValenceTagger": {"valence_intensity": 0.80, "valence_sign": 1},
        })
    assert out["integrated_rpe"] > 0.20
    assert out["rpe_state"] == "positive_burst"
    assert out["rpe_burst_detected"] is True


def test_omission_produces_negative_rpe():
    """Schultz 1997: omitted reward → pause (negative PE)."""
    m = RewardPredictionErrorIntegrator()
    # First build expectation
    for _ in range(20):
        _tick(m, {
            "ValenceTagger": {"valence_intensity": 0.70, "valence_sign": 1},
            "VentralTegmentalDopamine": {"da_release": 0.55},
        })
    # Then omit
    out = None
    for _ in range(8):
        out = _tick(m, {
            "ValenceTagger": {"valence_intensity": 0.05, "valence_sign": 0},
            "SubstantiaNigraCompacta": {"prediction_error": -0.55},
        })
    assert out["integrated_rpe"] < 0.0


def test_expected_value_grows_with_consistent_reward():
    """Rescorla-Wagner: expected value should grow over repeated reward."""
    m = RewardPredictionErrorIntegrator()
    out = None
    for _ in range(40):
        out = _tick(m, {
            "ValenceTagger": {"valence_intensity": 0.75, "valence_sign": 1},
            "VentralTegmentalDopamine": {"da_release": 0.55},
            "NucleusAccumbensCore": {"nacc_drive": 0.55},
        })
    assert out["expected_value_trace"] > 0.20


def test_quiet_no_input():
    m = RewardPredictionErrorIntegrator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["rpe_state"] == "quiet"
