"""Behavioral tests for SecondaryVisualCortex."""
import asyncio
from brain.mechanisms.SecondaryVisualCortex import SecondaryVisualCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_v1_drives_v2_engagement():
    m = SecondaryVisualCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {
                "v1_drive": 0.60,
                "magno_to_v2": 0.45,
                "parvo_to_v2": 0.55,
                "complex_cell_signal": 0.50,
            },
        })
    assert out["v2_drive"] > 0.25
    assert out["v2_state"] in ("border_active", "illusory_active", "engaged")


def test_high_form_input_yields_border_ownership():
    m = SecondaryVisualCortex()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrimaryVisualCortex": {
                "v1_drive": 0.75,
                "magno_to_v2": 0.30,
                "parvo_to_v2": 0.80,
                "complex_cell_signal": 0.60,
            },
        })
    assert out["border_ownership_signal"] > 0.30
    assert out["pale_stripe_signal"] > 0.30


def test_dorsal_vs_ventral_split():
    m = SecondaryVisualCortex()
    # magno-dominated → dorsal stream (MT input) > ventral
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {
                "v1_drive": 0.55,
                "magno_to_v2": 0.85,
                "parvo_to_v2": 0.10,
                "complex_cell_signal": 0.60,
            },
        })
    assert out["mt_input_signal"] > out["v4_input_signal"]


def test_quiet_no_input():
    m = SecondaryVisualCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["v2_state"] == "quiet"
