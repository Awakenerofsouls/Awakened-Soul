"""Behavioral tests for SubiculumDorsal."""
import asyncio
from brain.mechanisms.SubiculumDorsal import SubiculumDorsal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ca1_drives_papez_output():
    m = SubiculumDorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.65},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
            "MedialSeptum": {"theta_signal": 0.45},
        })
    assert out["dsub_drive"] > 0.30
    assert out["anterior_thalamic_drive"] > 0.20


def test_strong_drive_engages_burst_firing():
    m = SubiculumDorsal()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.85},
            "EntorhinalCortexGridCells": {"ec_output": 0.55},
            "MedialSeptum": {"theta_signal": 0.55},
        })
    assert out["mammillary_body_drive"] > 0.20


def test_grid_input_drives_bvc():
    m = SubiculumDorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.65},
        })
    assert out["boundary_vector_signal"] > 0.20


def test_quiet_no_input():
    m = SubiculumDorsal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dsub_state"] == "quiet"
