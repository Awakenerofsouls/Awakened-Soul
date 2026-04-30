"""Behavioral tests for PosteriorHypothalamus."""
import asyncio
from brain.subcortical.PosteriorHypothalamus import PosteriorHypothalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aggression_and_lhb_drive_panic():
    m = PosteriorHypothalamus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "AnteriorHypothalamus": {"ah_drive": 0.80},
            "LateralHabenula": {"lhb_drive": 0.75},
            "DorsomedialHypothalamus": {"dmh_drive": 0.60},
        })
    assert out["ph_drive"] > 0.40
    assert out["panic_defense_signal"] > 0.30
    assert out["ph_state"] in (
        "panic_defense", "sympathetic_burst", "arousal"
    )


def test_lc_drives_arousal():
    m = PosteriorHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LocusCoeruleusCore": {"lc_drive": 0.80},
        })
    assert out["arousal_signal"] > 0.30


def test_sympathetic_cardiovascular_link():
    m = PosteriorHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsomedialHypothalamus": {"dmh_drive": 0.65},
            "ParaventricularNucleusHypothalamus": {"pvn_drive": 0.50},
        })
    # cardiovascular tracks sympathetic
    assert out["cardiovascular_signal"] >= out["sympathetic_activation"] * 0.5


def test_quiet_no_input():
    m = PosteriorHypothalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ph_state"] == "quiet"
