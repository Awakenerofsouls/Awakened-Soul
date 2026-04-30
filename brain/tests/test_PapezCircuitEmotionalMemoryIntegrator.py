"""Behavioral tests for PapezCircuitEmotionalMemoryIntegrator."""
import asyncio
from brain.integration.PapezCircuitEmotionalMemoryIntegrator import PapezCircuitEmotionalMemoryIntegrator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_full_loop_drives_consolidation():
    """All Papez nodes active → loop closure → consolidation builds."""
    m = PapezCircuitEmotionalMemoryIntegrator()
    out = None
    for _ in range(60):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"subicular_output": 0.65},
            "MammillaryBody": {"mammillary_drive": 0.55},
            "AnteroVentralThalamus": {"atn_drive": 0.55},
            "CingulateAnterior": {"acc_drive": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.55},
        })
    assert out["loop_closure_strength"] > 0.30
    assert out["consolidation_signal"] > 0.10


def test_mammillary_failure_breaks_loop():
    """Vann 2009: mammillary lesion → amnesic break despite other nodes
    being active."""
    m = PapezCircuitEmotionalMemoryIntegrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"subicular_output": 0.65},
            "MammillaryBody": {"mammillary_drive": 0.05},  # damaged
            "AnteroVentralThalamus": {"atn_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.55},
            "EntorhinalCortexGridCells": {"ec_output": 0.55},
        })
    assert out["amnesic_node_failure"] > 0.30
    assert out["loop_closure_strength"] < 0.30
    assert out["papez_state"] == "amnesic_break"


def test_thalamocingulate_active_with_ATN_and_cingulate():
    """Catani 2023: thalamocingulate output arm — ATN + cingulate."""
    m = PapezCircuitEmotionalMemoryIntegrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AnteroVentralThalamus": {"atn_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.55},
        })
    assert out["thalamocingulate_signal"] > 0.30


def test_quiet_no_input():
    m = PapezCircuitEmotionalMemoryIntegrator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["papez_state"] == "quiet"
