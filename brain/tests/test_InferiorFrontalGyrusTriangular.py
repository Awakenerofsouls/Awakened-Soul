"""
Behavioral tests for InferiorFrontalGyrusTriangular (legacy numbered file).
"""

import asyncio

from brain.mechanisms.Neocortical034InferiorFrontalGyrusTriangular import InferiorFrontalGyrusTriangular


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestMechanismBasic:
    def test_instantiation(self):
        mech = InferiorFrontalGyrusTriangular()
        assert mech is not None

    def test_tick_returns_dict(self):
        mech = InferiorFrontalGyrusTriangular()
        result = _run(mech.tick({"prior_results": {}}))
        assert isinstance(result, dict)

    def test_repeated_ticks_no_crash(self):
        mech = InferiorFrontalGyrusTriangular()
        for _ in range(20):
            _run(mech.tick({"prior_results": {}}))

    def test_summary_returns_dict(self):
        mech = InferiorFrontalGyrusTriangular()
        for _ in range(5):
            _run(mech.tick({"prior_results": {}}))
        if hasattr(mech, "summary"):
            assert isinstance(mech.summary(), dict)
