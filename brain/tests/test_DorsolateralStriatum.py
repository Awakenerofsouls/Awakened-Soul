"""Behavioral tests for DorsolateralStriatum."""
import asyncio
from brain.subcortical.DorsolateralStriatum import DorsolateralStriatum


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_motor_input_drives_dls():
    m = DorsolateralStriatum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryMotorCortex": {"m1_drive": 0.65},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.55},
            "SubstantiaNigraCompacta": {"da_release_dls": 0.40},
        })
    assert out["dls_drive"] > 0.30
    assert out["d1_direct"] > 0.20


def test_habit_strength_grows_with_extended_training():
    """Yin 2004: habits require extended training to develop."""
    m = DorsolateralStriatum()
    out = None
    for _ in range(150):  # extended training
        out = _tick(m, {
            "PrimaryMotorCortex": {"m1_drive": 0.65},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.55},
            "SubstantiaNigraCompacta": {"da_release_dls": 0.50},
            "ValenceTagger": {"valence_intensity": 0.60, "valence_sign": 1},
        })
    assert out["habit_strength_signal"] > 0.20
    assert out["dls_state"] in ("habit_executing", "S-R_active")


def test_da_modulates_d1_d2_balance():
    """Kravitz 2010: high DA → D1 up, D2 down."""
    m_low_da = DorsolateralStriatum()
    out_low = None
    for _ in range(15):
        out_low = _tick(m_low_da, {
            "PrimaryMotorCortex": {"m1_drive": 0.55},
            "SubstantiaNigraCompacta": {"da_release_dls": 0.10},
        })

    m_high_da = DorsolateralStriatum()
    out_high = None
    for _ in range(15):
        out_high = _tick(m_high_da, {
            "PrimaryMotorCortex": {"m1_drive": 0.55},
            "SubstantiaNigraCompacta": {"da_release_dls": 0.85},
        })
    assert out_high["d1_direct"] > out_low["d1_direct"]
    assert out_high["d2_indirect"] < out_low["d2_indirect"]


def test_quiet_no_input():
    m = DorsolateralStriatum()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dls_state"] == "quiet"
