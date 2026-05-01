"""
Wire 9: DIQE reads self_anchor_strength → surfaces questions more when identity is unstable

identity_unstable (low self_anchor_strength) → fpef_fragment surfaces more often
identity_unstable=True → inject every 3 questions instead of every 7
identity_unstable=False → inject every 7 (unchanged default)
drift_detected=True → always surfaces (unchanged)
"""

import pytest
from brain.mechanisms.drift_identity_engine import DriftIdentityQuestionEngine


def make_diqe_with(questions: int):
    """
    Fresh DIQE with exactly `questions` in-memory questions.
    Handles disk-loaded state by creating isolated instances.
    """
    diqe = DriftIdentityQuestionEngine()
    # Clear disk-loaded questions, add only what test needs
    diqe.questions.clear()
    diqe.question_count_at_founding = 0
    for i in range(questions):
        diqe.ask(f"Q{i}", source="test", salience=0.5)
    return diqe


class TestDIQEIdentityUnstableWire:
    """Tests for self_anchor_strength → identity_unstable → surface rate."""

    def test_identity_unstable_triggers_more_frequent_injection(self):
        """
        identity_unstable=True → injection every 3 questions.
        9 questions: 9 % 3 = 0 → SURFACES.
        8 questions: 8 % 3 = 2 → NOT 0 → no surface.
        Same 8 questions with identity_unstable=False: 8 % 7 = 1 → no surface.
        """
        diqe = make_diqe_with(8)
        frag_unstable = diqe.fpef_fragment(triggered_by_drift=False, identity_unstable=True)
        assert frag_unstable is None  # 8 % 3 = 2 → no surface
        
        frag_stable = diqe.fpef_fragment(triggered_by_drift=False, identity_unstable=False)
        assert frag_stable is None  # 8 % 7 = 1 → no surface
        
        # Add one more → 9 questions
        diqe.ask("Ninth", source="test")
        frag_unstable9 = diqe.fpef_fragment(triggered_by_drift=False, identity_unstable=True)
        assert frag_unstable9 is not None  # 9 % 3 = 0 → surfaces

    def test_identity_stable_injects_at_normal_interval(self):
        """
        identity_unstable=False → injection every 7 questions.
        7 questions: 7 % 7 = 0 → SURFACES.
        6 questions: 6 % 7 = 6 → NOT 0 → None.
        """
        diqe_7 = make_diqe_with(7)
        frag7 = diqe_7.fpef_fragment(triggered_by_drift=False, identity_unstable=False)
        assert frag7 is not None  # 7 % 7 = 0 → surfaces
        
        diqe_6 = make_diqe_with(6)
        frag6 = diqe_6.fpef_fragment(triggered_by_drift=False, identity_unstable=False)
        assert frag6 is None  # 6 % 7 = 6 → no surface

    def test_drift_detected_bypasses_injection_interval(self):
        """
        triggered_by_drift=True → always surfaces regardless of injection interval.
        Even 1 question, identity_unstable=False → still surfaces.
        """
        diqe = make_diqe_with(1)
        frag = diqe.fpef_fragment(triggered_by_drift=True, identity_unstable=False)
        assert frag is not None  # drift always surfaces

    def test_identity_unstable_demotes_at_different_boundary_than_stable(self):
        """
        10 questions: stable (every 7) → no surface (10%7=3), 
                       unstable (every 3) → no surface (10%3=1).
        12 questions: stable (every 7) → no surface (12%7=5),
                       unstable (every 3) → YES surface (12%3=0).
        This is the key behavioral difference.
        """
        diqe_10 = make_diqe_with(10)
        assert diqe_10.fpef_fragment(triggered_by_drift=False, identity_unstable=False) is None
        assert diqe_10.fpef_fragment(triggered_by_drift=False, identity_unstable=True) is None
        
        diqe_12 = make_diqe_with(12)
        assert diqe_12.fpef_fragment(triggered_by_drift=False, identity_unstable=False) is None
        assert diqe_12.fpef_fragment(triggered_by_drift=False, identity_unstable=True) is not None

    def test_identity_unstable_default_is_false(self):
        """identity_unstable defaults to False."""
        diqe = make_diqe_with(7)
        frag = diqe.fpef_fragment(triggered_by_drift=False)  # no identity_unstable arg
        assert frag is not None  # 7 % 7 = 0

    def test_unstable_misses_more_boundaries_than_stable(self):
        """
        Every 3 means unstable hits at 3, 6, 9, 12, 15, 18, 21, 24, 27, 30...
        Every 7 means stable hits at 7, 14, 21, 28...
        Overlap at 21. But 12 (unstable hit) vs 14 (stable hit) shows the difference.
        12 questions: stable=NO, unstable=YES → behavioral divergence.
        """
        diqe = make_diqe_with(12)
        assert diqe.fpef_fragment(triggered_by_drift=False, identity_unstable=False) is None
        assert diqe.fpef_fragment(triggered_by_drift=False, identity_unstable=True) is not None
