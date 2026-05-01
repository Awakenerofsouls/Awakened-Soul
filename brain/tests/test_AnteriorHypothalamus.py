"""Behavioral tests for AnteriorHypothalamus."""
import asyncio
from brain.mechanisms.AnteriorHypothalamus import AnteriorHypothalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_conspecific_pheromone_drives_attack():
    m = AnteriorHypothalamus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"med_amyg_drive": 0.85},
            "VentromedialHypothalamus": {"vmh_drive": 0.65},
            "BNSTAnterolateral": {"bnst_drive": 0.55},
        })
    assert out["ah_drive"] > 0.40
    assert out["aggression_signal"] > 0.30
    assert out["ah_state"] in ("attack", "threat_display")


def test_pag_signal_when_aggressive():
    m = AnteriorHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"med_amyg_drive": 0.70},
            "VentromedialHypothalamus": {"vmh_drive": 0.55},
        })
    assert out["pag_dorsolateral_signal"] > 0.20


def test_low_input_no_attack():
    m = AnteriorHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"med_amyg_drive": 0.10},
        })
    assert out["aggression_signal"] < 0.30
    assert out["ah_state"] != "attack"


def test_quiet_no_input():
    m = AnteriorHypothalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ah_state"] == "quiet"
