"""
Behavioral tests for IntraPipelineRuleMutationSilenceAnchorAdapter.
"""

import asyncio

from brain.mechanisms.IntraPipelineRuleMutationSilenceAnchorAdapter import IntraPipelineRuleMutationSilenceAnchorAdapter


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestAdapterBasic:
    def test_instantiation_does_not_crash(self):
        mech = IntraPipelineRuleMutationSilenceAnchorAdapter()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = IntraPipelineRuleMutationSilenceAnchorAdapter()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = IntraPipelineRuleMutationSilenceAnchorAdapter()
        for _ in range(20):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state.get("tick_count", 0) >= 0

    def test_summary_returns_dict(self):
        mech = IntraPipelineRuleMutationSilenceAnchorAdapter()
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        if hasattr(mech, "summary"):
            s = mech.summary()
            assert isinstance(s, dict)
