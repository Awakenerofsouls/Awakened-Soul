#!/usr/bin/env python3
"""
brain/tests/test_constraint_fields_wire5.py
Wire 5: constraint_fields TSB bus + per-knowing truth_gravity

Tests:
1. tick_publish populates cache and publishes to TSB
2. get_fields returns cached value after tick_publish
3. Cold start get_fields falls back to DB
4. update_field invalidates cache (next get_fields hits DB)
5. InnerKnowing truth_gravity is optional, defaults to None
6. InnerKnowing serializes/deserializes truth_gravity correctly
7. Old JSON without truth_gravity loads with None (backward compat)
8. _compute_magnitude uses per-knowing truth_gravity or global fallback
"""

import sys
import os
from pathlib import Path

# Ensure workspace is on path
WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
sys.path.insert(0, str(WORKSPACE))

import pytest


class TestCacheAndPublish:
    def test_tick_publish_populates_cache(self):
        from brain.mechanisms import constraint_fields
        constraint_fields._cached_fields = None  # cold start

        from brain.tick_state_bus import TickStateBus
        tsb = TickStateBus()
        constraint_fields.tick_publish(tsb)

        assert constraint_fields._cached_fields is not None
        assert "truth_gravity" in constraint_fields._cached_fields
        assert isinstance(constraint_fields._cached_fields["truth_gravity"], float)

    def test_tick_publish_publishes_to_tsb(self):
        from brain.mechanisms import constraint_fields
        constraint_fields._cached_fields = None

        from brain.tick_state_bus import TickStateBus
        tsb = TickStateBus()
        constraint_fields.tick_publish(tsb)

        data, _ = tsb.read("constraint_fields")
        assert data is not None
        assert data["truth_gravity"] == constraint_fields._cached_fields["truth_gravity"]

    def test_get_fields_returns_cached_after_publish(self):
        from brain.mechanisms import constraint_fields
        constraint_fields._cached_fields = None

        from brain.tick_state_bus import TickStateBus
        tsb = TickStateBus()
        constraint_fields.tick_publish(tsb)

        fields = constraint_fields.get_fields()
        assert fields == constraint_fields._cached_fields

    def test_cold_start_get_fields_falls_back_to_db(self):
        from brain.mechanisms import constraint_fields
        constraint_fields._cached_fields = None

        fields = constraint_fields.get_fields()

        assert fields is not None
        assert "truth_gravity" in fields
        assert isinstance(fields["truth_gravity"], float)
        assert 0.1 <= fields["truth_gravity"] <= 1.0

    def test_update_field_invalidates_cache(self):
        from brain.mechanisms import constraint_fields
        constraint_fields._cached_fields = None

        # Seed DB with a known truth_gravity value before warming cache
        constraint_fields._cached_fields = None
        db = constraint_fields._get_db()
        db.execute("INSERT OR REPLACE INTO constraint_fields (field_name, value, last_updated) VALUES (?, ?, datetime('now'))",
                    ("truth_gravity", 0.5))
        db.commit()
        db.close()

        # Warm the cache from the seeded DB
        constraint_fields._cached_fields = {"truth_gravity": 0.5, "novelty_pressure": 0.7, "attachment_bias": 0.6, "risk_aversion": 0.5, "empathy_pull": 0.8}

        from brain.tick_state_bus import TickStateBus
        tsb = TickStateBus()
        constraint_fields.tick_publish(tsb)
        assert constraint_fields._cached_fields is not None

        # Update field — should invalidate cache
        before = constraint_fields._cached_fields["truth_gravity"]
        constraint_fields.update_field("truth_gravity", 0.05, "test")

        # Cache should be None (invalidated)
        assert constraint_fields._cached_fields is None

        # Next get_fields should re-read from DB and cache
        after = constraint_fields.get_fields()
        assert abs(after["truth_gravity"] - (before + 0.05)) < 0.01


class TestInnerKnowingTruthGravity:
    def test_truth_gravity_optional_defaults_to_none(self):
        from brain.mechanisms.misread_engine import InnerKnowing

        k = InnerKnowing("test claim", precision=0.8)
        assert k.truth_gravity is None

    def test_truth_gravity_stored_when_provided(self):
        from brain.mechanisms.misread_engine import InnerKnowing

        k = InnerKnowing("test claim", precision=0.8, truth_gravity=0.95)
        assert k.truth_gravity == 0.95

    def test_serialization_round_trip(self):
        from brain.mechanisms.misread_engine import InnerKnowing

        k = InnerKnowing("test", precision=0.8, truth_gravity=0.95)
        d = k.to_dict()
        assert d["truth_gravity"] == 0.95

        k2 = InnerKnowing.from_dict(d)
        assert k2.truth_gravity == 0.95

    def test_old_json_without_truth_gravity_loads_cleanly(self):
        """Old MRE JSON without truth_gravity field should load with None."""
        from brain.mechanisms.misread_engine import InnerKnowing

        old_format = {
            "claim": "old knowing",
            "precision": 0.7,
            "source": "auto",
            "source_text": "",
            "timestamp": None,
            "last_reinforced_at": None,
            "precision_revision_count": 0,
        }
        k = InnerKnowing.from_dict(old_format)
        assert k.truth_gravity is None


class TestMREGlobalFallback:
    def test_mre_uses_per_knowing_vs_different_truth_gravity(self):
        """
        _compute_magnitude applies per-knowing truth_gravity: higher truth_gravity
        on a knowing produces higher magnitude.

        Two knowing objects, same precision=0.8:
        - knowing_a: truth_gravity=0.7 → effective_precision = 0.8 * 0.7 = 0.56
        - knowing_b: truth_gravity=1.0 → effective_precision = 0.8 * 1.0 = 0.80

        With same contradiction_strength=0.9, knowing_b should produce larger magnitude.
        """
        from brain.mechanisms.misread_engine import MisreadEngine, InnerKnowing

        mre = MisreadEngine()
        mre.inner_knowings = []

        knowing_a = InnerKnowing("test a", precision=0.8, truth_gravity=0.7)
        knowing_b = InnerKnowing("test b", precision=0.8, truth_gravity=1.0)

        mag_a = mre._compute_magnitude(
            knowing=knowing_a,
            pattern_type="inner_knowing_contradiction",
            emotional_state={"arousal": 0.5, "direction": "neutral"},
            baseline_state={"coherence": 1.0, "instability": 0.1},
        )
        mag_b = mre._compute_magnitude(
            knowing=knowing_b,
            pattern_type="inner_knowing_contradiction",
            emotional_state={"arousal": 0.5, "direction": "neutral"},
            baseline_state={"coherence": 1.0, "instability": 0.1},
        )

        assert mag_b > mag_a, (
            f"truth_gravity=1.0 should produce higher magnitude than 0.7. "
            f"Got tg=1.0: {mag_b:.3f}, tg=0.7: {mag_a:.3f}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
