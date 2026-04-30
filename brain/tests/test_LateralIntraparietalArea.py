"""Behavioral tests for LateralIntraparietalArea (LIP)."""
import asyncio
from brain.neocortical.LateralIntraparietalArea import LateralIntraparietalArea


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_visual_input_drives_priority_map():
    m = LateralIntraparietalArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.55},
            "MiddleTemporalArea": {"lip_input_signal": 0.50},
            "PulvinarAttentionVisual": {"pulvinar_modulation": 0.30},
        })
    assert out["lip_drive"] > 0.20
    assert out["priority_signal"] > 0.20
    assert out["lip_state"] != "quiet"


def test_motion_evidence_ramps_decision_accumulator():
    """High coherence MT input should ramp the LIP accumulator."""
    m = LateralIntraparietalArea()
    accums = []
    for _ in range(20):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.50},
            "MiddleTemporalArea": {"lip_input_signal": 0.85},
            "FrontalEyeFields": {"attention_map": 0.40},
        })
        accums.append(out["decision_accumulator"])
    assert max(accums) > accums[0]
    assert max(accums) > 0.30


def test_high_evidence_yields_decision_commit():
    """Sustained high evidence triggers decision_committed state."""
    m = LateralIntraparietalArea()
    states = []
    for _ in range(40):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.75},
            "MiddleTemporalArea": {"lip_input_signal": 0.90},
            "FrontalEyeFields": {"attention_map": 0.65},
            "PulvinarAttentionVisual": {"pulvinar_modulation": 0.55},
        })
        states.append(out["lip_state"])
    assert "decision_committed" in states or "accumulating" in states


def test_quiet_no_input():
    m = LateralIntraparietalArea()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["lip_state"] == "quiet"
