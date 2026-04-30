"""Behavioral tests for ThetaGammaCrossFrequencyBinding."""
import asyncio
from brain.integration.ThetaGammaCrossFrequencyBinding import ThetaGammaCrossFrequencyBinding


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_theta_plus_gamma_drives_pac():
    """Lisman 2013: PAC requires both theta phase + gamma amplitude."""
    m = ThetaGammaCrossFrequencyBinding()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA3Dorsal": {"dca3_drive": 0.65},
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.55},
            "MedialSeptum": {"theta_signal": 0.65},
            "PrelimbicCortex": {"pl_drive": 0.55},
        })
    assert out["pac_strength"] > 0.30
    assert out["gamma_amplitude"] > 0.30
    assert out["theta_phase_coherence"] > 0.30
    assert out["cfc_state"] == "binding_active"


def test_theta_alone_no_pac():
    """Tort 2009: PAC requires both — theta without gamma → no coupling."""
    m = ThetaGammaCrossFrequencyBinding()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialSeptum": {"theta_signal": 0.85},
            "PrelimbicCortex": {"pl_drive": 0.55},
            # No CA3/CA1 inputs — no gamma
        })
    assert out["pac_strength"] < 0.20
    assert out["gamma_amplitude"] < 0.20


def test_pfc_engagement_loads_items():
    """Spellman 2017: hippocampal-PFC theta-gamma coupling tracks WM load."""
    m = ThetaGammaCrossFrequencyBinding()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "HippocampalCA3Dorsal": {"dca3_drive": 0.65},
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.65},
            "MedialSeptum": {"theta_signal": 0.65},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.75,
                                                  "working_memory_signal": 0.70},
        })
    assert out["item_load"] > 0.20


def test_quiet_no_input():
    m = ThetaGammaCrossFrequencyBinding()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["cfc_state"] == "quiet"
