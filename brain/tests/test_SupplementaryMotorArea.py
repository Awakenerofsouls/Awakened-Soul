"""Behavioral tests for SupplementaryMotorArea (SMA)."""
import asyncio
from brain.mechanisms.SupplementaryMotorArea import SupplementaryMotorArea


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_va_prelimbic_drive_internal_movement():
    """VA thalamic + prelimbic drive should engage internally generated signal."""
    m = SupplementaryMotorArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralAnteriorThalamus": {"va_drive": 0.65},
            "PrelimbicCortex": {"prelimbic_drive": 0.55},
        })
    assert out["sma_drive"] > 0.30
    assert out["internal_movement_signal"] > 0.20
    assert out["sma_state"] != "quiet"


def test_external_visual_suppresses_internal_signal():
    """Mushiake 1991 — external visual cue suppresses SMA internal signal."""
    m1 = SupplementaryMotorArea()
    m2 = SupplementaryMotorArea()
    no_vis = None
    with_vis = None
    for _ in range(15):
        no_vis = _tick(m1, {
            "VentralAnteriorThalamus": {"va_drive": 0.50},
            "PrelimbicCortex": {"prelimbic_drive": 0.45},
        })
        with_vis = _tick(m2, {
            "VentralAnteriorThalamus": {"va_drive": 0.50},
            "PrelimbicCortex": {"prelimbic_drive": 0.45},
            "VisualCortexV1": {"v1_drive": 0.80},
        })
    assert no_vis["internal_movement_signal"] >= with_vis["internal_movement_signal"]


def test_sequence_advances_position():
    """Sustained sequence_signal should advance the ordinal position counter."""
    m = SupplementaryMotorArea()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "VentralAnteriorThalamus": {"va_drive": 0.65},
            "PrelimbicCortex": {"prelimbic_drive": 0.65},
        })
    assert out["sequence_signal"] > 0.20
    assert out["sequence_position"] >= 1


def test_quiet_no_input():
    m = SupplementaryMotorArea()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["sma_state"] == "quiet"
