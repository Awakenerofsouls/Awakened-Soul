"""Behavioral tests for HippocampalCA3Dorsal."""
import asyncio
from brain.limbic.HippocampalCA3Dorsal import HippocampalCA3Dorsal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_dg_drives_ca3():
    m = HippocampalCA3Dorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.65},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
            "MedialSeptum": {"theta_signal": 0.55},
        })
    assert out["dca3_drive"] > 0.30
    assert out["schaffer_collateral_output"] > 0.20


def test_recurrent_attractor_builds():
    m = HippocampalCA3Dorsal()
    out = None
    for _ in range(25):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.50},
            "EntorhinalCortexGridCells": {"ec_output": 0.50},
        })
    assert out["recurrent_attractor_signal"] > 0.20


def test_low_theta_high_drive_ripple_origin():
    m = HippocampalCA3Dorsal()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.65},
            "EntorhinalCortexGridCells": {"ec_output": 0.55},
            "MedialSeptum": {"theta_signal": 0.05},
        })
    assert out["swr_origin_signal"] > 0.20


def test_quiet_no_input():
    m = HippocampalCA3Dorsal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dca3_state"] == "quiet"
