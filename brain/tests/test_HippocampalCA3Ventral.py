"""Behavioral tests for HippocampalCA3Ventral."""
import asyncio
from brain.limbic.HippocampalCA3Ventral import HippocampalCA3Ventral


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aversive_completes_fear():
    m = HippocampalCA3Ventral()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.55},
            "LateralEntorhinalCortex": {"lec_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["vca3_state"] == "fear_completing"
    assert out["valence_bound_signal"] > 0.20


def test_appetitive_completes_reward():
    m = HippocampalCA3Ventral()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.55},
            "LateralEntorhinalCortex": {"lec_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["vca3_state"] == "reward_completing"


def test_schaffer_active_when_engaged():
    m = HippocampalCA3Ventral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DentateGyrusPatternSep": {"dg_drive": 0.55},
            "LateralEntorhinalCortex": {"lec_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": -1},
        })
    assert out["ventral_schaffer_output"] > 0.20


def test_quiet_no_input():
    m = HippocampalCA3Ventral()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vca3_state"] == "quiet"
