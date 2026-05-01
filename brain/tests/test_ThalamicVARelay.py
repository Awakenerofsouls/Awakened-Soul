"""
Behavioral tests for ThalamicVARelay (legacy numbered file).
"""

import asyncio

from brain.mechanisms.Subcortical018ThalamicVentralAnteriorRelay import ThalamicVARelay


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestMechanismBasic:
    def test_instantiation(self):
        mech = ThalamicVARelay()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = ThalamicVARelay()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = ThalamicVARelay()
        for _ in range(20):
            _run(mech.tick({"prior_results": {}}))

    def test_summary_returns_dict(self):
        mech = ThalamicVARelay()
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        if hasattr(mech, "summary"):
            assert isinstance(mech.summary(), dict)
