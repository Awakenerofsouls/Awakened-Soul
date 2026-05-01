"""Behavioral tests for SecondarySomatosensoryCortex (S2)."""
import asyncio
from brain.mechanisms.SecondarySomatosensoryCortex import SecondarySomatosensoryCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_s1_drive_engages_s2():
    """Sustained S1 area-3b output should engage S2."""
    m = SecondarySomatosensoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimarySomatosensoryCortex": {
                "s1_drive": 0.65,
                "area_2_signal": 0.45,
            },
        })
    assert out["s2_drive"] > 0.30
    assert out["bilateral_integration"] > 0.20
    assert out["s2_state"] != "quiet"


def test_strong_a2_drives_object_recognition():
    """Deep area-2 input drives shape/object recognition (Hsiao 2008)."""
    m = SecondarySomatosensoryCortex()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrimarySomatosensoryCortex": {
                "s1_drive": 0.75,
                "area_2_signal": 0.70,
            },
            "VentralPosterolateralThalamus": {"vpl_drive": 0.50},
        })
    assert out["tactile_object_signal"] > 0.30
    assert out["shape_recognition"] > 0.10


def test_decision_correlate_present_when_active():
    """Romo 2002 — S2 carries decision correlate during active discrimination."""
    m = SecondarySomatosensoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimarySomatosensoryCortex": {
                "s1_drive": 0.55,
                "area_2_signal": 0.30,
            },
        })
    assert out["decision_correlate"] > 0.15


def test_quiet_no_input():
    m = SecondarySomatosensoryCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["s2_state"] == "quiet"
