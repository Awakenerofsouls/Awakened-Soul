"""Behavioral tests for ParaventricularNucleusThalamusAnterior."""
import asyncio
from brain.mechanisms.ParaventricularNucleusThalamusAnterior import ParaventricularNucleusThalamusAnterior


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_appetitive_engages_reward_prediction():
    m = ParaventricularNucleusThalamusAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HypothalamicLateral": {"lh_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["apvt_drive"] > 0.30
    assert out["reward_prediction_signal"] > 0.20
    assert out["apvt_state"] in ("reward_predictive", "appetitive")


def test_homeostatic_relay_active():
    m = ParaventricularNucleusThalamusAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HypothalamicLateral": {"lh_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.45},
        })
    assert out["homeostatic_relay"] > 0.20


def test_nac_drive_with_reward():
    m = ParaventricularNucleusThalamusAnterior()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "HypothalamicLateral": {"lh_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["nac_appetitive_drive"] > 0.20


def test_quiet_no_input():
    m = ParaventricularNucleusThalamusAnterior()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["apvt_state"] == "quiet"
