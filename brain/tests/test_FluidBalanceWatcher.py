"""Behavioral tests for FluidBalanceWatcher."""
import asyncio
from brain.mechanisms.FluidBalanceWatcher import FluidBalanceWatcher


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_low_vital_drives_thirst():
    """Bourque 2008: depleted state → osmoreceptor → thirst."""
    m = FluidBalanceWatcher()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VitalCoreRegulator": {"vital_drive": 0.10,
                                       "osmotic_signal": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["thirst_drive"] > 0.30
    assert out["osmotic_signal"] > 0.20
    assert out["fluid_state"] in ("thirsty", "drinking")


def test_avp_command_above_threshold():
    """Brown 2013: AVP rises sharply above osmotic threshold."""
    m = FluidBalanceWatcher()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VitalCoreRegulator": {"vital_drive": 0.10,
                                       "osmotic_signal": 0.75},
        })
    assert out["avp_command"] > 0.30


def test_arousal_required_for_water_seeking():
    """Zimmerman 2016: behavior requires alert state."""
    m_high_ar = FluidBalanceWatcher()
    out_high = None
    for _ in range(15):
        out_high = _tick(m_high_ar, {
            "VitalCoreRegulator": {"vital_drive": 0.10,
                                       "osmotic_signal": 0.55},
            "ArousalRegulator": {"tonic_level": 0.75},
        })

    m_low_ar = FluidBalanceWatcher()
    out_low = None
    for _ in range(15):
        out_low = _tick(m_low_ar, {
            "VitalCoreRegulator": {"vital_drive": 0.10,
                                       "osmotic_signal": 0.55},
            "ArousalRegulator": {"tonic_level": 0.05},
        })
    assert out_high["water_seeking_drive"] > out_low["water_seeking_drive"]


def test_quiet_no_input():
    m = FluidBalanceWatcher()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["fluid_state"] in ("quiet", "satiated")
