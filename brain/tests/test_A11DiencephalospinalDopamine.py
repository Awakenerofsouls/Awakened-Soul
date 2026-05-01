"""
Behavioral tests for A11DiencephalospinalDopamine.
"""

import asyncio

from brain.mechanisms.A11DiencephalospinalDopamine import A11DiencephalospinalDopamine


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    def test_required_keys_present(self):
        mech = A11DiencephalospinalDopamine()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['a11_drive', 'spinal_da_release', 'spinal_pain_modulation', 'iml_sympathetic_modulation', 'trigeminal_modulation', 'rls_marker', 'a11_state']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    def test_baseline_numeric_outputs_bounded(self):
        mech = A11DiencephalospinalDopamine()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"

    def test_saturated_inputs_stay_bounded(self):
        mech = A11DiencephalospinalDopamine()
        prior = {dep: {"_saturated": 1.0} for dep in ['SpinalDorsalHornGate', 'TrigeminalSensoryComplex', 'DescendingPainGate', 'ArousalRegulator', 'IronStatusProxy', 'SleepWakeFlipFlop', 'HypothalamicSupramammillary']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"


class TestStability:
    def test_repeated_ticks_no_crash(self):
        mech = A11DiencephalospinalDopamine()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"

    def test_tick_count_increments(self):
        mech = A11DiencephalospinalDopamine()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5
