"""Behavioral tests for MiddleTemporalArea (V5/MT)."""
import asyncio
from brain.neocortical.MiddleTemporalArea import MiddleTemporalArea


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_magno_drives_motion_response():
    m = MiddleTemporalArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"magno_to_v2": 0.70},
            "SecondaryVisualCortex": {"mt_input_signal": 0.65},
        })
    assert out["mt_drive"] > 0.25
    assert out["direction_signal"] > 0.20
    assert out["mt_state"] != "quiet"


def test_high_coherence_yields_coherent_state():
    m = MiddleTemporalArea()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrimaryVisualCortex": {"magno_to_v2": 0.85},
            "SecondaryVisualCortex": {"mt_input_signal": 0.85},
            "PulvinarAttentionVisual": {"pulvinar_modulation": 0.40},
        })
    assert out["coherence_signal"] > 0.40
    assert out["mt_state"] == "coherent_motion"


def test_optic_flow_feeds_mst_and_lip():
    m = MiddleTemporalArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"magno_to_v2": 0.60},
            "SecondaryVisualCortex": {"mt_input_signal": 0.60},
            "PulvinarAttentionVisual": {"pulvinar_modulation": 0.30},
        })
    assert out["mst_input_signal"] > 0.20
    assert out["lip_input_signal"] > 0.20


def test_quiet_no_input():
    m = MiddleTemporalArea()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["mt_state"] == "quiet"
