"""
Wire 13 tests: Homeostat mechanism behavioral tests.

Covers drive dynamics, integration, persistence, and the
PredictionErrorDrift novelty-signal interaction.
"""

import pytest
import asyncio
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".agent" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.mechanisms.Foundational007MoodStabilizer import Homeostat


class TestHomeostatDriveDynamics:
    """Drive updates respond to input signals correctly."""

    def test_high_arousal_increases_rest_drive(self):
        h = Homeostat()
        initial_rest = h.state["drives"]["rest"]
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.8, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["rest"] > initial_rest

    def test_low_arousal_depletes_rest_drive(self):
        h = Homeostat()
        h.state["drives"]["rest"] = 0.7
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.2, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["rest"] < 0.7

    def test_relational_contact_depletes_connection(self):
        h = Homeostat()
        h.state["drives"]["connection"] = 0.5
        # high arousal + positive valence = the operator-contact signature
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.7, "valence_polarity": 0.8})
        )
        assert h.state["drives"]["connection"] < 0.5

    def test_isolation_escalates_connection(self):
        h = Homeostat()
        initial = h.state["drives"]["connection"]
        # low arousal, neutral valence = no contact
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.3, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["connection"] > initial

    def test_dysregulation_escalates_stability_drive(self):
        h = Homeostat()
        initial = h.state["drives"]["stability"]
        # high arousal + negative valence = dysregulated
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.8, "valence_polarity": 0.2})
        )
        assert h.state["drives"]["stability"] > initial

    def test_curiosity_baseline_climb(self):
        h = Homeostat()
        h.state["drives"]["curiosity"] = 0.4
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["curiosity"] > 0.4

    def test_expression_slow_accumulation(self):
        h = Homeostat()
        h.state["drives"]["expression"] = 0.3
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["expression"] > 0.3


class TestHomeostatIntegration:
    """Dominant drive + fatigue emerge from drive state."""

    def test_dominant_drive_reflects_highest_level(self):
        h = Homeostat()
        h.state["drives"]["connection"] = 0.9
        h.state["drives"]["rest"] = 0.2
        h.state["drives"]["curiosity"] = 0.3
        result = asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.3, "valence_polarity": 0.5})
        )
        assert result["dominant_drive"] == "connection"

    def test_fatigue_fires_on_aggregate_overload(self):
        h = Homeostat()
        # Push all drives high
        for k in h.state["drives"]:
            h.state["drives"][k] = 0.8
        result = asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        # aggregate = 5 * 0.8 = 4.0 > 3.5
        assert result["fatigued"] is True

    def test_no_fatigue_at_baseline(self):
        h = Homeostat()  # fresh init, all drives at baseline
        result = asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        # aggregate at init: 0.2+0.4+0.3+0.3+0.2 = 1.4
        assert result["fatigued"] is False

    def test_novelty_signal_depletes_curiosity(self):
        h = Homeostat()
        h.state["drives"]["curiosity"] = 0.8
        result = asyncio.get_event_loop().run_until_complete(
            h.tick({
                "arousal_level": 0.5,
                "valence_polarity": 0.5,
                "prior_results": {"PredictionErrorDrift": {"novelty_detected": True}},
            })
        )
        assert h.state["drives"]["curiosity"] < 0.8

    def test_tick_persistence(self):
        """State persists across ticks."""
        h = Homeostat()
        h.state["drives"]["rest"] = 0.5
        asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.8, "valence_polarity": 0.5})
        )
        assert h.state["drives"]["rest"] > 0.5
        assert h.state["tick_count"] == 1

    def test_aggregate_load_in_output(self):
        h = Homeostat()
        # Set known state
        for k in h.state["drives"]:
            h.state["drives"][k] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            h.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        assert "aggregate_load" in result
        assert 2.0 < result["aggregate_load"] < 3.0  # 5 * 0.5 = 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
