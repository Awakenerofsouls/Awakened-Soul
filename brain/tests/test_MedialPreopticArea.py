"""Behavioral tests for MedialPreopticArea."""
import asyncio
from brain.mechanisms.MedialPreopticArea import MedialPreopticArea


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_warmth_drives_heat_loss():
    m = MedialPreopticArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ThermalInput": {"warm_signal": 0.80},
            "DorsomedialHypothalamus": {"dmh_drive": 0.30},
        })
    assert out["mpoa_drive"] > 0.20
    assert out["heat_loss_signal"] > 0.30
    assert out["mpoa_state"] in ("thermoregulating", "nrem_promoting")


def test_social_input_drives_parental():
    m = MedialPreopticArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"social_signal": 0.80},
        })
    assert out["parental_signal"] > 0.30
    assert out["mpoa_state"] in ("parental", "sexual")


def test_vlpo_coupling_promotes_nrem():
    m = MedialPreopticArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentrolateralPreoptic": {"vlpo_drive": 0.70},
            "ThermalInput": {"warm_signal": 0.20},
        })
    assert out["nrem_promoter_signal"] > 0.20


def test_quiet_no_input():
    m = MedialPreopticArea()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["mpoa_state"] == "quiet"
