"""Behavioral tests for GlobusPallidusInternal."""
import asyncio
from brain.subcortical.GlobusPallidusInternal import GlobusPallidusInternal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_stn_drive_engages_tonic_inhibition():
    """STN excitation engages tonic GPi inhibition of thalamus
    (DeLong 1990)."""
    m = GlobusPallidusInternal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SubthalamicNucleus": {"stn_drive": 0.65},
            "DorsolateralStriatum": {"d1_direct_output": 0.10},
        })
    assert out["gpi_drive"] > 0.30
    assert out["thalamic_inhibition"] > 0.20
    assert out["gpi_state"] in ("tonic_inhibit", "boosted_inhibit")


def test_d1_drive_pauses_gpi():
    """D1 direct-pathway should pause/reduce GPi (action gating —
    Albin 1989)."""
    m_d1 = GlobusPallidusInternal()
    m_no_d1 = GlobusPallidusInternal()
    out_a = None
    out_b = None
    for _ in range(15):
        out_a = _tick(m_d1, {
            "DorsolateralStriatum": {"d1_direct_output": 0.85},
            "DorsomedialStriatum": {"d1_direct_output": 0.80},
            "SubthalamicNucleus": {"stn_drive": 0.20},
        })
        out_b = _tick(m_no_d1, {
            "DorsolateralStriatum": {"d1_direct_output": 0.05},
            "SubthalamicNucleus": {"stn_drive": 0.20},
        })
    # D1 inhibits GPi → lower drive
    assert out_a["gpi_drive"] < out_b["gpi_drive"]


def test_high_stn_boosts_inhibition():
    """Indirect-pathway burst (STN high) should boost GPi (Mink 1996)."""
    m = GlobusPallidusInternal()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "SubthalamicNucleus": {"stn_drive": 0.90},
            "DorsolateralStriatum": {"d1_direct_output": 0.05},
        })
    assert out["gpi_drive"] > 0.50


def test_quiet_no_input():
    m = GlobusPallidusInternal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["gpi_state"] == "quiet"
