"""
Behavioral tests for Build 20: ThermoSleepGate (MnPO thermoregulatory sleep gate).

Run:
    pytest brain/tests/test_thermo_sleep_gate.py -v
"""

import asyncio
import pytest

from brain.foundational.Foundational011ThermoSleepGate import ThermoSleepGate


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestWarmthDrive:
    """MnPO warmth index tracks thermoregulatory state."""

    def test_baseline_warmth_in_normal_range(self):
        mech = ThermoSleepGate()
        for _ in range(20):
            result = _run(mech.tick({"prior_results": {}}))
        assert 0.30 <= result["warmth_index"] <= 0.70

    def test_high_core_temperature_elevates_warmth(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.80}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["warmth_index"] > 0.55

    def test_low_core_temperature_suppresses_warmth(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.20}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["warmth_index"] < 0.45


class TestSleepGate:
    """Sleep gate opens when warmth is high."""

    def test_sleep_gate_opens_at_high_warmth(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.80}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["sleep_gate_open"] is True

    def test_sleep_gate_closed_at_low_warmth(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.20}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["sleep_gate_open"] is False


class TestFeverMode:
    """Fever amplifies the sleep gate."""

    def test_fever_mode_detected_at_high_temperature(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.85}}
        for _ in range(10):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["fever_mode"] is True

    def test_gut_distress_can_trigger_fever_mode(self):
        """Gut distress simulating fever also activates fever mode."""
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.60}, "GutSignalRelay": {"gut_distress": 0.90}}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["fever_mode"] is True


class TestOrexinOpposition:
    """Orexin opposes the sleep gate (wake-promoting overrides warmth)."""

    def test_high_orexin_suppresses_warmth_index(self):
        mech = ThermoSleepGate()
        prior_base = {"BrainRunner": {"core_temperature": 0.70}}
        for _ in range(10):
            _run(mech.tick({"prior_results": prior_base}))
        result_base = mech.state["warmth_index"]

        prior_high_orexin = {
            "BrainRunner": {"core_temperature": 0.70},
            "OrexinWakePromoter": {"orexin_tone": 0.85},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior_high_orexin}))
        assert result["warmth_index"] < result_base


class TestTemperatureDeficit:
    """Cold exposure creates a temperature deficit signal."""

    def test_low_temperature_produces_deficit(self):
        mech = ThermoSleepGate()
        prior = {"BrainRunner": {"core_temperature": 0.20}}
        result = _run(mech.tick({"prior_results": prior}))
        assert result["temperature_deficit"] > 0.0


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = ThermoSleepGate()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["warmth_index", "sleep_gate_open", "fever_mode", "temperature_deficit"]:
            assert key in result
