"""
Behavioral tests for DualFailureAttractorFieldAdapter.
"""

import asyncio

from brain.mechanisms.DualFailureAttractorFieldAdapter import DualFailureAttractorFieldAdapter


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestAdapterBasic:
    def test_instantiation_does_not_crash(self):
        mech = DualFailureAttractorFieldAdapter()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = DualFailureAttractorFieldAdapter()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = DualFailureAttractorFieldAdapter()
        for _ in range(20):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) >= 0

    def test_summary_returns_dict(self):
        mech = DualFailureAttractorFieldAdapter()
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        if hasattr(mech, "summary"):
            s = mech.summary()
            assert isinstance(s, dict)
