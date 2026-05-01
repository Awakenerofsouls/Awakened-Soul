"""Behavioral tests for PrimaryVisualCortex."""
import asyncio
from brain.mechanisms.PrimaryVisualCortex import PrimaryVisualCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_lgn_drives_v1_orientation_response():
    m = PrimaryVisualCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralGeniculateNucleus": {
                "lgn_drive": 0.65,
                "magno_signal": 0.55,
                "parvo_signal": 0.60,
            },
        })
    assert out["v1_drive"] > 0.30
    assert out["simple_cell_signal"] > 0.20
    assert out["complex_cell_signal"] > 0.20
    assert out["v1_state"] in ("oriented_active", "high_contrast")


def test_magno_dominates_dorsal_stream():
    m = PrimaryVisualCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralGeniculateNucleus": {
                "lgn_drive": 0.55,
                "magno_signal": 0.80,
                "parvo_signal": 0.10,
            },
        })
    assert out["magno_to_v2"] > out["parvo_to_v2"]


def test_parvo_dominates_ventral_stream():
    m = PrimaryVisualCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "LateralGeniculateNucleus": {
                "lgn_drive": 0.55,
                "magno_signal": 0.10,
                "parvo_signal": 0.80,
            },
        })
    assert out["parvo_to_v2"] > out["magno_to_v2"]


def test_quiet_no_input():
    m = PrimaryVisualCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["v1_state"] == "quiet"
