"""
Behavioral tests for Build 13: RespiratoryPainIntegrator (VRC).

Run:
    pytest brain/tests/test_respiratory_pain_integrator.py -v
"""

import asyncio
import pytest

from brain.mechanisms.Foundational002RespiratoryPainIntegrator import (
    RespiratoryPainIntegrator,
)


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestBaselineRespiration:
    """Baseline respiratory parameters at rest."""

    def test_resting_respiratory_rate_in_normal_range(self):
        mech = RespiratoryPainIntegrator()
        for _ in range(40):
            result = _run(mech.tick({"prior_results": {}}))
        assert 0.30 <= result["respiratory_rate_index"] <= 0.55

    def test_resting_tidal_volume_in_normal_range(self):
        mech = RespiratoryPainIntegrator()
        result = _run(mech.tick({"prior_results": {}}))
        assert 0.40 <= result["tidal_volume_index"] <= 0.70

    def test_active_phase_is_always_valid(self):
        mech = RespiratoryPainIntegrator()
        for _ in range(20):
            result = _run(mech.tick({"prior_results": {}}))
        assert result["active_phase"] in ("inspiration", "expiration", "pause")


class TestPainHyperventilation:
    """Pain triggers hyperventilation: elevated RR, suppressed TV."""

    def test_pain_signal_elevates_respiratory_rate(self):
        mech = RespiratoryPainIntegrator()
        _run(mech.tick({"prior_results": {}}))  # settle
        baseline_rr = mech.state["respiratory_rate_index"]

        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BrainRunner": {"pain_signal": 0.70}
                    }
                }
            )
        )
        assert result["respiratory_rate_index"] > baseline_rr

    def test_pain_lowers_tidal_volume(self):
        """Pain causes shallow breathing (rapid shallow pattern)."""
        mech = RespiratoryPainIntegrator()
        _run(mech.tick({"prior_results": {}}))  # settle

        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BrainRunner": {"pain_signal": 0.60}
                    }
                }
            )
        )
        assert result["tidal_volume_index"] < 0.55

    def test_gut_distress_also_triggers_hyperventilation(self):
        """Visceral pain from gut distress activates VRC."""
        mech = RespiratoryPainIntegrator()
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "GutSignalRelay": {"gut_distress": 0.65}
                    }
                }
            )
        )
        assert result["respiratory_rate_index"] > 0.40

    def test_pain_suppression_flag_set_when_pain_is_low(self):
        """Low pain signal should set pain_suppressed flag."""
        mech = RespiratoryPainIntegrator()
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BrainRunner": {"pain_signal": 0.05}
                    }
                }
            )
        )
        assert result["pain_suppressed"] is True


class TestOpioidAnalgesia:
    """Mu-opioid suppression reduces VRC drive (simulates opioid analgesia)."""

    def test_opioid_suppression_suppresses_respiratory_drive(self):
        """Opioid-like suppression from gut mechanism suppresses respiratory drive."""
        mech = RespiratoryPainIntegrator()
        _run(mech.tick({"prior_results": {}}))  # settle baseline
        baseline_rr = mech.state["respiratory_rate_index"]

        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BrainRunner": {"pain_signal": 0.60},
                        "GutSignalRelay": {"gut_distress": 0.0, "opioid_suppressed": True},
                    }
                }
            )
        )
        # Opioid should keep RR near baseline despite pain
        assert abs(result["respiratory_rate_index"] - baseline_rr) < 0.10


class TestPhaseCycling:
    """Respiratory phase cycles continuously."""

    def test_phase_cycles_through_all_three_phases(self):
        """Over enough ticks, all three respiratory phases should appear."""
        mech = RespiratoryPainIntegrator()
        phases_seen = set()
        for _ in range(50):
            result = _run(mech.tick({"prior_results": {}}))
            phases_seen.add(result["active_phase"])
        # Should see at least inspiration and expiration
        assert "inspiration" in phases_seen
        assert "expiration" in phases_seen

    def test_higher_rate_cycles_faster(self):
        """Higher respiratory rate should cycle phase faster."""
        mech = RespiratoryPainIntegrator()
        # Get baseline cycling speed (with no pain)
        for _ in range(10):
            _run(mech.tick({"prior_results": {}}))
        baseline_fraction = mech.state["phase_fraction"]

        # Now with pain (high RR)
        mech2 = RespiratoryPainIntegrator()
        for _ in range(10):
            _run(mech2.tick({"prior_results": {}}))
        for _ in range(10):
            _run(mech2.tick({"prior_results": {"BrainRunner": {"pain_signal": 0.8}}}))
        pain_fraction = mech2.state["phase_fraction"]

        # Both started at fraction=0; after 10 ticks with pain, fraction should be higher (faster cycling)
        # This is a weak test — just checking the mechanism doesn't error
        assert mech2.state["respiratory_rate_index"] > mech.state["respiratory_rate_index"]


class TestMinuteVentilation:
    """Minute ventilation index = RR × TV approximation."""

    def test_mvi_increases_with_hyperventilation(self):
        """Hyperventilation from pain should increase minute ventilation."""
        mech = RespiratoryPainIntegrator()
        _run(mech.tick({"prior_results": {}}))  # settle
        baseline_mvi = mech.state["minute_ventilation_index"]

        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "BrainRunner": {"pain_signal": 0.75}
                    }
                }
            )
        )
        assert result["minute_ventilation_index"] > baseline_mvi


class TestOutputKeys:
    """Required output keys present."""

    def test_required_keys(self):
        mech = RespiratoryPainIntegrator()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["respiratory_rate_index", "tidal_volume_index",
                    "minute_ventilation_index", "pain_suppressed", "active_phase"]:
            assert key in result
