"""Behavioral tests for VentrolateralPrefrontalCortex."""
import asyncio
from brain.mechanisms.VentrolateralPrefrontalCortex import VentrolateralPrefrontalCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_stop_cue_engages_inhibition():
    m = VentrolateralPrefrontalCortex()
    out = None
    for _ in range(12):
        out = _tick(m, {
            "StopSignal": {"stop_cue": 0.85},
            "AnteriorCingulate": {"conflict_signal": 0.50},
        })
    assert out["inhibition_signal"] > 0.45
    assert out["response_brake"] > 0.45
    assert out["vlpfc_state"] == "stopping"


def test_semantic_competition_drives_selection():
    m = VentrolateralPrefrontalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "TemporalPole": {"semantic_drive": 0.75},
            "AnteriorCingulate": {"conflict_signal": 0.70},
            "DorsolateralPrefrontalCortex": {"top_down_bias": 0.55},
        })
    assert out["semantic_selection"] > 0.30
    assert out["vlpfc_state"] in ("selecting", "speaking")


def test_language_input_engages_broca():
    m = VentrolateralPrefrontalCortex()
    out = None
    for _ in range(12):
        out = _tick(m, {
            "Language": {"language_signal": 0.70},
            "DorsolateralPrefrontalCortex": {"top_down_bias": 0.40},
        })
    assert out["broca_unification"] > 0.30


def test_quiet_no_input():
    m = VentrolateralPrefrontalCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vlpfc_state"] == "quiet"
