"""Behavioral tests for AmygdalostriatalTransition."""
import asyncio
from brain.mechanisms.AmygdalostriatalTransition import AmygdalostriatalTransition


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_appetitive_engages_appetitive_action():
    m = AmygdalostriatalTransition()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasalAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["astr_state"] == "appetitive_action"
    assert out["nac_motivation_command"] > 0.20


def test_aversive_engages_aversive_action():
    m = AmygdalostriatalTransition()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CentralAmygdalaMedial": {"cem_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["astr_state"] == "aversive_action"
    assert out["valence_motor_translation"] > 0.20


def test_vp_command_active_with_strong_input():
    m = AmygdalostriatalTransition()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasalAmygdala": {"bla_drive": 0.75},
            "CentralAmygdalaMedial": {"cem_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.75, "valence_sign": -1},
        })
    assert out["vp_action_command"] > 0.30


def test_quiet_no_input():
    m = AmygdalostriatalTransition()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["astr_state"] == "quiet"
