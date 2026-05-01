"""Behavioral tests for ParahippocampalPlaceArea (PPA, Epstein 1998)."""
import asyncio
from brain.mechanisms.ParahippocampalPlaceArea import ParahippocampalPlaceArea


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_scene_input_engages_ppa():
    m = ParahippocampalPlaceArea()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.55},
            "InferotemporalCortex": {"it_drive": 0.55},
            "PostrhinalCortex": {"postrhinal_drive": 0.65},
        })
    assert out["ppa_drive"] > 0.25
    assert out["scene_signal"] > 0.20
    assert out["ppa_state"] != "quiet"


def test_high_scene_yields_recognition():
    m = ParahippocampalPlaceArea()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.65},
            "InferotemporalCortex": {"it_drive": 0.75},
            "PostrhinalCortex": {"postrhinal_drive": 0.85},
            "EntorhinalCortexGridCells": {"grid_signal": 0.55},
        })
    assert out["scene_signal"] > 0.40
    assert out["ppa_state"] in ("scene_recognized", "layout_active", "engaged")


def test_layout_independent_of_objects():
    """Empty-room style: low IT, high postrhinal/V4 should still drive layout."""
    m = ParahippocampalPlaceArea()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "VisualAreaV4": {"v4_drive": 0.65},
            "InferotemporalCortex": {"it_drive": 0.20},
            "PostrhinalCortex": {"postrhinal_drive": 0.70},
        })
    assert out["spatial_layout_signal"] > 0.25


def test_quiet_no_input():
    m = ParahippocampalPlaceArea()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ppa_state"] == "quiet"
