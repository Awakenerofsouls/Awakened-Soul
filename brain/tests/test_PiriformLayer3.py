"""Behavioral tests for PiriformLayer3."""
import asyncio
from brain.mechanisms.PiriformLayer3 import PiriformLayer3


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_pir2_drives_pir3_outputs():
    m = PiriformLayer3()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformLayer2": {"pir2_drive": 0.65},
            "EndopiriformNucleus": {"piriform_feedback_command": 0.45},
        })
    assert out["pir3_drive"] > 0.30
    assert out["ec_drive_signal"] > 0.20


def test_appetitive_drives_ofc_hedonic():
    m = PiriformLayer3()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformLayer2": {"pir2_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["ofc_drive_signal"] > 0.30
    assert out["hedonic_signal"] > 0.20


def test_aversive_drives_amygdala():
    m = PiriformLayer3()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformLayer2": {"pir2_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["amygdala_drive_signal"] > 0.30


def test_quiet_no_input():
    m = PiriformLayer3()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pir3_state"] == "quiet"
