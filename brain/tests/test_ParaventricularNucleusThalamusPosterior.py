"""Behavioral tests for ParaventricularNucleusThalamusPosterior."""
import asyncio
from brain.limbic.ParaventricularNucleusThalamusPosterior import ParaventricularNucleusThalamusPosterior


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aversive_engages_cea_pathway():
    m = ParaventricularNucleusThalamusPosterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "HypothalamicLateral": {"lh_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["ppvt_drive"] > 0.30
    assert out["cea_drive_signal"] > 0.30
    assert out["fear_memory_signal"] > 0.20


def test_chronic_stress_accumulates():
    m = ParaventricularNucleusThalamusPosterior()
    out = None
    for _ in range(80):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "HypothalamicLateral": {"lh_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["chronic_stress_load"] > 0.10


def test_bnst_drive_with_aversive():
    m = ParaventricularNucleusThalamusPosterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["bnst_drive_signal"] > 0.20


def test_quiet_no_input():
    m = ParaventricularNucleusThalamusPosterior()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ppvt_state"] == "quiet"
