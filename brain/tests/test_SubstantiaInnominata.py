"""Behavioral tests for SubstantiaInnominata."""
import asyncio
from brain.mechanisms.SubstantiaInnominata import SubstantiaInnominata


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_arousal_drives_tonic_ach():
    m = SubstantiaInnominata()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.45},
        })
    assert out["si_drive"] > 0.30
    assert out["cortical_ach_tone"] > 0.20


def test_phasic_release_on_intensity_change():
    m = SubstantiaInnominata()
    # Establish baseline
    for _ in range(5):
        _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.40},
            "ValenceTagger": {"valence_intensity": 0.10},
        })
    # Sudden intensity jump
    out = _tick(m, {
        "ArousalRegulator": {"tonic_level": 0.40},
        "ValenceTagger": {"valence_intensity": 0.85},
        "BasolateralAmygdala": {"bla_drive": 0.55},
    })
    assert out["cortical_ach_phasic"] > 0.30


def test_attention_gain_with_arousal_and_salience():
    m = SubstantiaInnominata()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55},
        })
    assert out["attention_gain_signal"] > 0.20


def test_quiet_no_input():
    m = SubstantiaInnominata()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["si_state"] == "quiet"
