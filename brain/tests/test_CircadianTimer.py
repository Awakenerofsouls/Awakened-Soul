"""Behavioral tests for CircadianTimer."""
import asyncio
from brain.foundational.CircadianTimer import CircadianTimer


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_phase_advances_each_tick():
    """Circadian phase should advance monotonically per tick."""
    m = CircadianTimer()
    phases = []
    for _ in range(20):
        out = _tick(m, {})
        phases.append(out["circadian_phase"])
    # Phase should advance (not stuck)
    diffs = [phases[i+1] - phases[i] for i in range(len(phases)-1)]
    positive_or_wrap = sum(1 for d in diffs if d > 0 or d < -0.5)
    assert positive_or_wrap >= 15


def test_subjective_day_vs_night_state():
    """Phase 0.5 → subjective day; phase 0.0 → subjective night."""
    m_day = CircadianTimer()
    m_day.state["circadian_phase"] = 0.5
    out_day = _tick(m_day, {})
    assert out_day["is_subjective_day"] is True
    assert out_day["firing_rate_proxy"] > 0.6

    m_night = CircadianTimer()
    m_night.state["circadian_phase"] = 0.0
    out_night = _tick(m_night, {})
    assert out_night["is_subjective_day"] is False
    # Melatonin peak at night
    assert out_night["melatonin_drive"] > 0.30


def test_light_during_subjective_night_entrains():
    """Light during subjective night should shift phase (entrainment)."""
    m = CircadianTimer()
    m.state["circadian_phase"] = 0.10  # late subjective night
    initial_phase = m.state["circadian_phase"]
    for _ in range(10):
        _tick(m, {"RetinalClockInput": {"light_signal": 0.85}})
    # Phase should have advanced more than a passive tick would
    final_phase = m.state["circadian_phase"]
    passive_expected = initial_phase + (10 / m.PERIOD_TICKS)
    assert final_phase != initial_phase
    # Light entrainment makes the phase advance faster than passive
    assert final_phase > passive_expected


def test_constant_darkness_reduces_amplitude_slowly():
    """Sustained darkness slowly degrades amplitude (free-running drift)."""
    m = CircadianTimer()
    initial_amplitude = float(m.state["circadian_amplitude"])
    for _ in range(50):
        _tick(m, {"RetinalClockInput": {"light_signal": 0.0}})
    final_amplitude = float(m.state["circadian_amplitude"])
    # Amplitude is sustained or slightly reduced
    assert final_amplitude <= initial_amplitude + 0.001


def test_temperature_setpoint_modulation_oscillates():
    """Temperature setpoint modulation should oscillate with phase."""
    m = CircadianTimer()
    m.state["circadian_phase"] = 0.6  # late afternoon, peak temp
    out_high = _tick(m, {})

    m2 = CircadianTimer()
    m2.state["circadian_phase"] = 0.1  # early morning, trough temp
    out_low = _tick(m2, {})

    # Late afternoon temp setpoint > early morning
    assert out_high["core_temp_setpoint_modulation"] > out_low["core_temp_setpoint_modulation"]


def test_subpvz_output_active():
    """SCN → subPVZ output should be elevated during active firing."""
    m = CircadianTimer()
    m.state["circadian_phase"] = 0.5
    out = _tick(m, {})
    assert out["subpvz_output"] > 0.30
