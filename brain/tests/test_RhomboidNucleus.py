"""Behavioral tests for RhomboidNucleus."""
import asyncio
from brain.mechanisms.RhomboidNucleus import RhomboidNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_pfc_and_hpc_drive_coordination():
    m = RhomboidNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.65},
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.55},
            "MedialSeptum": {"theta_signal": 0.55},
        })
    assert out["rh_drive"] > 0.30
    assert out["pfc_hpc_coordination_signal"] > 0.10


def test_working_memory_engages():
    m = RhomboidNucleus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.75},
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.65},
            "MedialSeptum": {"theta_signal": 0.65},
        })
    assert out["working_memory_signal"] > 0.20


def test_theta_synced_state():
    m = RhomboidNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.45},
            "MedialSeptum": {"theta_signal": 0.65},
        })
    assert out["rh_drive"] > 0.20


def test_quiet_no_input():
    m = RhomboidNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["rh_state"] == "quiet"
