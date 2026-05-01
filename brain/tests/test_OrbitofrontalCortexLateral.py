"""Behavioral tests for OrbitofrontalCortexLateral."""
import asyncio
from brain.mechanisms.OrbitofrontalCortexLateral import OrbitofrontalCortexLateral


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_outcome_identity_engages():
    m = OrbitofrontalCortexLateral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.65},
            "PiriformLayer3": {"ofc_drive_signal": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["lofc_drive"] > 0.30
    assert out["outcome_identity_signal"] > 0.30
    assert out["lofc_state"] in ("outcome_active", "expectancy")


def test_satiety_devalues_outcome():
    m = OrbitofrontalCortexLateral()
    # Sustained appetitive consumption — satiety should build, devalue
    out = None
    for _ in range(80):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.65},
            "PiriformLayer3": {"ofc_drive_signal": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["devaluation_sensitivity"] > 0.20


def test_bla_update_active_with_cue():
    m = OrbitofrontalCortexLateral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["bla_value_update_signal"] > 0.20


def test_quiet_no_input():
    m = OrbitofrontalCortexLateral()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["lofc_state"] == "quiet"
