"""Behavioral tests for ThalamicVentralLateralMotor."""

import asyncio
from brain.mechanisms.Subcortical019ThalamicVentralLateralMotor import ThalamicVentralLateralMotor


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestMechanismBasic:
    def test_instantiation(self):
        mech = ThalamicVentralLateralMotor()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = ThalamicVentralLateralMotor()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = ThalamicVentralLateralMotor()
        for _ in range(15):
            _run(mech.tick({"prior_results": {}}))
