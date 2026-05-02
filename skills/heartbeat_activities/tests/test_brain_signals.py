"""
Tests for brain_signals.py — signal reading, temperature computation, softmax pick.

Runs without real brain state files (mocked). Tests cover:
- read_brain_signals: no config, missing file, malformed JSON, valid read, path/key normalization
- Key path traversal: 'foo', 'foo.bar', 'foo.bar[-1]', 'foo[0].bar', 'foo[0]'
- Normalizers: passthrough, zero_to_hundred, neg_one_to_one, clamping
- compute_temperature: arousal 0.0/0.5/1.0, custom range, missing signal
- softmax_pick: empty candidates, no signals (→ weighted random), high-affinity bias,
  negative affinity suppression, numerical stability, equal weights
- Integration: full dispatch path with mocked signal files
"""

import json
import math
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import sys
# heartbeat_activities lives under skills/ — add workspace root (~/.agent/workspace)
# so 'from heartbeat_activities import ...' resolves correctly.
for p in [Path(__file__).parent.parent.parent,  # skills/
           Path(__file__).parent.parent.parent.parent]:  # workspace/
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from heartbeat_activities import brain_signals
from heartbeat_activities.dispatcher import softmax_pick


# ─── Helpers ───────────────────────────────────────────────────────────────────

def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data))


class TestReadBrainSignals(unittest.TestCase):
    """read_brain_signals: config-driven signal file reading."""

    def test_no_config_returns_empty_dict(self):
        """No BRAIN_SIGNAL_FILES in state → returns {}."""
        result = brain_signals.read_brain_signals({})
        self.assertEqual(result, {})

    def test_missing_file_returns_neutral_05(self):
        """Unreadable signal file → returns neutral 0.5 for that signal."""
        state = {
            "BRAIN_SIGNAL_FILES": [
                {"name": "conflict", "path": "/tmp/does_not_exist.json",
                 "key": "value", "normalizer": "passthrough"}
            ]
        }
        # Should not raise — logs warning internally
        result = brain_signals.read_brain_signals(state)
        self.assertEqual(result, {"conflict": 0.5})

    def test_malformed_json_returns_neutral_05(self):
        """Bad JSON → returns neutral 0.5 for that signal."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json{")
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "pe", "path": path, "key": "foo", "normalizer": "passthrough"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertEqual(result, {"pe": 0.5})
        finally:
            Path(path).unlink(missing_ok=True)

    def test_valid_read_passthrough(self):
        """Valid JSON with passthrough normalizer reads the value as-is, clamped to [0,1]."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"value": 0.73}, f)
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "my_signal", "path": path, "key": "value", "normalizer": "passthrough"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertAlmostEqual(result["my_signal"], 0.73)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_valid_read_zero_to_hundred(self):
        """zero_to_hundred normalizer divides by 100."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"level": 73}, f)
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "signal", "path": path, "key": "level", "normalizer": "zero_to_hundred"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertAlmostEqual(result["signal"], 0.73)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_valid_read_neg_one_to_one(self):
        """neg_one_to_one normalizer maps [-1,1] → [0,1]."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"arousal": -0.4}, f)
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "signal", "path": path, "key": "arousal", "normalizer": "neg_one_to_one"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertAlmostEqual(result["signal"], 0.3)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_clamp_at_upper_bound(self):
        """Value > 1.0 is clamped to 1.0."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"val": 1.5}, f)
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "s", "path": path, "key": "val", "normalizer": "passthrough"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertEqual(result["s"], 1.0)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_clamp_at_lower_bound(self):
        """Negative value is clamped to 0.0."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"val": -0.3}, f)
            path = f.name
        try:
            state = {
                "BRAIN_SIGNAL_FILES": [
                    {"name": "s", "path": path, "key": "val", "normalizer": "passthrough"}
                ]
            }
            result = brain_signals.read_brain_signals(state)
            self.assertEqual(result["s"], 0.0)
        finally:
            Path(path).unlink(missing_ok=True)


