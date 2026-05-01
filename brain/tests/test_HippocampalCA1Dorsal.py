"""Behavioral tests for HippocampalCA1Dorsal."""
import asyncio
from brain.mechanisms.HippocampalCA1Dorsal import HippocampalCA1Dorsal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ca3_and_ta_drive_place_cells():
    m = HippocampalCA1Dorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3Dorsal": {"dca3_drive": 0.65},
            "EntorhinalLayer3": {"temporoammonic_signal": 0.55},
            "MedialSeptum": {"theta_signal": 0.55},
        })
    assert out["ca1d_drive"] > 0.30
    assert out["place_cell_activation"] > 0.20
    assert out["ca1d_state"] in ("place_active", "theta_active")


def test_low_theta_high_ca3_triggers_ripples():
    m = HippocampalCA1Dorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3Dorsal": {"dca3_drive": 0.75},
            "EntorhinalLayer3": {"temporoammonic_signal": 0.30},
            "MedialSeptum": {"theta_signal": 0.05},
        })
    assert out["ripple_event_signal"] > 0.30


def test_subicular_output_when_active():
    m = HippocampalCA1Dorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3Dorsal": {"dca3_drive": 0.55},
            "EntorhinalLayer3": {"temporoammonic_signal": 0.45},
        })
    assert out["subicular_output"] > 0.20


def test_quiet_no_input():
    m = HippocampalCA1Dorsal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ca1d_state"] == "quiet"
