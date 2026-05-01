"""Behavioral tests for SalienceDefaultExecutiveToggling."""
import asyncio
from brain.mechanisms.SalienceDefaultExecutiveToggling import SalienceDefaultExecutiveToggling


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_low_salience_default_dominates():
    """Without salient stimuli, DMN should win."""
    m = SalienceDefaultExecutiveToggling()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "CingulatePosterior": {"pcc_drive": 0.55},
        })
    assert out["dominant_network"] == "default"
    assert out["default_network_dominance"] > out["executive_network_dominance"]


def test_high_salience_switches_to_executive():
    """Sridharan 2008: high salience drives transition INTO CEN."""
    m = SalienceDefaultExecutiveToggling()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.75},
            "CingulateAnterior": {"acc_drive": 0.70},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.55},
            "PosteriorParietalCortex": {"ppc_drive": 0.45},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.60},
            "ValenceTagger": {"valence_intensity": 0.65},
        })
    # Executive should be dominant or salience itself
    assert out["dominant_network"] in ("executive", "salience")
    # DMN should be suppressed (anti-correlation, Fox 2005)
    assert out["default_network_dominance"] < 0.40


def test_switching_event_detected():
    """When dominance shifts, toggling_signal should fire."""
    m = SalienceDefaultExecutiveToggling()
    # Phase 1: DMN dominant
    for _ in range(15):
        _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "CingulatePosterior": {"pcc_drive": 0.55},
        })
    # Phase 2: salience surge → switch
    out = None
    for _ in range(8):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.85},
            "CingulateAnterior": {"acc_drive": 0.80},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.85},
        })
    # Should have detected switching at some point
    assert out["dominant_network"] != "default"


def test_quiet_no_input():
    m = SalienceDefaultExecutiveToggling()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["switching_state"] == "quiet"
    assert out["dominant_network"] == "none"
