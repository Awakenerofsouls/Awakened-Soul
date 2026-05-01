"""Behavioral tests for PrimaryMotorCortex (M1)."""
import asyncio
from brain.mechanisms.PrimaryMotorCortex import PrimaryMotorCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_pmc_sma_drive_m1_execution():
    """Strong premotor + SMA drive should engage M1 corticospinal output."""
    m = PrimaryMotorCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PremotorCortex": {"pmc_drive": 0.65, "reach_direction": "right"},
            "SupplementaryMotorArea": {"sma_drive": 0.55},
            "CerebellarDeepNuclei": {"cb_output": 0.40},
        })
    assert out["m1_drive"] > 0.30
    assert out["corticospinal_drive"] > 0.20
    assert out["m1_state"] in ("executing", "preparing", "fine_motor")
    assert out["preferred_direction"] == "right"


def test_low_input_keeps_m1_subthreshold():
    """Low premotor input should keep CST output low."""
    m = PrimaryMotorCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PremotorCortex": {"pmc_drive": 0.05},
            "SupplementaryMotorArea": {"sma_drive": 0.05},
        })
    assert out["corticospinal_drive"] < 0.30


def test_betz_scales_with_drive():
    """Betz cell drive should scale with sustained M1 activity."""
    m = PrimaryMotorCortex()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PremotorCortex": {"pmc_drive": 0.70},
            "SupplementaryMotorArea": {"sma_drive": 0.60},
            "CerebellarDeepNuclei": {"cb_output": 0.50},
            "IntraparietalSulcus": {"ips_drive": 0.40},
        })
    assert out["betz_cell_drive"] > 0.25


def test_quiet_no_input():
    m = PrimaryMotorCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["m1_state"] == "quiet"
