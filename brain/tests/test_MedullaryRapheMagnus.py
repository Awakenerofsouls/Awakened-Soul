"""
Behavioral tests for MedullaryRapheMagnus.
"""

import asyncio

from brain.mechanisms.MedullaryRapheMagnus import MedullaryRapheMagnus


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    def test_required_keys_present(self):
        mech = MedullaryRapheMagnus()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['nrm_5ht_drive', 'on_cell_drive', 'off_cell_drive', 'net_descending_modulation', 'spinal_5ht_release', 'centralized_pain_drift', 'bidirectional_balance', 'descending_facilitatory_shift', 'rvm_serotonin_ascending_mood']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    def test_baseline_numeric_outputs_bounded(self):
        mech = MedullaryRapheMagnus()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"

    def test_saturated_inputs_stay_bounded(self):
        mech = MedullaryRapheMagnus()
        prior = {dep: {"_saturated": 1.0} for dep in ['ArousalRegulator', 'DorsalRapheSerotonin', 'PeriaqueductalDefenseRouter', 'DescendingPainGate']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"


class TestStability:
    def test_repeated_ticks_no_crash(self):
        mech = MedullaryRapheMagnus()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"

    def test_tick_count_increments(self):
        mech = MedullaryRapheMagnus()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5
