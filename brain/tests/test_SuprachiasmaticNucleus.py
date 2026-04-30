"""Behavioral tests for SuprachiasmaticNucleus."""
import asyncio
from brain.subcortical.SuprachiasmaticNucleus import SuprachiasmaticNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_light_entrains_pacemaker():
    m = SuprachiasmaticNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralGeniculateNucleus": {"light_signal": 0.85},
        })
    assert out["scn_drive"] > 0.30
    assert out["scn_state"] in (
        "subjective_day", "phase_shifting", "subjective_night"
    )


def test_phase_advances_with_ticks():
    m = SuprachiasmaticNucleus()
    p0 = _tick(m, {})["circadian_phase"]
    for _ in range(60):
        _tick(m, {})
    pN = _tick(m, {})["circadian_phase"]
    # Phase should have advanced
    assert pN != p0


def test_vip_signal_with_light():
    m = SuprachiasmaticNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralGeniculateNucleus": {"light_signal": 0.70},
        })
    assert out["vip_signal"] > 0.20


def test_quiet_no_input():
    m = SuprachiasmaticNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["scn_state"] == "quiet"
