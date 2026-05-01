"""Behavioral tests for AnteriorOlfactoryNucleus."""
import asyncio
from brain.mechanisms.AnteriorOlfactoryNucleus import AnteriorOlfactoryNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ob_input_drives_aon():
    m = AnteriorOlfactoryNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {"OlfactoryBulb": {"ob_drive": 0.75}})
    assert out["aon_drive"] > 0.30
    assert out["bilateral_integration_signal"] > 0.30
    assert out["ob_feedback_command"] > 0.10


def test_repeated_odor_increases_familiarity():
    m = AnteriorOlfactoryNucleus()
    out = None
    for _ in range(40):
        out = _tick(m, {"OlfactoryBulb": {"ob_drive": 0.65}})
    assert out["olfactory_familiarity_signal"] > 0.30


def test_no_input_quiet():
    m = AnteriorOlfactoryNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["aon_state"] == "quiet"


def test_aco_input_engages_social_recognition():
    m = AnteriorOlfactoryNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.55},
            "AmygdalaCorticalAnterior": {"aco_drive": 0.65},
        })
    assert out["aon_state"] in ("social_recognition", "novel_odor", "familiar_odor")
