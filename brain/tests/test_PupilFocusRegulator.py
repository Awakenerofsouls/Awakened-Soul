"""Behavioral tests for PupilFocusRegulator."""
import asyncio
from brain.foundational.PupilFocusRegulator import PupilFocusRegulator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_light_constricts_pupil():
    """McDougal 2015: pretectal light input → EW → pupil constriction."""
    m = PupilFocusRegulator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PretectalPupillaryReflex": {"opn_drive": 0.85},
            "ArousalRegulator": {"tonic_level": 0.40},
        })
    assert out["light_reflex_signal"] > 0.30
    assert out["pupil_state"] == "constricted"


def test_lc_arousal_dilates_pupil():
    """Joshi 2016: pupil dilation tracks LC NE firing."""
    m = PupilFocusRegulator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LocusCoeruleusCore": {"lc_drive": 0.85},
            "ArousalRegulator": {"tonic_level": 0.75},
        })
    assert out["pupil_size"] > 0.55


def test_cognitive_effort_dilates():
    """Nassar 2012: cognitive effort produces pupil dilation."""
    m = PupilFocusRegulator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LocusCoeruleusCore": {"lc_drive": 0.55},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.85,
                                                  "working_memory_signal": 0.75},
        })
    assert out["effort_dilation"] > 0.30


def test_quiet_no_input():
    m = PupilFocusRegulator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pupil_state"] in ("rest", "constricted")
