"""
Behavioral tests for AreaPostremaToxinGuard.

Run:
    pytest brain/tests/test_AreaPostremaToxinGuard.py -v
"""

import asyncio

from brain.mechanisms.AreaPostremaToxinGuard import AreaPostremaToxinGuard


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
        mech = AreaPostremaToxinGuard()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['toxin_detected', 'nausea_intensity', 'emesis_threshold_proximity', 'aversive_interoceptive_signal', 'ap_5ht3_drive', 'ap_d2_drive', 'food_aversion_active', 'emesis_count', 'chronic_nausea_load', 'chronic_active', 'taste_aversion_forming']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    """Numeric outputs stay in [0.0, 1.0] under empty and saturating input."""

    def test_baseline_numeric_outputs_bounded(self):
        mech = AreaPostremaToxinGuard()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert 0.0 <= float(v) <= 1.0, f"{k}={v} out of [0,1]"

    def test_saturated_inputs_stay_bounded(self):
        mech = AreaPostremaToxinGuard()
        prior = {dep: {"_saturated": 1.0} for dep in ['DorsalRapheSerotonin', 'AppetiteNPYBalancer', 'VitalCoreRegulator', 'StressActivationAxis']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert 0.0 <= float(v) <= 1.0, f"{k}={v} out of [0,1]"


class TestStatePersistence:
    """Internal state advances across ticks."""

    def test_tick_count_increments(self):
        mech = AreaPostremaToxinGuard()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5


class TestStability:
    """Repeated ticks neither crash nor produce NaN/None numerics."""

    def test_repeated_ticks_no_crash(self):
        mech = AreaPostremaToxinGuard()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"
                assert v is not None
