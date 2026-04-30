"""Behavioral tests for IntraparietalSulcus (IPS)."""
import asyncio
from brain.neocortical.IntraparietalSulcus import IntraparietalSulcus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_visual_drive_engages_ips_grasp():
    """Visual drive + posterior parietal should engage AIP grasp signal."""
    m = IntraparietalSulcus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualCortexV1": {"v1_drive": 0.65, "salient_direction": "right"},
            "PosteriorParietalCortex": {"ppc_drive": 0.55, "spatial_direction": "right"},
        })
    assert out["ips_drive"] > 0.30
    assert out["aip_grasp_signal"] > 0.20
    assert out["reach_direction"] == "right"


def test_numerosity_cue_engages_hips():
    """An upstream numerosity_cue should engage IPS numerosity signal (Nieder/Dehaene)."""
    m = IntraparietalSulcus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualCortexV1": {"v1_drive": 0.55, "numerosity_cue": 0.65},
        })
    assert out["numerosity_signal"] > 0.25


def test_pulvinar_gates_lip():
    """Pulvinar attention input should boost LIP saccade signal."""
    m1 = IntraparietalSulcus()
    m2 = IntraparietalSulcus()
    no_pulv = None
    with_pulv = None
    for _ in range(15):
        no_pulv = _tick(m1, {
            "VisualCortexV1": {"v1_drive": 0.45},
        })
        with_pulv = _tick(m2, {
            "VisualCortexV1": {"v1_drive": 0.45},
            "PulvinarAttentionVisual": {"pulvinar_drive": 0.70},
        })
    assert with_pulv["lip_saccade_signal"] > no_pulv["lip_saccade_signal"]


def test_quiet_no_input():
    m = IntraparietalSulcus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ips_state"] == "quiet"
