"""Behavioral tests for TuberalNucleus."""
import asyncio
from brain.subcortical.TuberalNucleus import TuberalNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aggression_inputs_drive_attack():
    m = TuberalNucleus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "AnteriorHypothalamus": {"ah_drive": 0.85},
            "VentromedialHypothalamus": {"vmh_drive": 0.75},
            "MedialAmygdalaPosterior": {"med_amyg_drive": 0.70},
        })
    assert out["tun_drive"] > 0.40
    assert out["attack_execution_signal"] > 0.30
    assert out["tun_state"] in ("intermale_attack", "predator_defense")


def test_pheromone_drives_predator_defense():
    m = TuberalNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"med_amyg_drive": 0.85},
            "LateralHabenula": {"lhb_drive": 0.70},
        })
    assert out["predator_defense_signal"] > 0.20


def test_pmv_dat_engaged_with_attack():
    m = TuberalNucleus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "AnteriorHypothalamus": {"ah_drive": 0.80},
            "VentromedialHypothalamus": {"vmh_drive": 0.65},
            "HypothalamicSupramammillary": {"sum_drive": 0.55},
        })
    assert out["pmv_dat_proxy"] > 0.30


def test_quiet_no_input():
    m = TuberalNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["tun_state"] == "quiet"
