"""Behavioral tests for ArcuateAgRP."""
import asyncio
from brain.mechanisms.ArcuateAgRP import ArcuateAgRP


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_hunger_drives_feeding_motivation():
    m = ArcuateAgRP()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.75},
            "VitalCoreRegulator": {"vital_drive": 0.30},
        })
    assert out["agrp_drive"] > 0.30
    assert out["feeding_motivation"] > 0.30
    assert out["pvn_inhibition"] > 0.20
    assert out["agrp_state"] == "hunger_active"


def test_food_cue_anticipatory_suppression():
    """Chen 2015: AgRP rapidly suppressed by food cues even before eating."""
    m_no_cue = ArcuateAgRP()
    out_no = None
    for _ in range(15):
        out_no = _tick(m_no_cue, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.65},
            "VitalCoreRegulator": {"vital_drive": 0.35},
        })

    m_with_cue = ArcuateAgRP()
    out_with = None
    for _ in range(15):
        out_with = _tick(m_with_cue, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.65},
            "VitalCoreRegulator": {"vital_drive": 0.35},
            "OlfactoryBulb": {"food_odor_signal": 0.75},
        })
    assert out_with["agrp_drive"] < out_no["agrp_drive"]


def test_pomc_antagonism():
    """POMC anorexigenic input should reduce AgRP drive (Cone 2005)."""
    m_no_pomc = ArcuateAgRP()
    out_no = None
    for _ in range(15):
        out_no = _tick(m_no_pomc, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.55},
        })

    m_pomc = ArcuateAgRP()
    out_pomc = None
    for _ in range(15):
        out_pomc = _tick(m_pomc, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.55},
            "ArcuatePOMC": {"pomc_alpha_msh_drive": 0.70},
        })
    assert out_pomc["agrp_drive"] < out_no["agrp_drive"]


def test_predator_threat_suppresses_feeding():
    m = ArcuateAgRP()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AppetiteNPYBalancer": {"hunger_signal": 0.65},
            "ValenceTagger": {"aversive_signal": 0.85},
        })
    # Threat suppression — drive should be lowered relative to pure hunger
    assert out["agrp_drive"] < 0.50


def test_quiet_no_input():
    m = ArcuateAgRP()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["agrp_state"] in ("quiet", "satiated")