class TestKeyPathTraversal(unittest.TestCase):
    """_read_key: JSON path traversal with dot notation and array indices."""

    def _read(self, data, key):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            path = f.name
        try:
            return brain_signals._read_key(path, key)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_simple_key(self):
        self.assertEqual(self._read({"foo": 0.8}, "foo"), 0.8)

    def test_nested_key(self):
        self.assertEqual(self._read({"a": {"b": 0.6}}, "a.b"), 0.6)

    def test_nested_key_deep(self):
        self.assertEqual(self._read({"a": {"b": {"c": 0.4}}}, "a.b.c"), 0.4)

    def test_array_index(self):
        self.assertEqual(self._read({"arr": [10, 20, 30]}, "arr[1]"), 20)

    def test_nested_with_array(self):
        self.assertEqual(self._read({"a": [{"x": 0.1}, {"x": 0.2}]}, "a[1].x"), 0.2)

    def test_last_element(self):
        self.assertEqual(self._read({"trend": [0.1, 0.3, 0.7, 0.9]}, "trend[-1]"), 0.9)

    def test_missing_key_returns_none(self):
        result = self._read({"foo": 1}, "bar")
        self.assertIsNone(result)

    def test_invalid_array_index_returns_none(self):
        result = self._read({"arr": [1, 2]}, "arr[99]")
        self.assertIsNone(result)


class TestComputeTemperature(unittest.TestCase):
    """compute_temperature: arousal → softmax temperature mapping."""

    def test_high_arousal_low_temp(self):
        """arousal=1.0 → temp=lo (decisive picks)."""
        temp = brain_signals.compute_temperature(
            {"arousal": 1.0}, "arousal", temp_range=(0.7, 2.0)
        )
        self.assertAlmostEqual(temp, 0.7)

    def test_low_arousal_high_temp(self):
        """arousal=0.0 → temp=hi (exploratory picks)."""
        temp = brain_signals.compute_temperature(
            {"arousal": 0.0}, "arousal", temp_range=(0.7, 2.0)
        )
        self.assertAlmostEqual(temp, 2.0)

    def test_mid_arousal_mid_temp(self):
        """arousal=0.5 → temp=midpoint."""
        temp = brain_signals.compute_temperature(
            {"arousal": 0.5}, "arousal", temp_range=(0.7, 2.0)
        )
        self.assertAlmostEqual(temp, 1.35)

    def test_missing_arousal_signal_uses_midpoint(self):
        """Missing signal → midpoint temperature."""
        temp = brain_signals.compute_temperature({}, "missing_signal", temp_range=(0.7, 2.0))
        self.assertAlmostEqual(temp, 1.35)

    def test_custom_range(self):
        """Custom range is respected."""
        temp = brain_signals.compute_temperature(
            {"a": 1.0}, "a", temp_range=(0.5, 3.0)
        )
        self.assertAlmostEqual(temp, 0.5)


