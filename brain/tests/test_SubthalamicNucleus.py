"""Behavioral tests for SubthalamicNucleus."""
import asyncio
from brain.mechanisms.SubthalamicNucleus import SubthalamicNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_vlpfc_hyperdirect_drives_stop():
    """Aron 2006: VLPFC/rIFC → STN hyperdirect = stop signal."""
    m = SubthalamicNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentrolateralPrefrontalCortex": {"vlpfc_drive": 0.85},
        })
    assert out["stn_drive"] > 0.30
    assert out["response_inhibition_signal"] > 0.40
    assert out["gpi_excitation"] > 0.30
    assert out["stn_state"] == "stop_active"


def test_acc_conflict_drives_hold():
    """Frank 2007: ACC conflict → STN raises decision threshold."""
    m = SubthalamicNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CingulateAnterior": {"acc_drive": 0.75},
        })
    assert out["conflict_hold_signal"] > 0.30
    assert out["stn_state"] == "conflict_hold"


def test_gpe_inhibition_dampens_stn():
    """Bevan 2002: STN-GPe reciprocal — high GPe inhibits STN."""
    m_no_gpe = SubthalamicNucleus()
    out_no = None
    for _ in range(15):
        out_no = _tick(m_no_gpe, {
            "VentrolateralPrefrontalCortex": {"vlpfc_drive": 0.55},
            "CingulateAnterior": {"acc_drive": 0.45},
        })

    m_gpe = SubthalamicNucleus()
    out_gpe = None
    for _ in range(15):
        out_gpe = _tick(m_gpe, {
            "VentrolateralPrefrontalCortex": {"vlpfc_drive": 0.55},
            "CingulateAnterior": {"acc_drive": 0.45},
            "GlobusPallidusExternal": {"gpe_drive": 0.85},
        })
    assert out_gpe["stn_drive"] < out_no["stn_drive"]


def test_pacemaker_baseline():
    """STN never silent — tonic baseline firing."""
    m = SubthalamicNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["stn_drive"] >= 0.10
    assert out["stn_state"] in ("pacemaker", "quiet")


def test_quiet_no_input():
    m = SubthalamicNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["stn_state"] in ("pacemaker", "quiet")
