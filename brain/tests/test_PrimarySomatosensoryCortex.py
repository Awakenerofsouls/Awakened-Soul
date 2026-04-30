"""Behavioral tests for PrimarySomatosensoryCortex (S1)."""
import asyncio
from brain.neocortical.PrimarySomatosensoryCortex import PrimarySomatosensoryCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_vpl_drives_s1_engagement():
    """Cutaneous body input via VPL should drive S1 area 3b/1."""
    m = PrimarySomatosensoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralPosterolateralThalamus": {"vpl_drive": 0.70},
            "DorsalColumnNuclei": {"dcn_signal": 0.60},
        })
    assert out["s1_drive"] > 0.30
    assert out["area_3b_signal"] > 0.30
    assert out["s1_state"] != "quiet"


def test_proprio_dominant_drives_3a():
    """Strong DCN proprioceptive input should preferentially engage 3a."""
    m = PrimarySomatosensoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsalColumnNuclei": {"dcn_signal": 0.80},
            "VentralPosterolateralThalamus": {"vpl_drive": 0.20},
        })
    assert out["area_3a_signal"] > 0.20


def test_vpm_face_focus():
    """VPM face input should select lip/face homunculus focus."""
    m = PrimarySomatosensoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralPosteromedialThalamus": {"vpm_drive": 0.65},
        })
    assert out["homunculus_focus"] in ("lip", "face")


def test_quiet_no_input():
    m = PrimarySomatosensoryCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["s1_state"] == "quiet"
