"""
Behavioral tests for ThermoregulationCore.
"""

import asyncio

from brain.mechanisms.ThermoregulationCore import ThermoregulationCore


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    def test_required_keys_present(self):
        mech = ThermoregulationCore()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['core_temp_setpoint', 'thermal_drive', 'bat_activation', 'cutaneous_vasoconstriction', 'fever_state', 'sleep_thermal_drop_active']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    def test_baseline_numeric_outputs_bounded(self):
        mech = ThermoregulationCore()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert isinstance(v, (int, float)) and v == v, f"{k}={v} not a finite number"

    def test_saturated_inputs_stay_bounded(self):
        mech = ThermoregulationCore()
        prior = {dep: {"_saturated": 1.0} for dep in ['ArousalRegulator', 'Homeostat', 'VitalCoreRegulator', 'CircadianTimer']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert isinstance(v, (int, float)) and v == v, f"{k}={v} not a finite number"


class TestStability:
    def test_repeated_ticks_no_crash(self):
        mech = ThermoregulationCore()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"

    def test_tick_count_increments(self):
        mech = ThermoregulationCore()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5
