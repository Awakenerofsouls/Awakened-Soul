"""Behavioral tests for HistamineArousalBooster."""
import asyncio
from brain.foundational.HistamineArousalBooster import HistamineArousalBooster


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_orexin_drives_tmn_wake():
    """Brown 2001: TMN wake-active; orexin excites it."""
    m = HistamineArousalBooster()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OrexinWakePromoter": {"tmn_excitation": 0.65},
            "ArousalRegulator": {"tonic_level": 0.65},
            "CircadianTimer": {"firing_rate_proxy": 0.70},
        })
    assert out["tmn_drive"] > 0.30
    assert out["cortical_histamine_release"] > 0.20
    assert out["tmn_state"] == "active_wake"


def test_vlpo_suppresses_tmn():
    """Saper 2005 flip-flop: VLPO inhibits TMN (sleep state)."""
    m_no_vlpo = HistamineArousalBooster()
    out_no = None
    for _ in range(15):
        out_no = _tick(m_no_vlpo, {
            "OrexinWakePromoter": {"tmn_excitation": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
        })

    m_vlpo = HistamineArousalBooster()
    out_vlpo = None
    for _ in range(15):
        out_vlpo = _tick(m_vlpo, {
            "OrexinWakePromoter": {"tmn_excitation": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
            "VentrolateralPreoptic": {"vlpo_drive": 0.85},
        })
    assert out_vlpo["tmn_drive"] < out_no["tmn_drive"]


def test_low_arousal_high_vlpo_rem_silent():
    """Brown 2001: TMN completely silent during REM."""
    m = HistamineArousalBooster()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "OrexinWakePromoter": {"tmn_excitation": 0.05},
            "VentrolateralPreoptic": {"vlpo_drive": 0.75},
            "ArousalRegulator": {"tonic_level": 0.05},
        })
    assert out["tmn_state"] in ("rem_silent", "nrem", "quiet")


def test_quiet_no_input():
    m = HistamineArousalBooster()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["tmn_state"] in ("quiet", "drowsy")
