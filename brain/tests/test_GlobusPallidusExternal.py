"""Behavioral tests for GlobusPallidusExternal."""
import asyncio
from brain.subcortical.GlobusPallidusExternal import GlobusPallidusExternal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_tonic_activity_with_network_drive():
    """GPe shows tonic firing when reciprocal STN/striatum online
    (Bevan 2002 pacemaker)."""
    m = GlobusPallidusExternal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralStriatum": {"d2_indirect_output": 0.20},
            "SubthalamicNucleus": {"stn_drive": 0.45},
        })
    assert out["gpe_drive"] > 0.20
    assert out["gpe_state"] in ("tonic_active", "stop_gate")


def test_d2_input_disinhibits_gpe():
    """Heavy D2 striatal drive should suppress GPe firing."""
    m_high_d2 = GlobusPallidusExternal()
    m_low_d2 = GlobusPallidusExternal()
    out_h = None
    out_l = None
    for _ in range(15):
        out_h = _tick(m_high_d2, {
            "DorsolateralStriatum": {"d2_indirect_output": 0.85},
            "DorsomedialStriatum": {"d2_indirect_output": 0.80},
            "SubthalamicNucleus": {"stn_drive": 0.40},
        })
        out_l = _tick(m_low_d2, {
            "DorsolateralStriatum": {"d2_indirect_output": 0.05},
            "DorsomedialStriatum": {"d2_indirect_output": 0.05},
            "SubthalamicNucleus": {"stn_drive": 0.40},
        })
    # High D2 → MORE inhibition → lower GPe drive
    assert out_h["gpe_drive"] < out_l["gpe_drive"]


def test_stn_input_separates_arky_proto():
    """High STN should bias arkypallidal in-phase
    (Mallet 2012, Dodson 2015)."""
    m_high = GlobusPallidusExternal()
    m_low = GlobusPallidusExternal()
    out_h = None
    out_l = None
    for _ in range(15):
        out_h = _tick(m_high, {
            "DorsolateralStriatum": {"d2_indirect_output": 0.40},
            "SubthalamicNucleus": {"stn_drive": 0.85},
        })
        out_l = _tick(m_low, {
            "DorsolateralStriatum": {"d2_indirect_output": 0.40},
            "SubthalamicNucleus": {"stn_drive": 0.10},
        })
    assert out_h["arkypallidal_output"] > out_l["arkypallidal_output"]


def test_quiet_no_input():
    m = GlobusPallidusExternal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["gpe_state"] == "quiet"
