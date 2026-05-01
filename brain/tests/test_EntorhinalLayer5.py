"""Behavioral tests for EntorhinalLayer5."""
import asyncio
from brain.mechanisms.EntorhinalLayer5 import EntorhinalLayer5


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ca1_input_drives_cortical_output():
    m = EntorhinalLayer5()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.65},
            "SubiculumDorsal": {"dsub_drive": 0.55},
        })
    assert out["ec5_drive"] > 0.30
    assert out["cortical_output_signal"] > 0.30


def test_sustained_activity_consolidates():
    m = EntorhinalLayer5()
    out = None
    for _ in range(40):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.70},
            "SubiculumDorsal": {"dsub_drive": 0.60},
            "PrelimbicCortex": {"pl_drive": 0.50},
        })
    assert out["consolidation_signal"] > 0.20


def test_loop_feedback_when_active():
    m = EntorhinalLayer5()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.45},
        })
    assert out["ec_loop_feedback"] > 0.20


def test_quiet_no_input():
    m = EntorhinalLayer5()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ec5_state"] == "quiet"
