"""
Behavioral tests for Build 21: FluidBalanceWatcher (SFO thirst).

Run:
    pytest brain/tests/test_fluid_balance_watcher.py -v
"""

import asyncio
import pytest

from brain.foundational.Foundational012FluidBalanceWatcher import FluidBalanceWatcher


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestThirstDrive:
    """SFO thirst drive responds to osmolality and RAS activation."""

    def test_baseline_thirst_in_normal_range(self):
        mech = FluidBalanceWatcher()
        for _ in range(20):
            result = _run(mech.tick({"prior_results": {}}))
        assert 0.0 <= result["thirst_drive"] <= 0.80

    def test_high_osmolality_elevates_thirst(self):
        mech = FluidBalanceWatcher()
        prior = {"BrainRunner": {"plasma_osmolality": 0.80}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["thirst_drive"] > 0.30

    def test_normal_osmolality_suppresses_thirst(self):
        mech = FluidBalanceWatcher()
        prior = {"BrainRunner": {"plasma_osmolality": 0.35}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["thirst_drive"] < 0.30


class TestAngiotensinSignal:
    """CRH activates renin-angiotensin system → thirst."""

    def test_crh_activates_angiotensin_signal(self):
        mech = FluidBalanceWatcher()
        prior = {"StressActivationAxis": {"crh_level": 0.70}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["angiotensin_signal"] > 0.0

    def test_hungry_metabolic_state_activates_angiotensin(self):
        mech = FluidBalanceWatcher()
        prior = {"Homeostat": {"metabolic_state": "hungry"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["angiotensin_signal"] > 0.0


class TestNatriureticSuppression:
    """Natriuretic peptides suppress thirst."""

    def test_gut_distress_low_osmolality_triggers_natriuretic_suppression(self):
        mech = FluidBalanceWatcher()
        prior = {
            "BrainRunner": {"plasma_osmolality": 0.30},
            "GutSignalRelay": {"gut_distress": 0.60},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["natriuretic_suppression"] > 0.0

    def test_natriuretic_suppression_reduces_thirst(self):
        mech = FluidBalanceWatcher()
        prior_no_suppression = {
            "BrainRunner": {"plasma_osmolality": 0.70},
            "GutSignalRelay": {"gut_distress": 0.0},
        }
        prior_with_suppression = {
            "BrainRunner": {"plasma_osmolality": 0.70},
            "GutSignalRelay": {"gut_distress": 0.60},
        }
        for _ in range(20):
            _run(mech.tick({"prior_results": prior_no_suppression}))
        result_no = _run(mech.tick({"prior_results": prior_no_suppression}))

        for _ in range(20):
            _run(mech.tick({"prior_results": prior_with_suppression}))
        result_with = _run(mech.tick({"prior_results": prior_with_suppression}))
        assert result_with["thirst_drive"] < result_no["thirst_drive"]


class TestDipsogenicThreshold:
    """Thirst drive above threshold activates dipsogenic behavior."""

    def test_high_osmolality_crosses_threshold(self):
        mech = FluidBalanceWatcher()
        prior = {"BrainRunner": {"plasma_osmolality": 0.85}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["dipsogenic_threshold_crossed"] is True

    def test_normal_osmolality_below_threshold(self):
        mech = FluidBalanceWatcher()
        prior = {"BrainRunner": {"plasma_osmolality": 0.35}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["dipsogenic_threshold_crossed"] is False


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = FluidBalanceWatcher()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["thirst_drive", "angiotensin_signal",
                    "natriuretic_suppression", "dipsogenic_threshold_crossed"]:
            assert key in result
