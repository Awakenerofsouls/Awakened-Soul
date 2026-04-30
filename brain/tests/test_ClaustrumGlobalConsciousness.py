"""Behavioral tests for ClaustrumGlobalConsciousness."""
import asyncio
from brain.integration.ClaustrumGlobalConsciousness import ClaustrumGlobalConsciousness


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_coherent_cortical_signals_drive_binding():
    """Crick 2005: claustrum binds when cortical signals are coherent."""
    m = ClaustrumGlobalConsciousness()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.60},
            "InsulaAnterior": {"aic_drive": 0.62},
            "PrimaryVisualCortex": {"v1_drive": 0.58},
            "ArousalRegulator": {"tonic_level": 0.65},
        })
    assert out["claustrum_drive"] > 0.30
    assert out["coherence_index"] > 0.30  # signals are similar magnitude
    assert out["global_binding_signal"] > 0.20
    assert out["claustrum_state"] in ("binding", "broadcasting")


def test_low_arousal_engages_slow_wave():
    """Norimoto 2020 / Atlan 2018: low arousal → slow-wave modulation."""
    m = ClaustrumGlobalConsciousness()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.45},
            "PrimaryVisualCortex": {"v1_drive": 0.40},
            "ArousalRegulator": {"tonic_level": 0.10},  # asleep
        })
    assert out["slow_wave_modulation"] > 0.20
    assert out["claustrum_state"] == "slow_wave"
    # Conscious access should be CLOSED during sleep
    assert out["conscious_access_gate"] < 0.20


def test_incoherent_cortical_signals_dont_bind():
    """Bind requires coherence — incoherent input shouldn't produce binding."""
    m = ClaustrumGlobalConsciousness()
    out = None
    # Big mismatch: one signal at 0.85, others near 0
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.85},
            "PrimaryVisualCortex": {"v1_drive": 0.05},
            "PrimaryAuditoryCortex": {"a1_drive": 0.05},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["coherence_index"] < 0.30


def test_quiet_no_input():
    m = ClaustrumGlobalConsciousness()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["claustrum_state"] == "quiet"
