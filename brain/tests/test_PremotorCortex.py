"""Behavioral tests for PremotorCortex."""
import asyncio
from brain.neocortical.PremotorCortex import PremotorCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_ips_ppc_drive_pmd_selection():
    """Strong parietal input (IPS+PPC) should engage PMd reach selection."""
    m = PremotorCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "IntraparietalSulcus": {"ips_drive": 0.65, "reach_direction": "right"},
            "PosteriorParietalCortex": {"ppc_drive": 0.55},
        })
    assert out["pmc_drive"] > 0.30
    assert out["pmd_drive"] > 0.30
    assert out["reach_direction"] == "right"
    assert out["pmc_state"] in ("selecting", "executing_plan")


def test_visual_input_drives_pmv_mirror():
    """Visual + grasp signals drive PMv mirror activity (Rizzolatti 1996)."""
    m = PremotorCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualCortexV1": {"v1_drive": 0.60},
            "IntraparietalSulcus": {"ips_drive": 0.50},
        })
    assert out["pmv_drive"] > 0.20
    assert out["mirror_neuron_signal"] > 0.15


def test_action_competition_with_dual_targets():
    """Concurrent PMd+PPC drive raises affordance-competition signal."""
    m = PremotorCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "IntraparietalSulcus": {"ips_drive": 0.60},
            "PosteriorParietalCortex": {"ppc_drive": 0.60},
            "PrelimbicCortex": {"prelimbic_drive": 0.40},
        })
    assert out["action_competition"] > 0.20


def test_quiet_no_input():
    m = PremotorCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["pmc_state"] == "quiet"
