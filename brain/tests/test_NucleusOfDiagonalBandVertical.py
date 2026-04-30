"""Behavioral tests for NucleusOfDiagonalBandVertical."""
import asyncio
from brain.limbic.NucleusOfDiagonalBandVertical import NucleusOfDiagonalBandVertical


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_arousal_drives_theta():
    m = NucleusOfDiagonalBandVertical()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.65},
        })
    assert out["vdbb_drive"] > 0.30
    assert out["theta_signal"] > 0.20
    assert out["vdbb_state"] in ("theta_pacing", "ach_high")


def test_ach_modulation_active():
    m = NucleusOfDiagonalBandVertical()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.55},
            "HippocampalCA3": {"ca3_output": 0.45},
        })
    assert out["ach_modulation"] > 0.20


def test_lateral_habenula_dampens_drive():
    m = NucleusOfDiagonalBandVertical()
    out_neutral = None
    for _ in range(15):
        out_neutral = _tick(m, {"ArousalRegulator": {"tonic_level": 0.55}})

    m2 = NucleusOfDiagonalBandVertical()
    out_inhib = None
    for _ in range(15):
        out_inhib = _tick(m2, {
            "ArousalRegulator": {"tonic_level": 0.55},
            "LateralHabenula": {"lhab_drive": 0.60},
        })
    assert out_inhib["vdbb_drive"] <= out_neutral["vdbb_drive"]


def test_quiet_no_input():
    m = NucleusOfDiagonalBandVertical()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vdbb_state"] == "quiet"
