"""Behavioral tests for LateralPosteriorThalamus."""
import asyncio
from brain.mechanisms.LateralPosteriorThalamus import LateralPosteriorThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_visual_drive_engages_lp():
    """Strong SC + V1 + cortical input should engage LP visuospatial relay."""
    m = LateralPosteriorThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SuperiorColliculus": {"visual_signal": 0.60},
            "V1": {"layer5_output": 0.55},
            "V2": {"cortical_drive": 0.50},
            "PosteriorParietalCortex": {"cortical_drive": 0.50},
        })
    assert out["lp_drive"] > 0.35
    assert out["v2_signal"] > 0.20
    assert out["ppc_signal"] > 0.20
    assert out["lp_state"] in ("attentive", "relay", "mismatch")


def test_unexpected_visual_triggers_mismatch():
    """Strong bottom-up SC+V1 with low cortical prediction → mismatch signal."""
    m = LateralPosteriorThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SuperiorColliculus": {"visual_signal": 0.70},
            "V1": {"layer5_output": 0.65},
            # No V2/PPC predictive drive — Roth 2016 mismatch condition
        })
    assert out["mismatch_signal"] > 0.30
    assert out["lp_state"] == "mismatch"


def test_matched_prediction_suppresses_mismatch():
    """Matched cortical prediction should NOT generate mismatch."""
    m = LateralPosteriorThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SuperiorColliculus": {"visual_signal": 0.50},
            "V1": {"layer5_output": 0.50},
            "V2": {"cortical_drive": 0.50},
            "PosteriorParietalCortex": {"cortical_drive": 0.50},
        })
    # When prediction matches sensory drive, mismatch should be small
    assert out["mismatch_signal"] < 0.20
    assert out["lp_state"] in ("attentive", "relay")


def test_quiet_no_input():
    m = LateralPosteriorThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["lp_state"] == "quiet"
