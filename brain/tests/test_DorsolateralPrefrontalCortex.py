"""Behavioral tests for DorsolateralPrefrontalCortex."""
import asyncio
from brain.neocortical.DorsolateralPrefrontalCortex import DorsolateralPrefrontalCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_demand_engages_executive():
    m = DorsolateralPrefrontalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "FrontoParietalControl": {"control_demand": 0.70},
            "AnteriorCingulate": {"conflict_signal": 0.50},
            "Pulvinar": {"attended_signal": 0.60},
        })
    assert out["executive_engagement"] > 0.30
    assert out["dlpfc_state"] in ("engaged", "maintenance", "biasing")


def test_persistent_delay_activity_outlives_input():
    m = DorsolateralPrefrontalCortex()
    # First load content
    for _ in range(10):
        _tick(m, {
            "FrontoParietalControl": {"control_demand": 0.65},
            "Pulvinar": {"attended_signal": 0.65},
        })
    delay_loaded = m.state["delay_activity"]
    assert delay_loaded > 0.20
    # Now remove content but persistent activity should not collapse instantly
    out = _tick(m, {"FrontoParietalControl": {"control_demand": 0.65}})
    assert out["delay_activity"] > delay_loaded * 0.4


def test_high_demand_produces_top_down_bias():
    m = DorsolateralPrefrontalCortex()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "FrontoParietalControl": {"control_demand": 0.85},
            "AnteriorCingulate": {"conflict_signal": 0.70},
            "Pulvinar": {"attended_signal": 0.70},
        })
    assert out["top_down_bias"] > 0.30


def test_quiet_no_input():
    m = DorsolateralPrefrontalCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dlpfc_state"] == "quiet"
