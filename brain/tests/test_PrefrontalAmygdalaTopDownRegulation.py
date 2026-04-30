"""Behavioral tests for PrefrontalAmygdalaTopDownRegulation."""
import asyncio
from brain.integration.PrefrontalAmygdalaTopDownRegulation import PrefrontalAmygdalaTopDownRegulation


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_vmpfc_drives_amygdala_suppression():
    """Phelps 2004: vmPFC engagement suppresses amygdala output."""
    m = PrefrontalAmygdalaTopDownRegulation()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65,
                                                  "emotion_regulation_signal": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "CentralAmygdalaMedial": {"cea_drive": 0.50},
            "ValenceTagger": {"aversive_signal": 0.65},
        })
    assert out["regulation_drive"] > 0.30
    assert out["amygdala_suppression_signal"] > 0.20
    assert out["regulation_state"] in ("regulating", "extinction_recall")


def test_extinction_recall_builds_with_sustained_engagement():
    """Quirk 2008: extinction recall requires sustained IL engagement
    against fear cue."""
    m = PrefrontalAmygdalaTopDownRegulation()
    out = None
    for _ in range(60):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.75},
            "InfralimbicCortex": {"il_drive": 0.70},
            "CentralAmygdalaMedial": {"cea_drive": 0.55},
            "ValenceTagger": {"aversive_signal": 0.55},
        })
    assert out["extinction_recall_strength"] > 0.10


def test_hyperactive_amygdala_resists_suppression():
    """Etkin 2007: PTSD-like state — high amygdala drive resists
    vmPFC regulation (saturating effect)."""
    m_low = PrefrontalAmygdalaTopDownRegulation()
    out_low = None
    for _ in range(15):
        out_low = _tick(m_low, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.30},
            "ValenceTagger": {"aversive_signal": 0.55},
        })

    m_high = PrefrontalAmygdalaTopDownRegulation()
    out_high = None
    for _ in range(15):
        out_high = _tick(m_high, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.85},  # hyperactive
            "ValenceTagger": {"aversive_signal": 0.55},
        })
    # Suppression / amygdala-output ratio should be lower in PTSD-like state
    assert out_high["regulation_success"] < out_low["regulation_success"]


def test_quiet_no_input():
    m = PrefrontalAmygdalaTopDownRegulation()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["regulation_state"] == "quiet"
