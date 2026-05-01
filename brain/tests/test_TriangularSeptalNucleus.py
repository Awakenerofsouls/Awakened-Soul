"""Behavioral tests for TriangularSeptalNucleus."""
import asyncio
from brain.mechanisms.TriangularSeptalNucleus import TriangularSeptalNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_septofimbrial_drives_substance_p():
    m = TriangularSeptalNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SeptofimbrialNucleus": {"sfi_drive": 0.65},
        })
    assert out["ts_drive"] > 0.20
    assert out["mhb_substance_p_signal"] > 0.20


def test_aversive_relay_active():
    m = TriangularSeptalNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SeptofimbrialNucleus": {"sfi_drive": 0.55},
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "HypothalamicLateral": {"lh_drive": 0.45},
        })
    assert out["aversive_relay_signal"] > 0.20
    assert out["ts_state"] == "aversive_active"


def test_vca1_alone_some_drive():
    m = TriangularSeptalNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
        })
    assert out["ts_drive"] > 0.20


def test_quiet_no_input():
    m = TriangularSeptalNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ts_state"] == "quiet"
