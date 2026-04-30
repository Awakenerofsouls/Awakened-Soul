"""Behavioral tests for PeriaqueductalGrayDefense."""
import asyncio
from brain.foundational.PeriaqueductalGrayDefense import PeriaqueductalGrayDefense


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_cea_drives_freeze():
    """Tovote 2016: CeA → vlPAG drives freezing."""
    m = PeriaqueductalGrayDefense()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CentralAmygdalaMedial": {"cea_drive": 0.75},
            "ValenceTagger": {"aversive_signal": 0.65, "valence_intensity": 0.65},
        })
    assert out["pag_drive"] > 0.30
    assert out["vlpag_immobility_analgesia"] > 0.30
    assert out["defensive_state"] in ("passive_freeze", "tonic_immobility")


def test_vmh_drives_escape():
    """Bandler 2000: VMH → dlPAG drives active escape."""
    m = PeriaqueductalGrayDefense()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialHypothalamus": {"vmhdm_defense_drive": 0.75},
            "ValenceTagger": {"aversive_signal": 0.65, "valence_intensity": 0.65},
        })
    assert out["dlpag_escape_command"] > 0.30


def test_vlpag_freeze_drives_pain_inhibition():
    """Carrive 1993: vlPAG freeze engages descending opioid analgesia."""
    m = PeriaqueductalGrayDefense()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CentralAmygdalaMedial": {"cea_drive": 0.75},
            "ValenceTagger": {"aversive_signal": 0.55},
        })
    assert out["descending_pain_inhibition"] > 0.20


def test_quiet_no_input():
    m = PeriaqueductalGrayDefense()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["defensive_state"] == "quiet"
