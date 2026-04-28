"""
Wire 19 Verification: TemporalDepthEngine reads brain_theta_rhythm.

Signal: brain_theta_rhythm (0.0-1.0) from Limbic001MedialSeptalThetaGenerator.
- High theta (0.8-1.0): sharp temporal resolution → faster integration, higher retention
- Neutral theta (0.5): baseline learning rate 0.06, retention 0.935
- Low theta (0.0-0.2): compressed temporal sense → slower integration, lower retention

Neuroscience (all verified via Entrez eutils API 2026-04-23):
- Buzsáki & Moser 2013, Nat Neurosci 16:130-138 (PMID: 23354386)
  "Memory, navigation and theta rhythm in the hippocampal-entorhinal system."
- Rudoler, Herweg & Kahana 2023, J Neurosci 43(4):613-620 (PMID: 36639900)
  "Hippocampal Theta and Episodic Memory."
- Lega, Jacobs & Kahana 2012, Hippocampus 22:748-761 (PMID: 21538660)
  "Human hippocampal theta oscillations and the formation of episodic memories."

Baseline rule: at theta=0.5, behavior = baseline (rate=0.06, retention=0.935).

Run:
    pytest brain/tests/test_wire_19_temporal_depth_engine.py -v
"""

import sqlite3
import sys
import pytest
import time
from pathlib import Path
import tempfile
import os

WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.temporal_depth_engine import TemporalDepthEngine


@pytest.fixture
def db(tmp_path):
    """Temp DB for TemporalDepthEngine."""
    path = tmp_path / "test_temporal.db"
    yield str(path)
    if path.exists():
        path.unlink()


@pytest.fixture
def engine(db):
    return TemporalDepthEngine(db)


