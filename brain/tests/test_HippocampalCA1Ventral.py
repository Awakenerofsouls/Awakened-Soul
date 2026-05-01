"""Behavioral tests for HippocampalCA1Ventral."""
import asyncio
from brain.mechanisms.HippocampalCA1Ventral import HippocampalCA1Ventral


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aversive_engages_fear_context():
    m = HippocampalCA1Ventral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3": {"ca3_output": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1,
                                "aversive_signal": 0.65},
        })
    assert out["vca1_state"] == "fear_context"
    assert out["bla_contextual_fear_drive"] > 0.20
    assert out["bnst_anxiety_drive"] > 0.20


def test_appetitive_engages_reward_context():
    m = HippocampalCA1Ventral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3": {"ca3_output": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["vca1_state"] == "reward_context"
    assert out["nac_reward_context_drive"] > 0.20


def test_neutral_context_state():
    m = HippocampalCA1Ventral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3": {"ca3_output": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
            "ValenceTagger": {"valence_intensity": 0.10, "valence_sign": 0},
        })
    assert out["vca1_state"] in ("neutral_context", "quiet")


def test_quiet_no_input():
    m = HippocampalCA1Ventral()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vca1_state"] == "quiet"
