"""
Behavioral tests for OlfactoryBulb.
"""

import asyncio

from brain.mechanisms.OlfactoryBulb import OlfactoryBulb


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    def test_required_keys_present(self):
        mech = OlfactoryBulb()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ['mob_mitral_drive', 'aob_mitral_drive', 'glomerular_drive', 'granule_inhibition', 'piriform_relay', 'mea_pheromone_relay', 'gamma_oscillation', 'ob_state']:
            assert key in result, f"missing output key: {key}"


class TestNumericBounds:
    def test_baseline_numeric_outputs_bounded(self):
        mech = OlfactoryBulb()
        for _ in range(10):
            result = _run(mech.tick({"prior_results": {}}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"

    def test_saturated_inputs_stay_bounded(self):
        mech = OlfactoryBulb()
        prior = {dep: {"_saturated": 1.0} for dep in ['NorepiPhasicTonicSwitcher', 'PreBotzingerInspiration', 'ArousalRegulator', 'NucleusBasalisAcetylcholine', 'OdorantInputProxy']}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -1.0 <= float(v) <= 1.0, f"{k}={v} out of [-1,1]"


class TestStability:
    def test_repeated_ticks_no_crash(self):
        mech = OlfactoryBulb()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, float):
                assert v == v, f"{k} produced NaN"

    def test_tick_count_increments(self):
        mech = OlfactoryBulb()
        start = mech.state.get("tick_count", 0)
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) == start + 5
