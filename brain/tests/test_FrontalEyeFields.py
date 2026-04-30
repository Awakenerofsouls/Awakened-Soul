"""Behavioral tests for FrontalEyeFields (FEF)."""
import asyncio
from brain.neocortical.FrontalEyeFields import FrontalEyeFields


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_lip_drives_fef_target_selection():
    m = FrontalEyeFields()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralIntraparietalArea": {"priority_signal": 0.65},
            "VisualAreaV4": {"v4_drive": 0.50},
        })
    assert out["fef_drive"] > 0.25
    assert out["target_selection"] > 0.15
    assert out["fef_state"] != "quiet"


def test_high_priority_yields_saccade_prep():
    m = FrontalEyeFields()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "LateralIntraparietalArea": {"priority_signal": 0.85},
            "VisualAreaV4": {"v4_drive": 0.70},
            "MiddleTemporalArea": {"lip_input_signal": 0.60},
        })
    assert out["saccade_vector_signal"] > 0.40
    assert out["fef_state"] in ("saccade_prep", "engaged")


def test_attention_map_modulates_v4():
    """FEF → V4 attentional projection (Moore 2003)."""
    m = FrontalEyeFields()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralIntraparietalArea": {"priority_signal": 0.55},
            "VisualAreaV4": {"v4_drive": 0.55},
        })
    assert out["attention_map"] > 0.20
    assert out["v4_modulation"] > 0.15


def test_quiet_no_input():
    m = FrontalEyeFields()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["fef_state"] == "quiet"
