"""
Behavioral tests for AnteriorHypothalamicCooling.

Run:
    pytest brain/tests/test_AnteriorHypothalamicCooling.py -v
"""

import asyncio

from brain.mechanisms.AnteriorHypothalamicCooling import AnteriorHypothalamicCooling


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    """All declared output keys are present every tick."""

    def test_required_keys_present(self):
        mech = AnteriorHypothalamicCooling()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['cooling_signal', 'warm_exposure_flag', 'behavioral_thermoregulation', 'preoptic_sleep_gate', 'poa_temperature_index']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    """Numeric outputs stay in [0.0, 1.0] under empty and saturating input."""

    def test_baseline_numeric_outputs_bounded(self):
        mech = AnteriorHypothalamicCooling()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert 0.0 <= float(v) <= 1.0, f"{k}={v} out of [0,1]"

    def test_saturated_inputs_stay_bounded(self):
        mech = AnteriorHypothalamicCooling()
        prior = {dep: {"_saturated": 1.0} for dep in ['PassiveQuiescenceMode', 'CoreTemperatureMonitor', 'AmbientTemperatureRelay', 'PeripheralTemperature']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert 0.0 <= float(v) <= 1.0, f"{k}={v} out of [0,1]"


class TestStatePersistence:
    """Internal state advances across ticks."""

    def test_tick_count_increments(self):
        mech = AnteriorHypothalamicCooling()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5


class TestStability:
    """Repeated ticks neither crash nor produce NaN/None numerics."""

    def test_repeated_ticks_no_crash(self):
        mech = AnteriorHypothalamicCooling()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"
                assert v is not None
