"""Behavioral tests for PaleocorticalAmygdala."""
import asyncio
from brain.limbic.PaleocorticalAmygdala import PaleocorticalAmygdala


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_predator_odor_drives_innate_fear():
    m = PaleocorticalAmygdala()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65,
                              "predator_odor_signal": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["pca_drive"] > 0.30
    assert out["innate_fear_signal"] > 0.30
    assert out["pca_state"] == "innate_fear"


def test_food_odor_drives_innate_appetitive():
    m = PaleocorticalAmygdala()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65,
                              "food_odor_signal": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["innate_appetitive_signal"] > 0.30


def test_bla_drive_when_active():
    m = PaleocorticalAmygdala()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OlfactoryBulb": {"ob_drive": 0.65,
                              "predator_odor_signal": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": -1},
        })
    assert out["bla_drive_signal"] > 0.20


def test_quiet_no_input():
    m = PaleocorticalAmygdala()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pca_state"] == "quiet"
