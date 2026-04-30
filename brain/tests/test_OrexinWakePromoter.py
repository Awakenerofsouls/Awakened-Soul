"""Behavioral tests for OrexinWakePromoter."""
import asyncio
from brain.foundational.OrexinWakePromoter import OrexinWakePromoter


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_arousal_plus_day_drives_orexin():
    """Sakurai 1998: orexin promotes wake; circadian + arousal drive."""
    m = OrexinWakePromoter()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.65},
            "CircadianTimer": {"firing_rate_proxy": 0.75},
        })
    assert out["orexin_drive"] > 0.30
    assert out["wake_stabilization_signal"] > 0.20
    assert out["orexin_state"] == "active_wake"


def test_hunger_engages_homeostatic_feeding():
    """Sakurai 1998: orexin links energy state to arousal."""
    m = OrexinWakePromoter()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.45},
            "CircadianTimer": {"firing_rate_proxy": 0.60},
            "ArcuateAgRP": {"feeding_motivation": 0.65},
            "VitalCoreRegulator": {"vital_drive": 0.20},
        })
    assert out["orexin_drive"] > 0.30
    assert out["orexin_state"] in ("homeostatic_feeding", "active_wake")


def test_ascending_excitation_active():
    """Saper 2010: orexin excites LC, TMN, PPN, raphe."""
    m = OrexinWakePromoter()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.70},
            "CircadianTimer": {"firing_rate_proxy": 0.70},
        })
    assert out["lc_excitation"] > 0.20
    assert out["tmn_excitation"] > 0.20
    assert out["ppn_excitation"] > 0.20
    assert out["raphe_excitation"] > 0.20


def test_quiet_no_input():
    m = OrexinWakePromoter()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["orexin_state"] in ("quiet", "low_arousal")
