"""Behavioral tests for EndopiriformNucleus."""
import asyncio
from brain.limbic.EndopiriformNucleus import EndopiriformNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_piriform_input_engages_en():
    m = EndopiriformNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformCortex": {"pir_drive": 0.75},
            "AnteriorOlfactoryNucleus": {"aon_drive": 0.45},
        })
    assert out["en_drive"] > 0.30
    assert out["piriform_feedback_command"] > 0.30


def test_strong_pir_drives_recurrent_excitation():
    m = EndopiriformNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformCortex": {"pir_drive": 0.85},
            "OlfactoryTubercleStriatal": {"ot_drive": 0.55},
        })
    assert out["recurrent_excitation_signal"] > 0.30


def test_bla_input_drives_amygdala_pathway():
    m = EndopiriformNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PiriformCortex": {"pir_drive": 0.55},
            "BasalAmygdala": {"bla_drive": 0.65},
        })
    assert out["amygdala_olfactory_drive"] > 0.30


def test_quiet_no_input():
    m = EndopiriformNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["en_state"] == "quiet"
