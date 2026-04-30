"""Behavioral tests for SeptofimbrialNucleus."""
import asyncio
from brain.limbic.SeptofimbrialNucleus import SeptofimbrialNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_hippocampal_input_drives_relay():
    m = SeptofimbrialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "SubiculumVentral": {"vsub_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": -1},
        })
    assert out["sfi_drive"] > 0.30
    assert out["hippocampal_habenular_relay"] > 0.20


def test_aversive_drives_lhb():
    m = SeptofimbrialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["lhb_drive_signal"] > 0.20


def test_intensity_drives_mhb():
    m = SeptofimbrialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "SubiculumVentral": {"vsub_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["mhb_drive_signal"] > 0.20


def test_quiet_no_input():
    m = SeptofimbrialNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["sfi_state"] == "quiet"