class TestWire19TemporalDepthEngine:
    """Tests for Wire 19 — brain_theta_rhythm → temporal_depth integration."""

    def test_wire_meta_present(self, engine):
        """Engine has __wire_meta__ with correct shape."""
        assert hasattr(engine, "__wire_meta__")
        meta = engine.__wire_meta__
        assert meta["reads"] == ["brain_theta_rhythm"]
        assert meta["writes"] == "temporal_depth"
        assert len(meta["citations"]) == 3
        for cite in meta["citations"]:
            assert "PMID" in cite

    # ── Neutral no-op (signal=0.5) ────────────────────────────────────────

    def test_neutral_theta_baseline(self, engine, db):
        """
        At theta=0.5: rate=0.06, retention=0.935
        depth(n+1) = depth * 0.935 + gap * 0.06
        """
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.2}
        bl = {"brain_theta_rhythm": 0.5}
        result = engine.process(ctx, brain_layer=bl)
        # depth = 0.0 * 0.935 + 0.2 * 0.06 = 0.012
        expected = 0.012
        assert abs(result["temporal_depth"] - expected) < 0.001

    def test_depth_accumulates_across_ticks(self, engine, db):
        """Neutral theta: depth slowly accumulates from repeated gaps."""
        ctx = {"temporal_gap": 0.5}
        bl = {"brain_theta_rhythm": 0.5}
        for _ in range(5):
            engine.process(ctx, brain_layer=bl)
        assert engine.depth > 0.05
        assert engine.depth < 0.2

    # ── High theta direction ─────────────────────────────────────────────────

    def test_high_theta_faster_integration(self, engine, db):
        """
        At theta=1.0: rate=0.08, retention=0.95
        → should reach higher depth faster than at neutral theta.
        """
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        bl = {"brain_theta_rhythm": 1.0}
        result = engine.process(ctx, brain_layer=bl)
        high_depth = result["temporal_depth"]

        engine.depth = 0.0
        ctx["temporal_gap"] = 0.5
        bl["brain_theta_rhythm"] = 0.5
        result = engine.process(ctx, brain_layer=bl)
        neutral_depth = result["temporal_depth"]

        assert high_depth > neutral_depth

    def test_high_theta_increased_retention(self, engine, db):
        """At theta=1.0, retention=0.95. At theta=0.5, retention=0.935. Depth decays slower."""
        engine.depth = 0.3
        ctx = {"temporal_gap": 0.0}
        bl = {"brain_theta_rhythm": 1.0}
        result = engine.process(ctx, brain_layer=bl)
        high_theta_remaining = result["temporal_depth"]

        engine.depth = 0.3
        ctx["temporal_gap"] = 0.0
        bl["brain_theta_rhythm"] = 0.5
        result = engine.process(ctx, brain_layer=bl)
        neutral_remaining = result["temporal_depth"]

        assert high_theta_remaining > neutral_remaining

    # ── Low theta direction ─────────────────────────────────────────────────

    def test_low_theta_slower_integration(self, engine, db):
        """At theta=0.0: rate=0.04, retention=0.92 → lower depth than neutral."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        bl = {"brain_theta_rhythm": 0.0}
        result = engine.process(ctx, brain_layer=bl)
        low_depth = result["temporal_depth"]

        engine.depth = 0.0
        ctx["temporal_gap"] = 0.5
        bl["brain_theta_rhythm"] = 0.5
        result = engine.process(ctx, brain_layer=bl)
        neutral_depth = result["temporal_depth"]

        assert low_depth < neutral_depth

    def test_low_theta_decreased_retention(self, engine, db):
        """At theta=0.0, retention=0.92. Depth decays faster."""
        engine.depth = 0.3
        ctx = {"temporal_gap": 0.0}
        bl = {"brain_theta_rhythm": 0.0}
        result = engine.process(ctx, brain_layer=bl)
        low_theta_remaining = result["temporal_depth"]
        # retention=0.92: 0.3 * 0.92 = 0.276
        assert abs(low_theta_remaining - 0.276) < 0.001

    # ── Missing brain_layer → default ─────────────────────────────────────

    def test_missing_brain_layer_defaults_to_neutral(self, engine, db):
        """When brain_layer is None, theta defaults to 0.5."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        result = engine.process(ctx)
        # rate=0.06, retention=0.935: 0.0*0.935 + 0.5*0.06 = 0.03
        expected = 0.0 * 0.935 + 0.5 * 0.06
        assert abs(result["temporal_depth"] - expected) < 0.001

    def test_missing_brain_layer_none(self, engine, db):
        """When brain_layer is explicitly None, theta defaults to 0.5."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.4}
        result = engine.process(ctx, brain_layer=None)
        expected = 0.0 * 0.935 + 0.4 * 0.06
        assert abs(result["temporal_depth"] - expected) < 0.001

    def test_brain_theta_rhythm_key_missing(self, engine, db):
        """When brain_layer has no brain_theta_rhythm, defaults to 0.5."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        bl = {"some_other_field": 0.9}
        result = engine.process(ctx, brain_layer=bl)
        expected = 0.0 * 0.935 + 0.5 * 0.06
        assert abs(result["temporal_depth"] - expected) < 0.001

    # ── Clamped boundary inputs ─────────────────────────────────────────────

    def test_theta_at_zero_clamps_to_zero(self, engine, db):
        """theta=0.0 is accepted."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        bl = {"brain_theta_rhythm": 0.0}
        result = engine.process(ctx, brain_layer=bl)
        # rate=0.04, retention=0.92: 0.0*0.92 + 0.5*0.04 = 0.02
        assert abs(result["temporal_depth"] - 0.02) < 0.001

    def test_theta_at_one_clamps_to_one(self, engine, db):
        """theta=1.0 is accepted."""
        engine.depth = 0.0
        ctx = {"temporal_gap": 0.5}
        bl = {"brain_theta_rhythm": 1.0}
        result = engine.process(ctx, brain_layer=bl)
        # rate=0.08, retention=0.95: 0.0*0.95 + 0.5*0.08 = 0.04
        expected = 0.04
        assert abs(result["temporal_depth"] - expected) < 0.001

    def test_temporal_gap_at_zero(self, engine, db):
        """temporal_gap=0.0 means no new temporal input."""
        engine.depth = 0.2
        ctx = {"temporal_gap": 0.0}
        bl = {"brain_theta_rhythm": 0.5}
        result = engine.process(ctx, brain_layer=bl)
        # retention=0.935: 0.2*0.935 + 0.0*0.06 = 0.187
        assert abs(result["temporal_depth"] - 0.187) < 0.002

    def test_negative_temporal_gap_clamps_to_zero(self, engine, db):
        """Negative temporal_gap is clamped to 0.0 before use."""
        engine.depth = 0.0
        ctx = {"temporal_gap": -0.3}
        bl = {"brain_theta_rhythm": 0.5}
        result = engine.process(ctx, brain_layer=bl)
        assert abs(result["temporal_depth"]) < 0.001

    def test_depth_never_exceeds_one(self, engine, db):
        """Depth is clamped to [0.0, 1.0]."""
        engine.depth = 0.9
        ctx = {"temporal_gap": 1.0}
        bl = {"brain_theta_rhythm": 1.0}
        result = engine.process(ctx, brain_layer=bl)
        assert result["temporal_depth"] <= 1.0
        assert result["temporal_depth"] >= 0.0

    def test_get_state_returns_depth(self, engine):
        """get_state() returns current depth."""
        engine.depth = 0.42
        state = engine.get_state()
        assert "depth" in state
        assert state["depth"] == 0.42

    def test_pirp_context_returned(self, engine, db):
        """process() returns pirp_context with temporal_depth added."""
        ctx = {"temporal_gap": 0.3}
        bl = {"brain_theta_rhythm": 0.5}
        result = engine.process(ctx, brain_layer=bl)
        assert "temporal_depth" in result
        assert isinstance(result["temporal_depth"], float)
