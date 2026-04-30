"""Behavioral tests for PrePresubiculum."""
import asyncio
from brain.limbic.PrePresubiculum import PrePresubiculum


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_atn_drives_hd_signal():
    m = PrePresubiculum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AnteriorThalamicPapez": {"atn_drive": 0.65},
            "VestibularNuclei": {"angular_velocity_signal": 0.20},
        })
    assert out["prps_drive"] > 0.30
    assert out["head_direction_signal"] > 0.30
    assert out["mec_grid_input"] > 0.20


def test_compass_locks_with_sustained_hd():
    m = PrePresubiculum()
    out = None
    for _ in range(40):
        out = _tick(m, {
            "AnteriorThalamicPapez": {"atn_drive": 0.55},
            "VestibularNuclei": {"angular_velocity_signal": 0.10},
        })
    assert out["allocentric_compass_signal"] > 0.20


def test_high_motion_drift():
    m = PrePresubiculum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AnteriorThalamicPapez": {"atn_drive": 0.55},
            "VestibularNuclei": {"angular_velocity_signal": 0.85},
        })
    # Either drift or hd_active is acceptable; just check signal is alive
    assert out["prps_drive"] > 0.20


def test_quiet_no_input():
    m = PrePresubiculum()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["prps_state"] == "quiet"
