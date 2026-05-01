"""Behavioral tests for SuperiorColliculusOrient."""
import asyncio
from brain.mechanisms.SuperiorColliculusOrient import SuperiorColliculusOrient


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_fef_drives_saccade():
    """Wurtz 1980: FEF top-down drives SC saccade output."""
    m = SuperiorColliculusOrient()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"v1_drive": 0.45},
            "FrontalEyeFields": {"fef_drive": 0.75},
        })
    assert out["sc_drive"] > 0.20
    assert out["saccade_command"] > 0.30


def test_looming_threat_drives_escape():
    """Comoli 2003 + Wei 2015: looming visual + aversive → escape."""
    m = SuperiorColliculusOrient()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"v1_drive": 0.75},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"aversive_signal": 0.75, "valence_intensity": 0.75,
                                "valence_sign": -1},
        })
    assert out["looming_response"] > 0.30
    assert out["escape_command"] > 0.30
    assert out["sc_state"] == "escape"


def test_aversive_no_strong_visual_freezes():
    """When aversive without strong looming → freezing rather than escape."""
    m = SuperiorColliculusOrient()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"v1_drive": 0.20},  # weak visual
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "ValenceTagger": {"aversive_signal": 0.65},
        })
    # Either freezing or quiet — escape should not win
    assert out["escape_command"] < out["freezing_command"]


def test_quiet_no_input():
    m = SuperiorColliculusOrient()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["sc_state"] == "quiet"
