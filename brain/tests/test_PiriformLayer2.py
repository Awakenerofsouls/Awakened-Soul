"""Behavioral tests for PiriformLayer2."""
import asyncio
from brain.mechanisms.PiriformLayer2 import PiriformLayer2


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_olfactory_input_drives_object():
    m = PiriformLayer2()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65},
            "AnteriorOlfactoryNucleus": {"aon_drive": 0.45},
        })
    assert out["pir2_drive"] > 0.30
    assert out["odor_object_signal"] > 0.20


def test_ach_increases_sparseness():
    m_no_ach = PiriformLayer2()
    out_no = None
    for _ in range(15):
        out_no = _tick(m_no_ach, {
            "OlfactoryBulb": {"ob_drive": 0.55},
        })

    m_ach = PiriformLayer2()
    out_ach = None
    for _ in range(15):
        out_ach = _tick(m_ach, {
            "OlfactoryBulb": {"ob_drive": 0.55},
            "NucleusOfDiagonalBandHorizontal": {"piriform_ach_signal": 0.65},
        })
    assert out_ach["ensemble_sparseness"] >= out_no["ensemble_sparseness"]


def test_layer3_drive_active():
    m = PiriformLayer2()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.55},
            "AnteriorOlfactoryNucleus": {"aon_drive": 0.45},
        })
    assert out["layer3_drive_signal"] > 0.20


def test_quiet_no_input():
    m = PiriformLayer2()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pir2_state"] == "quiet"
