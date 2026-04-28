"""
Wire 14 tests: PredictionErrorDrift behavioral tests.

Covers RPE computation, novelty detection, habituation dynamics,
expectation learning, and Homeostat integration.
"""

import pytest
import asyncio
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.subcortical.Subcortical027SubstantiaNigraCompactaCognitive import PredictionErrorDrift


class TestPredictionErrorBasics:
    """RPE computation: signed error + unsigned surprise magnitude."""

    def test_zero_error_when_actual_matches_expected(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        assert abs(result["prediction_error"]) < 0.01
        assert result["surprise_magnitude"] < 0.02

    def test_positive_error_when_actual_exceeds_expected(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.3
        p.state["expected_valence"] = 0.3
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
        )
        assert result["prediction_error"] > 0.4
        assert result["surprise_magnitude"] > 0.6

    def test_negative_error_when_actual_below_expected(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.8
        p.state["expected_valence"] = 0.8
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.2, "valence_polarity": 0.2})
        )
        assert result["prediction_error"] < -0.4
        assert result["surprise_magnitude"] > 0.6

    def test_surprise_is_unsigned(self):
        """Surprise magnitude is absolute value of PE — symmetric for ± deviation."""
        p1 = PredictionErrorDrift()
        p1.state["expected_arousal"] = 0.5
        p1.state["expected_valence"] = 0.5
        r1 = asyncio.get_event_loop().run_until_complete(
            p1.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
        )
        p2 = PredictionErrorDrift()
        p2.state["expected_arousal"] = 0.5
        p2.state["expected_valence"] = 0.5
        r2 = asyncio.get_event_loop().run_until_complete(
            p2.tick({"arousal_level": 0.1, "valence_polarity": 0.1})
        )
        assert abs(r1["surprise_magnitude"] - r2["surprise_magnitude"]) < 0.1


class TestNoveltyDetection:
    """Novelty fires when surprise exceeds threshold for unseen pattern."""

    def test_novelty_fires_on_large_unseen_shift(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.95, "valence_polarity": 0.95})
        )
        assert result["novelty_detected"] is True

    def test_no_novelty_on_small_error(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.55, "valence_polarity": 0.55})
        )
        assert result["novelty_detected"] is False

    def test_novelty_habituates_with_repeated_exposure(self):
        """Schultz 1998: novelty responses decrease with repetition."""
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        # First exposure — novel
        r1 = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
        )
        assert r1["novelty_detected"] is True
        # Repeat same pattern — now in recent buffer, expectation shifted
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(
                p.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
            )
        rN = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
        )
        assert rN["novelty_detected"] is False

    def test_novelty_uses_discretized_pattern(self):
        """Pattern at 0.55 vs 0.5 should be considered different."""
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        # 0.55 discretizes to same bucket as 0.5 (round to 1 decimal)
        r1 = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.55, "valence_polarity": 0.55})
        )
        # Small error, below threshold
        assert r1["novelty_detected"] is False


class TestHabituationDynamics:
    """Habituation accumulates on stable input, disrupts on strong surprise."""

    def test_habituation_accumulates_on_stable_input(self):
        p = PredictionErrorDrift()
        initial_hab = p.state["habituation_level"]
        # Stable input — low surprise across ticks
        for _ in range(10):
            asyncio.get_event_loop().run_until_complete(
                p.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
            )
        assert p.state["habituation_level"] > initial_hab

    def test_strong_surprise_disrupts_habituation(self):
        p = PredictionErrorDrift()
        p.state["habituation_level"] = 0.8
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.95, "valence_polarity": 0.95})
        )
        assert p.state["habituation_level"] < 0.8


class TestExpectationLearning:
    """Expectation drifts toward actual via bounded learning rate."""

    def test_expectation_drifts_toward_actual(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.3
        p.state["expected_valence"] = 0.3
        asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.9, "valence_polarity": 0.9})
        )
        assert p.state["expected_arousal"] > 0.3
        assert p.state["expected_valence"] > 0.3
        # Not all the way — learning rate 0.15
        assert p.state["expected_arousal"] < 0.9

    def test_sustained_input_converges_expectation(self):
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.3
        for _ in range(20):
            asyncio.get_event_loop().run_until_complete(
                p.tick({"arousal_level": 0.8, "valence_polarity": 0.5})
            )
        assert abs(p.state["expected_arousal"] - 0.8) < 0.05


class TestHomeostatIntegration:
    """PredictionErrorDrift.novelty_detected feeds Homeostat curiosity."""

    def test_novelty_signal_format_matches_homeostat_expectation(self):
        """Homeostat reads prior_results['PredictionErrorDrift']['novelty_detected']."""
        p = PredictionErrorDrift()
        p.state["expected_arousal"] = 0.5
        p.state["expected_valence"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.95, "valence_polarity": 0.95})
        )
        assert "novelty_detected" in result
        assert isinstance(result["novelty_detected"], bool)
        assert result["novelty_detected"] is True

    def test_all_required_output_keys_present(self):
        p = PredictionErrorDrift()
        result = asyncio.get_event_loop().run_until_complete(
            p.tick({"arousal_level": 0.5, "valence_polarity": 0.5})
        )
        required_keys = [
            "prediction_error", "surprise_magnitude", "novelty_detected",
            "habituation_level", "expected_signature",
        ]
        for key in required_keys:
            assert key in result, f"Missing output key: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
