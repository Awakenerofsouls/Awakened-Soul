"""Behavioral tests for ParaSubiculum."""
import asyncio
from brain.limbic.ParaSubiculum import ParaSubiculum


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_hd_and_theta_drive_grid_support():
    m = ParaSubiculum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrePresubiculum": {"head_direction_signal": 0.65},
            "MedialSeptum": {"theta_signal": 0.65},
            "AnteriorThalamicPapez": {"atn_drive": 0.45},
        })
    assert out["pasb_drive"] > 0.30
    assert out["grid_supportive_signal"] > 0.20


def test_theta_pacing_active():
    m = ParaSubiculum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialSeptum": {"theta_signal": 0.75},
            "AnteriorThalamicPapez": {"atn_drive": 0.45},
        })
    assert out["mec_theta_pacing"] > 0.20


def test_hd_input_active():
    m = ParaSubiculum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrePresubiculum": {"head_direction_signal": 0.75},
            "AnteriorThalamicPapez": {"atn_drive": 0.55},
        })
    assert out["mec_hd_input"] > 0.20


def test_quiet_no_input():
    m = ParaSubiculum()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pasb_state"] == "quiet"
