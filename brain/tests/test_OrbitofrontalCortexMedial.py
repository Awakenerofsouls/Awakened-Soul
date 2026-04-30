"""Behavioral tests for OrbitofrontalCortexMedial."""
import asyncio
from brain.neocortical.OrbitofrontalCortexMedial import OrbitofrontalCortexMedial


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_subjective_value_engages():
    m = OrbitofrontalCortexMedial()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusAccumbensCore": {"nac_drive": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "VentralTegmentalArea": {"da_signal": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["mofc_drive"] > 0.30
    assert out["subjective_value_signal"] > 0.20
    assert out["common_currency_value"] > 0.10
    assert out["mofc_state"] in ("valuing", "comparing")


def test_aversive_produces_negative_currency():
    m = OrbitofrontalCortexMedial()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["common_currency_value"] < 0.0


def test_variable_value_increases_risk_sensitivity():
    m = OrbitofrontalCortexMedial()
    # Alternating high/low value should grow variance
    out = None
    for i in range(40):
        intensity = 0.85 if i % 2 == 0 else 0.10
        out = _tick(m, {
            "NucleusAccumbensCore": {"nac_drive": 0.55},
            "VentralTegmentalArea": {"da_signal": intensity},
            "ValenceTagger": {"valence_intensity": intensity,
                                "valence_sign": 1},
        })
    assert out["risk_sensitivity_signal"] > 0.10


def test_quiet_no_input():
    m = OrbitofrontalCortexMedial()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["mofc_state"] == "quiet"
