"""Behavioral tests for AnteroMedialThalamus."""
import asyncio
from brain.subcortical.AnteroMedialThalamus import AnteroMedialThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_papez_pfc_engages_integration():
    """Subicular + MMN + mPFC together should engage hippo-PFC bridge."""
    m = AnteroMedialThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MammillaryBodyMedial": {"mmn_drive": 0.55},
            "SubiculumDorsal": {"subiculum_output": 0.55},
            "PrelimbicCortex": {"cortical_drive": 0.55},
            "RetrosplenialCortex": {"cortical_drive": 0.40},
            "PerirhinalCortex": {"cortical_drive": 0.40},
        })
    assert out["am_drive"] > 0.30
    assert out["pfc_signal"] > 0.20
    assert out["hippo_pfc_bridge_signal"] > 0.20
    assert out["am_state"] in ("integrating", "recency_active", "relay")


def test_changing_perirhinal_input_drives_recency():
    """Variable perirhinal input should engage recency / temporal-order."""
    m = AnteroMedialThalamus()
    out = None
    inputs = [0.10, 0.70, 0.20, 0.65, 0.15, 0.60, 0.25, 0.55, 0.10, 0.50,
              0.30, 0.65, 0.20, 0.55, 0.10]
    for v in inputs:
        out = _tick(m, {
            "MammillaryBodyMedial": {"mmn_drive": 0.45},
            "SubiculumDorsal": {"subiculum_output": 0.40},
            "PerirhinalCortex": {"cortical_drive": v},
        })
    # variability should produce some temporal-order signal
    assert out["temporal_order_signal"] > 0.10


def test_isolated_pfc_vs_full_papez():
    """Full Papez + PFC drive should exceed PFC alone in bridge signal."""
    m_papez = AnteroMedialThalamus()
    m_pfc = AnteroMedialThalamus()
    out_p = None
    out_c = None
    for _ in range(15):
        out_p = _tick(m_papez, {
            "MammillaryBodyMedial": {"mmn_drive": 0.60},
            "SubiculumDorsal": {"subiculum_output": 0.55},
            "PrelimbicCortex": {"cortical_drive": 0.55},
        })
        out_c = _tick(m_pfc, {
            "PrelimbicCortex": {"cortical_drive": 0.55},
        })
    assert out_p["am_drive"] > out_c["am_drive"] + 0.05
    assert out_p["hippo_pfc_bridge_signal"] > out_c["hippo_pfc_bridge_signal"]


def test_quiet_no_input():
    m = AnteroMedialThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["am_state"] == "quiet"
