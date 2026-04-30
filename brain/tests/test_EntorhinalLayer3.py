"""Behavioral tests for EntorhinalLayer3."""
import asyncio
from brain.limbic.EntorhinalLayer3 import EntorhinalLayer3


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ec_input_engages_ta_pathway():
    m = EntorhinalLayer3()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "EntorhinalCortexGridCells": {"ec_output": 0.65},
            "LateralEntorhinalCortex": {"lec_drive": 0.55},
            "PrelimbicCortex": {"pl_drive": 0.40},
        })
    assert out["ec3_drive"] > 0.30
    assert out["temporoammonic_signal"] > 0.30
    assert out["ec3_state"] in ("ta_active", "persistent")


def test_mismatch_when_ca3_weak():
    m = EntorhinalLayer3()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "EntorhinalCortexGridCells": {"ec_output": 0.75},
            "LateralEntorhinalCortex": {"lec_drive": 0.65},
            "HippocampalCA3": {"ca3_output": 0.05},  # weak retrieval
        })
    assert out["match_mismatch_gate"] > 0.20


def test_persistent_firing_accumulates():
    m = EntorhinalLayer3()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "EntorhinalCortexGridCells": {"ec_output": 0.55},
            "PrelimbicCortex": {"pl_drive": 0.55},
        })
    assert out["persistent_firing_signal"] > 0.20


def test_quiet_no_input():
    m = EntorhinalLayer3()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ec3_state"] == "quiet"
