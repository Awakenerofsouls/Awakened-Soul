"""Behavioral tests for NucleusOfDiagonalBandHorizontal."""
import asyncio
from brain.mechanisms.NucleusOfDiagonalBandHorizontal import NucleusOfDiagonalBandHorizontal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_olfactory_input_engages_ach():
    m = NucleusOfDiagonalBandHorizontal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["hdbb_drive"] > 0.30
    assert out["ob_ach_signal"] > 0.20
    assert out["piriform_ach_signal"] > 0.20


def test_discrimination_gain_elevated():
    m = NucleusOfDiagonalBandHorizontal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.75},
            "ArousalRegulator": {"tonic_level": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.45},
        })
    assert out["odor_discrimination_gain"] > 0.20
    assert out["hdbb_state"] in ("ach_active", "discrimination_high")


def test_motivation_amplifies_drive():
    m = NucleusOfDiagonalBandHorizontal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.45},
            "BasolateralAmygdala": {"bla_drive": 0.65},
        })
    assert out["hdbb_drive"] > 0.20


def test_quiet_no_input():
    m = NucleusOfDiagonalBandHorizontal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["hdbb_state"] == "quiet"
