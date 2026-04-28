"""
Tests: Foundational015BaroreflexBalancer (NTS-CVLM-RVLM Baroreceptor Reflex)
===========================================================================
"""

import pytest
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.foundational.Foundational015BaroreflexBalancer import BaroreflexBalancer


def tick_sync(m, inputs):
    """Await the async tick method synchronously."""
    return asyncio.run(m.tick(inputs))


def test_baseline_reflex_suppresses_sympathetic_in_hypertension():
    """Elevated MAP triggers CVLM → RVLM suppression → reduced sympathetic tone."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    inputs = {
        "prior_results": {
            "SympatheticVasomotorController": {"mean_arterial_pressure": 0.90},
            "HeartRateController": {"heart_rate": 0.60},
            "CRHStressDispatcher": {"crh_level": 0.0},
        }
    }
    result = tick_sync(m, inputs)
    assert result["baroreflex_activity"] > 0.1
    assert result["sympathetic_tone"] < 0.38  # below baseline


def test_hypotension_rises_sympathetic_tone():
    """Low MAP disengages CVLM → sympathetic tone rises."""
    m1 = BaroreflexBalancer()
    m1._state_loaded = True
    m1.state["sympathetic_tone"] = 0.20
    r1 = tick_sync(m1, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.30},
        "HeartRateController": {"heart_rate": 0.40},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})

    m2 = BaroreflexBalancer()
    m2._state_loaded = True
    m2.state["sympathetic_tone"] = 0.20
    r2 = tick_sync(m2, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.70},
        "HeartRateController": {"heart_rate": 0.50},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})

    assert r1["sympathetic_tone"] > r2["sympathetic_tone"], \
        "Hypotension should raise sympathetic tone above normotension"


def test_stress_overrides_baroreflex():
    """CRH/stress suppresses baroreflex and drives sympathetic tone."""
    m1 = BaroreflexBalancer()
    m1._state_loaded = True
    m1.state["sympathetic_tone"] = 0.20
    r1 = tick_sync(m1, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.70},
        "HeartRateController": {"heart_rate": 0.50},
        "CRHStressDispatcher": {"crh_level": 0.80},
    }})

    m2 = BaroreflexBalancer()
    m2._state_loaded = True
    m2.state["sympathetic_tone"] = 0.20
    r2 = tick_sync(m2, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.70},
        "HeartRateController": {"heart_rate": 0.50},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})

    assert r1["sympathetic_tone"] > r2["sympathetic_tone"], \
        "Stress should elevate sympathetic tone above baroreflex-only baseline"


def test_parasympathetic_tone_falls_with_stress():
    """Vagal withdrawal during acute stress."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    inputs = {
        "prior_results": {
            "SympatheticVasomotorController": {"mean_arterial_pressure": 0.50},
            "HeartRateController": {"heart_rate": 0.50},
            "CRHStressDispatcher": {"crh_level": 0.70},
        }
    }
    result = tick_sync(m, inputs)
    assert result["parasympathetic_tone"] < 0.32  # below baseline


def test_hypotension_risk_detected_on_low_pressure():
    """Hypotension risk is non-zero when MAP is low."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    result = tick_sync(m, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.30},
        "HeartRateController": {"heart_rate": 0.35},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})
    assert result["hypotension_risk"] > 0.0


def test_hypertension_risk_detected_on_high_pressure():
    """Hypertension risk is non-zero when MAP is high."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    result = tick_sync(m, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.90},
        "HeartRateController": {"heart_rate": 0.70},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})
    assert result["hypertension_risk"] > 0.0


def test_setpoint_adapts_to_sustained_hypertension():
    """Operating point drifts upward under sustained hypertension."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    m.state["baroreflex_setpoint"] = 0.70  # normalized ≈ 95 mmHg
    inputs = {
        "prior_results": {
            "SympatheticVasomotorController": {"mean_arterial_pressure": 0.90},
            "HeartRateController": {"heart_rate": 0.65},
            "CRHStressDispatcher": {"crh_level": 0.0},
        }
    }
    for _ in range(200):
        result = tick_sync(m, inputs)
    # After sustained hypertension, setpoint should have drifted up
    assert result["baroreflex_setpoint"] > 0.70, \
        f"Setpoint should rise under sustained hypertension, got {result['baroreflex_setpoint']}"


def test_bp_regulation_strength_zero_at_normotension():
    """Minimal regulation drive when MAP is near the setpoint."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    m.state["baroreflex_setpoint"] = 0.70  # normotension
    result = tick_sync(m, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.70},
        "HeartRateController": {"heart_rate": 0.50},
        "CRHStressDispatcher": {"crh_level": 0.0},
    }})
    assert result["bp_regulation_strength"] < 0.15


def test_enrichment_outputs_match_brain_runner():
    """All required output keys present."""
    m = BaroreflexBalancer()
    m._state_loaded = True
    result = tick_sync(m, {"prior_results": {
        "SympatheticVasomotorController": {"mean_arterial_pressure": 0.60},
        "HeartRateController": {"heart_rate": 0.50},
        "CRHStressDispatcher": {"crh_level": 0.10},
    }})
    required_keys = [
        "baroreflex_activity", "sympathetic_tone", "parasympathetic_tone",
        "bp_regulation_strength", "hypotension_risk", "hypertension_risk",
    ]
    for key in required_keys:
        assert key in result, f"Missing output: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
