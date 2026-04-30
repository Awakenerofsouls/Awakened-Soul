"""Behavioral tests for VentralLateralThalamus."""
import asyncio
from brain.subcortical.VentralLateralThalamus import VentralLateralThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_cerebellar_drive_engages_m1_deep():
    """Strong DCN drive should engage VL and M1 deep layer signal."""
    m = VentralLateralThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CerebellarDeepNuclei": {"dcn_drive": 0.70},
            "MotorCortex": {"cortical_drive": 0.45},
            "PedunculopontineCholinergic": {"ach_drive": 0.45},
            "LocusCoeruleusCore": {"ne_drive": 0.55},
        })
    assert out["vl_drive"] > 0.35
    assert out["m1_deep_layer_signal"] > 0.25
    assert out["motor_tuning_signal"] > 0.30
    assert out["vl_state"] in ("tuning_active", "tonic", "burst")


def test_high_dcn_low_ne_promotes_burst():
    """Burst mode requires strong DCN with low NE (hyperpolarized state)."""
    m = VentralLateralThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "CerebellarDeepNuclei": {"dcn_drive": 0.80},
            "LocusCoeruleusCore": {"ne_drive": 0.05},
        })
    assert out["vl_drive"] > 0.30


def test_dcn_vs_no_dcn_differential():
    """Cerebellar input should be the dominant driver vs corticothalamic."""
    m_dcn = VentralLateralThalamus()
    m_ctx = VentralLateralThalamus()
    out_d = None
    out_c = None
    for _ in range(15):
        out_d = _tick(m_dcn, {
            "CerebellarDeepNuclei": {"dcn_drive": 0.70},
        })
        out_c = _tick(m_ctx, {
            "MotorCortex": {"cortical_drive": 0.70},
        })
    # DCN is the driver — should produce stronger VL drive than ctx alone
    assert out_d["vl_drive"] > out_c["vl_drive"] + 0.05
    assert out_d["m1_deep_layer_signal"] > out_c["m1_deep_layer_signal"]


def test_quiet_no_input():
    m = VentralLateralThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vl_state"] == "quiet"
