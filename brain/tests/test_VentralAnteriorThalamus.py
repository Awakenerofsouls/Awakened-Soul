"""Behavioral tests for VentralAnteriorThalamus."""
import asyncio
from brain.mechanisms.VentralAnteriorThalamus import VentralAnteriorThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_disinhibition_releases_va():
    """Pause in GPi/SNr (low values) plus cortical drive releases VA."""
    m = VentralAnteriorThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "GlobusPallidusInternal": {"gpi_output": 0.10},
            "SubstantiaNigraReticulata": {"snr_output": 0.10},
            "MotorCortex": {"cortical_drive": 0.55},
            "PedunculopontineCholinergic": {"ach_drive": 0.40},
        })
    assert out["va_drive"] > 0.30
    assert out["disinhibition_event"] > 0.30
    assert out["layer1_motor_signal"] > 0.20
    assert out["gating_state"] in ("released", "modulated")


def test_high_bg_inhibition_gates_va():
    """High GPi/SNr tonic firing should suppress VA into 'gated' state."""
    m = VentralAnteriorThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "GlobusPallidusInternal": {"gpi_output": 0.85},
            "SubstantiaNigraReticulata": {"snr_output": 0.85},
            "MotorCortex": {"cortical_drive": 0.40},
        })
    assert out["disinhibition_event"] < 0.05
    assert out["gating_state"] in ("gated", "quiet")


def test_release_vs_gated_differential():
    """Two regimes: low BG vs high BG should produce different drives."""
    m_release = VentralAnteriorThalamus()
    m_gate = VentralAnteriorThalamus()
    out_r = None
    out_g = None
    for _ in range(15):
        out_r = _tick(m_release, {
            "GlobusPallidusInternal": {"gpi_output": 0.05},
            "SubstantiaNigraReticulata": {"snr_output": 0.05},
            "MotorCortex": {"cortical_drive": 0.50},
        })
        out_g = _tick(m_gate, {
            "GlobusPallidusInternal": {"gpi_output": 0.85},
            "SubstantiaNigraReticulata": {"snr_output": 0.85},
            "MotorCortex": {"cortical_drive": 0.50},
        })
    assert out_r["va_drive"] > out_g["va_drive"] + 0.10
    assert out_r["layer1_motor_signal"] > out_g["layer1_motor_signal"]


def test_quiet_no_input():
    m = VentralAnteriorThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["gating_state"] == "quiet"
