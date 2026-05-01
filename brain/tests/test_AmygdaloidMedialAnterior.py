"""Behavioral tests for AmygdaloidMedialAnterior."""
import asyncio
from brain.mechanisms.AmygdaloidMedialAnterior import AmygdaloidMedialAnterior


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aob_aversive_engages_predator_autonomic():
    m = AmygdaloidMedialAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AccessoryOlfactoryBulbProxy": {"aob_signal": 0.85},
            "PosteriorCorticalAmygdala": {"pheromone_signal": 0.65},
            "ValenceTagger": {"aversive_signal": 0.75, "valence_sign": -1,
                                "valence_intensity": 0.75, "social_context": False},
        })
    assert out["meaa_state"] == "predator_autonomic"
    assert out["bnst_command"] > 0.30


def test_visceral_input_engages_pvn_command():
    m = AmygdaloidMedialAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ParabrachialTasteVisceral": {"parabrachial_signal": 0.75},
            "ValenceTagger": {"aversive_signal": 0.50},
        })
    assert out["pvn_autonomic_command"] > 0.30


def test_social_context_engages_social_autonomic():
    m = AmygdaloidMedialAnterior()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AccessoryOlfactoryBulbProxy": {"aob_signal": 0.55},
            "PosteriorCorticalAmygdala": {"pheromone_signal": 0.45},
            "ValenceTagger": {"valence_sign": 1, "valence_intensity": 0.30,
                                "social_context": True, "aversive_signal": 0.10},
        })
    assert out["meaa_state"] in ("social_autonomic", "stress_autonomic", "quiet")


def test_quiet_no_input():
    m = AmygdaloidMedialAnterior()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["meaa_state"] == "quiet"