class TestSoftmaxPick(unittest.TestCase):
    """softmax_pick: weighted-softmax activity selection."""

    def test_empty_candidates_returns_none(self):
        result = softmax_pick([], {}, 1.0, {})
        self.assertIsNone(result)

    def test_no_signals_reduces_to_weighted_random(self):
        """With no signals, distribution should reflect overdue-based weights."""
        candidates = ["a", "b", "c"]
        state = {"overdue_activities": {"a": 0, "b": 9, "c": 0}}
        # Run many times and check 'a' and 'c' are selected more than 'b'
        picks = [softmax_pick(candidates, {}, 1.0, state) for _ in range(5000)]
        # 'a' and 'c' have equal weight (1.0), 'b' has weight 0.1
        # So 'b' should appear ~5% of the time, 'a' and 'c' ~47.5% each
        b_count = picks.count("b")
        self.assertLess(b_count, 400, f"'b' appeared {b_count} times — too often for weighted random")

    def test_high_affinity_bias_picks_correct_activity(self):
        """High signal+affinity product → that activity dominates at low temperature."""
        candidates = ["a", "b"]
        signals = {"pe": 1.0}
        # 'a' has affinity 0.7 for 'pe', 'b' has 0.0
        state = {"overdue_activities": {}}
        with patch("heartbeat_activities.dispatcher.get_affinities",
                   return_value={"a": {"pe": 0.7}, "b": {}}):
            picks = [softmax_pick(candidates, signals, 0.3, state) for _ in range(200)]
        a_count = picks.count("a")
        self.assertGreater(a_count, 150, f"'a' only picked {a_count}/200 times at τ=0.3")

    def test_negative_affinity_suppresses(self):
        """Negative affinity for a signal should suppress that activity."""
        candidates = ["x", "y"]
        signals = {"conflict": 0.7}  # 0.7 × -0.7 = -0.49 bonus for x (scores: y=1.0, x≈0.51)
        state = {"overdue_activities": {}}
        # Low temperature — bias should be sharp
        with patch("heartbeat_activities.dispatcher.get_affinities",
                   return_value={"x": {"conflict": -0.7}, "y": {}}):
            picks = [softmax_pick(candidates, signals, 0.5, state) for _ in range(2000)]
        x_count = picks.count("x")
        y_count = picks.count("y")
        # At τ=0.5 with signal=0.7, y's probability ≈ 77% — should beat 2x x
        self.assertGreater(y_count, x_count * 2,
            f"y={y_count}, x={x_count} — negative affinity not suppressing 'x'")

        # Higher temperature — effect present but less decisive
        with patch("heartbeat_activities.dispatcher.get_affinities",
                   return_value={"x": {"conflict": -0.7}, "y": {}}):
            picks = [softmax_pick(candidates, signals, 1.0, state) for _ in range(500)]
        x_count = picks.count("x")
        y_count = picks.count("y")
        self.assertGreater(y_count, x_count,
            f"y={y_count}, x={x_count} — suppression not present at τ=1.0")

    def test_numerical_stability_extreme_scores(self):
        """Extreme scores (very negative) should not cause overflow."""
        candidates = ["a", "b"]
        signals = {"pe": 1.0, "conflict": 0.0}
        state = {"overdue_activities": {}}
        with patch("heartbeat_activities.dispatcher.get_affinities",
                   return_value={"a": {"pe": 10.0, "conflict": -10.0}, "b": {}}):
            # Should not raise
            result = softmax_pick(candidates, signals, 0.5, state)
        self.assertIn(result, candidates)

    def test_additive_signal_bonus(self):
        """Additive: activity matching two signals gets both bonuses."""
        candidates = ["multi", "single", "none"]
        signals = {"pe": 0.8, "conflict": 0.8}
        state = {"overdue_activities": {}}
        with patch("heartbeat_activities.dispatcher.get_affinities",
                   return_value={
                       "multi": {"pe": 0.5, "conflict": 0.5},   # bonus: 0.8*0.5 + 0.8*0.5 = 0.8
                       "single": {"pe": 0.5},                    # bonus: 0.8*0.5 = 0.4
                       "none": {}
                   }):
            picks = [softmax_pick(candidates, signals, 0.8, state) for _ in range(500)]
        multi_count = picks.count("multi")
        single_count = picks.count("single")
        # 'multi' should beat 'single' — higher combined bonus
        self.assertGreater(multi_count, single_count,
            f"multi={multi_count}, single={single_count} — additive bonus not stacking")


class TestDispatchIntegration(unittest.TestCase):
    """Full dispatch path with mocked signal files."""

    def test_dispatch_with_brain_signals_loaded(self):
        """Dispatcher dispatch() completes without error when brain signals configured."""
        from heartbeat_activities.dispatcher import dispatch, invalidate_affinity_cache

        # Write a fake brain state file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"dACC_signal_strength": 0.62}, f)
            conflict_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"salience_level": 0.48}, f)
            pe_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"cholinergic_tone": 0.55}, f)
            reset_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"tonic_level": 0.5}, f)
            osc_path = f.name

        try:
            state = {
                "tick_count": 10,
                "overdue_activities": {},
                "unfinished_threads": [],
                "WORKSPACE": str(Path(__file__).parent.parent),
                "BRAIN_SIGNAL_FILES": [
                    {"name": "conflict", "path": conflict_path, "key": "dACC_signal_strength", "normalizer": "passthrough"},
                    {"name": "prediction_error", "path": pe_path, "key": "salience_level", "normalizer": "passthrough"},
                    {"name": "affective_reset", "path": reset_path, "key": "cholinergic_tone", "normalizer": "passthrough"},
                    {"name": "oscillation_balance", "path": osc_path, "key": "tonic_level", "normalizer": "passthrough"},
                ],
                "AROUSAL_SIGNAL": "oscillation_balance",
                "TEMPERATURE_RANGE": [0.7, 2.0],
                "LLM_ENDPOINT": "http://localhost:11434",
                "LLM_MODEL": "qwen2.5vl:7b",
            }

            invalidate_affinity_cache()
            result = dispatch(state)

            # Should return a valid result dict
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("category", result)
        finally:
            Path(conflict_path).unlink(missing_ok=True)
            Path(pe_path).unlink(missing_ok=True)
            Path(reset_path).unlink(missing_ok=True)
            Path(osc_path).unlink(missing_ok=True)
            invalidate_affinity_cache()


if __name__ == "__main__":
    unittest.main()
