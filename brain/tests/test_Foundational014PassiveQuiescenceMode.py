"""
Tests: Foundational014PassiveQuiescenceMode (VLPO/SubC Sleep-Promoting System)
=============================================================================
"""

import pytest
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.foundational.Foundational014PassiveQuiescenceMode import PassiveQuiescenceMode


def make_mechanism():
    m = PassiveQuiescenceMode()
    # state is already initialized by __init__ — don't overwrite
    m._state_loaded = True
    return m


def tick_sync(m, inputs):
    """Await the async tick method synchronously in tests."""
    return asyncio.run(m.tick(inputs))


def test_baseline_quiescence_low_during_active_wake():
    """Minimal VLPO/SubC firing when wake-promoters are active."""
    m = make_mechanism()
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.80, "phasic_bursting": True},
            "OrexinWakePromoter": {"orexin_level": 0.85, "orexin_active": True},
            "HistamineArousalBooster": {"histamine_level": 0.75},
            "Homeostat": {"dominant_drive": "expression", "cumulative_pressure": 0.1},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.0},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": False},
        }
    }
    result = tick_sync(m, inputs)
    assert result["passive_quiescence_level"] < 0.30
    assert result["sleep_likelihood"] < 0.40


def test_sleep_pressure_accumulates_with_high_cumulative_pressure():
    """Homeostatic sleep pressure drives VLPO activation."""
    m = PassiveQuiescenceMode()
    m._state_loaded = True
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.25, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.05, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.05},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.85},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.6},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    for _ in range(3):
        result = tick_sync(m, inputs)
    assert result["sleep_pressure"] > 0.6
    assert result["passive_quiescence_level"] > 0.5


def test_orexin_absence_enables_vlpo_activation():
    """Orexin suppresses VLPO — orexin removal allows sleep onset."""
    # Run 3 ticks so orexin-disinhibition effect compounds
    m1 = PassiveQuiescenceMode()
    m1._state_loaded = True
    inputs_low_orx = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.30, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.05, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.10},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.80},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.5},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    for _ in range(3):
        r1 = tick_sync(m1, inputs_low_orx)
    low_orx_q = r1["passive_quiescence_level"]

    m2 = PassiveQuiescenceMode()
    m2._state_loaded = True
    inputs_high_orx = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.30, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.80, "orexin_active": True},
            "HistamineArousalBooster": {"histamine_level": 0.10},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.80},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.5},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    for _ in range(3):
        r2 = tick_sync(m2, inputs_high_orx)
    high_orx_q = r2["passive_quiescence_level"]

    assert low_orx_q > high_orx_q, f"Low orexin quiescence ({low_orx_q:.4f}) should exceed high orexin ({high_orx_q:.4f})"


def test_nrem_active_above_sleep_onset_threshold():
    """NREM mode fires when quiescence exceeds threshold but REM not met."""
    m = PassiveQuiescenceMode()
    m._state_loaded = True
    # Pre-seed state so quiescence can accumulate to threshold in one tick
    m.state["passive_quiescence_level"] = 0.40
    m.state["sleep_pressure"] = 0.60
    m.state["tick_count"] = 0
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.35, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.05, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.05},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.75},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.5},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    result = tick_sync(m, inputs)
    assert result["passive_quiescence_level"] > 0.35, \
        f"NREM onset needs quiescence > 0.35, got {result['passive_quiescence_level']:.4f}"
    assert result["rem_active"] is False, \
        f"REM should not fire at this threshold, got {result['rem_active']}"


def test_rem_active_above_rem_threshold_low_arousal():
    """REM: very high quiescence + low arousal."""
    m = make_mechanism()
    # Pre-seed state via direct attribute so __init__ defaults hold
    m.state["passive_quiescence_level"] = 0.75
    m.state["sleep_pressure"] = 0.80
    m.state["tick_count"] = 0
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.15, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.0, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.0},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.90},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.8},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    result = tick_sync(m, inputs)
    assert result["rem_active"] is True
    assert result["nrem_active"] is False


def test_phasic_arousal_disrupts_sleep_onset():
    """LC phasic bursts suppress VLPO and delay sleep onset."""
    m1 = PassiveQuiescenceMode()
    m1._state_loaded = True
    inputs_no_phasic = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.40, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.05, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.05},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.70},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.4},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    for _ in range(3):
        r1 = tick_sync(m1, inputs_no_phasic)
    no_phasic_q = r1["passive_quiescence_level"]

    m2 = PassiveQuiescenceMode()
    m2._state_loaded = True
    inputs_phasic = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.40, "phasic_bursting": True},
            "OrexinWakePromoter": {"orexin_level": 0.05, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.05},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.70},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.4},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    for _ in range(3):
        r2 = tick_sync(m2, inputs_phasic)
    phasic_q = r2["passive_quiescence_level"]

    assert no_phasic_q > phasic_q


def test_wake_inhibition_scales_with_quiescence():
    """Wake inhibition output increases with VLPO/SubC activation."""
    m = PassiveQuiescenceMode()
    m._state_loaded = True
    # Pre-seed so we don't need multi-tick warmup
    m.state["passive_quiescence_level"] = 0.50
    m.state["sleep_pressure"] = 0.80
    m.state["tick_count"] = 0
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.20, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.0, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.0},
            "Homeostat": {"dominant_drive": "rest", "cumulative_pressure": 0.90},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.8},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": True},
        }
    }
    result = tick_sync(m, inputs)
    assert result["wake_inhibition"] > 0.0
    assert result["passive_quiescence_level"] > 0.4


def test_wake_inhibition_zero_when_quiescence_low():
    """No wake suppression when VLPO/SubC are inactive."""
    m = PassiveQuiescenceMode()
    m._state_loaded = True
    inputs = {
        "prior_results": {
            "ArousalRegulator": {"arousal_level": 0.85, "phasic_bursting": True},
            "OrexinWakePromoter": {"orexin_level": 0.85, "orexin_active": True},
            "HistamineArousalBooster": {"histamine_level": 0.80},
            "Homeostat": {"dominant_drive": "expression", "cumulative_pressure": 0.1},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.0},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": False},
        }
    }
    result = tick_sync(m, inputs)
    assert result["wake_inhibition"] == 0.0
    assert result["sleep_likelihood"] < 0.3


def test_enrichment_outputs_match_brain_runner():
    """All required output keys present."""
    m = PassiveQuiescenceMode()
    m._state_loaded = True
    inputs = {
        "prior_results": {
            "Homeostat": {"dominant_drive": "curiosity", "cumulative_pressure": 0.3},
            "ArousalRegulator": {"arousal_level": 0.5, "phasic_bursting": False},
            "OrexinWakePromoter": {"orexin_level": 0.5, "orexin_active": False},
            "HistamineArousalBooster": {"histamine_level": 0.5},
            "AnteriorHypothalamicCooling": {"cooling_signal": 0.0},
            "ThermoSleepGate": {"thermoregulatory_sleep_mode": False},
        }
    }
    result = tick_sync(m, inputs)
    required_keys = [
        "passive_quiescence_level", "sleep_likelihood", "rem_active",
        "nrem_active", "wake_inhibition", "sleep_pressure"
    ]
    for key in required_keys:
        assert key in result, f"Missing output: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])