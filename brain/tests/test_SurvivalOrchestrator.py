"""Behavioral tests for SurvivalOrchestrator."""
import asyncio
from brain.mechanisms.SurvivalOrchestrator import SurvivalOrchestrator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_threat_engages_defense_priority():
    """Strong threat should make defense the dominant drive."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "ValenceTagger": {"aversive_signal": 0.85, "threat_signal": 0.85},
            "VitalCoreRegulator": {"vital_drive": 0.5, "survival_threat_level": 0.65},
        })
    assert out["defense_priority"] > 0.40
    assert out["dominant_drive"] == "defense"
    assert "defense" in out["survival_state"]


def test_hunger_drives_energy_priority():
    """High hunger + low threat → energy dominant drive."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "ValenceTagger": {"aversive_signal": 0.0, "threat_signal": 0.0},
            "AppetiteNPYBalancer": {"hunger_signal": 0.85},
            "VitalCoreRegulator": {"vital_drive": 0.30},
        })
    assert out["energy_priority"] > 0.30
    assert out["dominant_drive"] == "energy"


def test_thirst_drives_fluid_priority():
    """High thirst → fluid priority."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "FluidBalanceWatcher": {"thirst_drive": 0.85, "osmotic_signal": 0.65},
        })
    assert out["fluid_priority"] > 0.30
    assert out["dominant_drive"] == "fluid"


def test_extreme_temp_drives_thermal_priority():
    """Extreme core temp deviation → thermal priority."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "ThermoregulationCore": {"core_temp_proxy": 0.85},
        })
    assert out["thermal_priority"] > 0.20


def test_threat_overrides_other_drives():
    """Defense should win even when other priorities are high (Cannon 1929)."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {
            "ValenceTagger": {"aversive_signal": 0.80, "threat_signal": 0.80},
            "AppetiteNPYBalancer": {"hunger_signal": 0.80},
            "FluidBalanceWatcher": {"thirst_drive": 0.80},
        })
    # Defense overrides
    assert out["dominant_drive"] == "defense"


def test_quiet_no_drives():
    """No drive inputs → quiet state."""
    m = SurvivalOrchestrator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["survival_state"] == "quiet"
    assert out["urgency_score"] < 0.10
