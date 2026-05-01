"""Behavioral tests for ParatenialNucleus."""
import asyncio
from brain.mechanisms.ParatenialNucleus import ParatenialNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_amygdala_drives_salience():
    m = ParatenialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "CentralAmygdalaMedial": {"cea_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["pt_drive"] > 0.30
    assert out["salience_relay_signal"] > 0.30
    assert out["pt_state"] == "salience_relay"


def test_nac_signal_when_intense():
    m = ParatenialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65},
        })
    assert out["nac_drive_signal"] > 0.20


def test_arousal_drives_pfc():
    m = ParatenialNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.45},
            "ArousalRegulator": {"tonic_level": 0.65},
        })
    assert out["pfc_drive_signal"] > 0.20


def test_quiet_no_input():
    m = ParatenialNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pt_state"] == "quiet"
