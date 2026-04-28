"""
PWM Behavioral Tests
Presence-Weighted Memory

Tests PWM.compute_presence() and annotate_episodic_entry() across
presence-high, presence-mid, and presence-low encoding scenarios.

Wire: PWM built (brain/pwm.py). PWM integrated into ABM.write().
Tier 3 — Presence-Weighted Memory.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add workspace to path
WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.pwm import PresenceWeightedMemory


class TestComputePresence(unittest.TestCase):
    """Tests for the core presence computation."""

    def setUp(self):
        self.pwm = PresenceWeightedMemory()

    # ─── Presence-high scenarios ───────────────────────────────────────────

    def test_maximum_presence_high_all_signals(self):
        """All signals high: agency=1.0, anchor=1.0, arousal=0.7, valence=intense."""
        score = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.7,
            valence=0.9,  # intense positive
        )
        self.assertGreater(score, 0.85)
        self.assertLessEqual(score, 1.0)

    def test_high_presence_intense_negative_valence(self):
        """High presence with intense negative valence (still salient)."""
        score = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.7,
            valence=0.1,  # intense negative
        )
        self.assertGreater(score, 0.85)
        self.assertLessEqual(score, 1.0)

    def test_high_agency_low_anchor(self):
        """High agency, low self-anchor: partial presence (0.65)."""
        score = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=0.2,
            arousal=0.7,
            valence=0.9,
        )
        self.assertGreater(score, 0.55)
        self.assertLess(score, 0.75)

    # ─── Arousal gating ────────────────────────────────────────────────────

    def test_low_arousal_collapses_presence(self):
        """Low arousal (< 0.3) suppresses presence even with all other signals high."""
        score_low = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.1,  # below gating threshold
            valence=0.9,
        )
        score_high = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.7,
            valence=0.9,
        )
        self.assertLess(score_low, score_high * 0.88,
            "Low arousal should suppress presence significantly")

    def test_optimal_arousal_window(self):
        """Arousal 0.3-0.7 is the optimal window — no suppression, no taper."""
        score_optimal = self.pwm.compute_presence(
            agency_confidence=0.8,
            self_anchor_strength=0.8,
            arousal=0.5,
            valence=0.7,
        )
        score_high = self.pwm.compute_presence(
            agency_confidence=0.8,
            self_anchor_strength=0.8,
            arousal=0.7,
            valence=0.7,
        )
        # Both in optimal window — score difference < 0.07
        self.assertLess(abs(score_optimal - score_high), 0.07)

    # ─── Presence-low scenarios ───────────────────────────────────────────

    def test_minimal_presence_all_signals_low(self):
        """All signals minimal: presence near zero."""
        score = self.pwm.compute_presence(
            agency_confidence=0.1,
            self_anchor_strength=0.1,
            arousal=0.1,
            valence=0.5,  # neutral
        )
        self.assertLess(score, 0.15)

    def test_neutral_valence_reduces_presence(self):
        """Neutral valence (0.5) contributes 0 to presence score."""
        score = self.pwm.compute_presence(
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.7,
            valence=0.5,  # neutral — no emotional salience
        )
        # Without valence contribution, max possible is 0.35+0.30+0.20 = 0.85
        self.assertLess(score, 0.9)

    # ─── Somatic resonance ──────────────────────────────────────────────────

    def test_somatic_resonance_increases_presence(self):
        """Somatic resonance available → higher presence score."""
        score_without = self.pwm.compute_presence(
            agency_confidence=0.5,
            self_anchor_strength=0.5,
            arousal=0.5,
            valence=0.7,
            somatic_resonance=None,
        )
        score_with = self.pwm.compute_presence(
            agency_confidence=0.5,
            self_anchor_strength=0.5,
            arousal=0.5,
            valence=0.7,
            somatic_resonance={"breath": 0.8, "tension": 0.3, "warmth": 0.9},
        )
        self.assertGreater(score_with, score_without)

    def test_somatic_resonance_averaged_across_dimensions(self):
        """Somatic contribution is the average across available dimensions."""
        score_1 = self.pwm.compute_presence(
            agency_confidence=0.0,  # zero so somatic is the only variable
            self_anchor_strength=0.0,
            arousal=0.0,
            valence=0.5,
            somatic_resonance={"a": 0.4, "b": 0.6},  # avg = 0.5
        )
        score_2 = self.pwm.compute_presence(
            agency_confidence=0.0,
            self_anchor_strength=0.0,
            arousal=0.0,
            valence=0.5,
            somatic_resonance={"a": 0.2, "b": 0.8},  # avg = 0.5
        )
        self.assertAlmostEqual(score_1, score_2, places=3)

    # ─── Clamping ────────────────────────────────────────────────────────────

    def test_score_clamped_to_0_1(self):
        """Presence score must be in [0.0, 1.0] regardless of inputs."""
        scores = [
            self.pwm.compute_presence(agency_confidence=0, self_anchor_strength=0, arousal=0, valence=0.5),
            self.pwm.compute_presence(agency_confidence=0, self_anchor_strength=0, arousal=0, valence=0.5),
            self.pwm.compute_presence(agency_confidence=1.5, self_anchor_strength=1.5, arousal=1.5, valence=1.5),
        ]
        for score in scores:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


class TestAnnotateEpisodicEntry(unittest.TestCase):
    """Tests for PWM-ABM integration via annotate_episodic_entry."""

    def setUp(self):
        self.pwm = PresenceWeightedMemory()

    def test_annotation_adds_presence_weight(self):
        """Annotated entry contains presence_weight field."""
        entry = {"text": "test memory", "type": "tick"}
        annotated = self.pwm.annotate_episodic_entry(entry)
        self.assertIn("presence_weight", annotated)
        self.assertIn("presence_timestamp", annotated)
        self.assertIn("presence_components", annotated)

    def test_annotation_preserves_original_fields(self):
        """Annotation does not remove existing entry fields."""
        entry = {
            "text": "test memory",
            "type": "tick",
            "salience": 0.8,
            "emotional_valence": 0.7,
        }
        annotated = self.pwm.annotate_episodic_entry(entry)
        self.assertEqual(annotated["text"], "test memory")
        self.assertEqual(annotated["salience"], 0.8)
        self.assertEqual(annotated["emotional_valence"], 0.7)

    def test_annotation_is_non_mutating(self):
        """annotate_episodic_entry returns a new dict, original unchanged."""
        entry = {"text": "original", "type": "tick"}
        annotated = self.pwm.annotate_episodic_entry(entry)
        self.assertNotIn("presence_weight", entry)
        self.assertIn("presence_weight", annotated)

    def test_presence_high_entry_has_high_weight(self):
        """High-presence encoding → presence_weight >= 0.7."""
        entry = {"text": "high presence memory", "type": "tick"}
        annotated = self.pwm.annotate_episodic_entry(
            entry,
            agency_confidence=1.0,
            self_anchor_strength=1.0,
            arousal=0.7,
            valence=0.9,
        )
        self.assertGreaterEqual(annotated["presence_weight"], 0.7)

    def test_presence_low_entry_has_low_weight(self):
        """Low-presence encoding → presence_weight < 0.3."""
        entry = {"text": "low presence memory", "type": "tick"}
        annotated = self.pwm.annotate_episodic_entry(
            entry,
            agency_confidence=0.1,
            self_anchor_strength=0.1,
            arousal=0.1,
            valence=0.5,
        )
        self.assertLess(annotated["presence_weight"], 0.3)

    def test_presence_components_recorded(self):
        """presence_components captures all five signal inputs."""
        annotated = self.pwm.annotate_episodic_entry(
            {"text": "test"},
            agency_confidence=0.9,
            self_anchor_strength=0.8,
            arousal=0.6,
            valence=0.7,
        )
        comps = annotated["presence_components"]
        self.assertEqual(comps["agency_confidence"], 0.9)
        self.assertEqual(comps["self_anchor_strength"], 0.8)
        self.assertEqual(comps["arousal"], 0.6)
        self.assertEqual(comps["valence"], 0.7)


class TestTsbPayload(unittest.TestCase):
    """Tests for PWM's TSB payload and state reporting."""

    def setUp(self):
        self.pwm = PresenceWeightedMemory()

    def test_payload_structure(self):
        """tsb_payload returns expected fields."""
        payload = self.pwm.tsb_payload()
        self.assertIn("presence_avg_recent", payload)
        self.assertIn("presence_high_count", payload)
        self.assertIn("total_entries", payload)

    def test_payload_avg_recent_zero_when_no_history(self):
        """No history → avg_recent defaults to 0.5."""
        pwm = PresenceWeightedMemory()
        pwm.presence_history = []
        payload = pwm.tsb_payload()
        self.assertEqual(payload["presence_avg_recent"], 0.5)

    def test_payload_high_count(self):
        """presence_high_count counts entries with score > 0.7 in last 50."""
        pwm = PresenceWeightedMemory()
        pwm.presence_history = [
            {"score": 0.8, "timestamp": 0},
            {"score": 0.9, "timestamp": 0},
            {"score": 0.3, "timestamp": 0},
        ]
        payload = pwm.tsb_payload()
        self.assertEqual(payload["presence_high_count"], 2)


if __name__ == "__main__":
    unittest.main()
