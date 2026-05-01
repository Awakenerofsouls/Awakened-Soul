"""Behavioral tests for PredictionErrorDrift."""

import asyncio
from brain.mechanisms.Subcortical027SubstantiaNigraCompactaCognitive import PredictionErrorDrift


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestMechanismBasic:
    def test_instantiation(self):
        mech = PredictionErrorDrift()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = PredictionErrorDrift()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = PredictionErrorDrift()
        for _ in range(15):
            _run(mech.tick({"prior_results": {}}))
