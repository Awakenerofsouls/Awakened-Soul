"""Behavioral tests for SubstantiaNigraReticulata."""
import asyncio
from brain.mechanisms.SubstantiaNigraReticulata import SubstantiaNigraReticulata


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_stn_drive_engages_tonic_inhibition():
    """STN excitation engages SNr tonic output to SC and thalamus
    (Hikosaka 2000)."""
    m = SubstantiaNigraReticulata()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SubthalamicNucleus": {"stn_drive": 0.65},
        })
    assert out["snr_drive"] > 0.30
    assert out["collicular_inhibition"] > 0.20
    assert out["thalamic_inhibition"] > 0.15
    assert out["snr_state"] in ("tonic_inhibit", "boosted_inhibit")


def test_d1_caudate_pauses_snr():
    """D1 striatal direct path inhibits SNr — releasing SC for saccade
    (Hikosaka 1983)."""
    m_d1 = SubstantiaNigraReticulata()
    m_no_d1 = SubstantiaNigraReticulata()
    out_a = None
    out_b = None
    for _ in range(15):
        out_a = _tick(m_d1, {
            "DorsomedialStriatum": {"d1_direct_output": 0.85},
            "DorsolateralStriatum": {"d1_direct_output": 0.40},
            "SubthalamicNucleus": {"stn_drive": 0.20},
        })
        out_b = _tick(m_no_d1, {
            "DorsomedialStriatum": {"d1_direct_output": 0.05},
            "DorsolateralStriatum": {"d1_direct_output": 0.05},
            "SubthalamicNucleus": {"stn_drive": 0.20},
        })
    # D1 inhibits SNr → lower drive AND saccade gate signal active
    assert out_a["snr_drive"] < out_b["snr_drive"]
    assert out_a["saccade_gate_signal"] > out_b["saccade_gate_signal"]


def test_saccade_gate_state_triggered():
    """Strong DMS D1 with weaker STN → saccade gate state."""
    m = SubstantiaNigraReticulata()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "DorsomedialStriatum": {"d1_direct_output": 0.85},
            "SubthalamicNucleus": {"stn_drive": 0.10},
        })
    assert out["saccade_gate_signal"] > 0.20


def test_quiet_no_input():
    m = SubstantiaNigraReticulata()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["snr_state"] == "quiet"
