"""Behavioral tests for CingulumBundleAssociativeBridge."""
import asyncio
from brain.integration.CingulumBundleAssociativeBridge import CingulumBundleAssociativeBridge


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_executive_route_when_frontal_active():
    """Bubb 2018: dorsal cingulum carries frontal-cingulate-parietal."""
    m = CingulumBundleAssociativeBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CingulateAnterior": {"acc_drive": 0.65},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "PosteriorParietalCortex": {"ppc_drive": 0.55},
        })
    assert out["dorsal_cingulum_signal"] > 0.30
    assert out["cingulum_state"] in ("executive_route", "fragmented")


def test_memory_route_when_temporal_active():
    """Aggleton 2014: parahippocampal cingulum = memory traffic."""
    m = CingulumBundleAssociativeBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Dorsal": {"ca1d_drive": 0.65},
            "ParahippocampalPlaceArea": {"ppa_drive": 0.55},
            "CingulatePosterior": {"pcc_drive": 0.55},
        })
    assert out["parahippocampal_cingulum_signal"] > 0.30
    assert out["cingulum_state"] in ("memory_route", "fragmented")


def test_papez_return_with_atn_acc():
    """Subcortical cingulum carries Papez return arm."""
    m = CingulumBundleAssociativeBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AnteroVentralThalamus": {"atn_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.55},
        })
    assert out["subcortical_cingulum_signal"] > 0.30


def test_quiet_no_input():
    m = CingulumBundleAssociativeBridge()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["cingulum_state"] == "quiet"
