"""Behavioral tests for AmygdaloidCorticalAnterior."""
import asyncio
from brain.mechanisms.AmygdaloidCorticalAnterior import AmygdaloidCorticalAnterior


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ob_drives_odor_identity():
    m = AmygdaloidCorticalAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.75},
            "PiriformCortex": {"pir_drive": 0.55},
        })
    assert out["odor_identity_signal"] > 0.30
    assert out["aco_drive"] > 0.30


def test_aversive_odor_engages_emotion():
    m = AmygdaloidCorticalAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65},
            "PiriformCortex": {"pir_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["olfactory_emotion_signal"] > 0.30
    assert out["aco_state"] == "odor_emotion"


def test_bla_drive_scales_with_intensity():
    m = AmygdaloidCorticalAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.75, "valence_sign": 1},
        })
    assert out["bla_olfactory_drive"] > 0.30


def test_quiet_no_input():
    m = AmygdaloidCorticalAnterior()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["aco_state"] == "quiet"
