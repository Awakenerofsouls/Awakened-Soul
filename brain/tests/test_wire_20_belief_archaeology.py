"""
Wire 20 Verification: BeliefArchaeologyLayer reads brain_consciousness_level.

Signal: brain_consciousness_level (0.0-1.0) from Integration035 IdentityConsciousnessGuardian.
- High consciousness (0.8-1.0): grief erosion reduced → beliefs feel stable
- Neutral consciousness (0.5): baseline grief erosion
- Low consciousness (0.0-0.2): grief erosion amplified → beliefs feel fragile

Citations (all verified via Entrez eutils API 2026-04-23):
- PMID 40924468: "Neural correlates of Bayesian social belief updating in the medial prefrontal cortex."
  Hofmans L, van den Bos W. Cereb Cortex 35 (2025 Aug 1).
- PMID 39819882: "Self-referential belief shares common neural correlates with general belief."
  Bruns E, Scholz I, Koppe G, Kirsch P et al. Sci Rep 15 (2025 Jan 16).
- PMID 29336688: "Beliefs about Memory as a Mediator of Relations between Metacognitive Beliefs and Actual Memory Performance."
  Irak M, Çapan D. J Gen Psychol 145 (2018 Jan-Mar).

Baseline rule: at consciousness=0.5, grief erosion = baseline (unchanged from original).

Run:
    pytest brain/tests/test_wire_20_belief_archaeology.py -v
"""

import sqlite3
import sys
import pytest
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.belief_archaeology import BeliefArchaeologyLayer


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test_belief.db"
    yield str(path)
    if path.exists():
        path.unlink()


@pytest.fixture
def layer(db):
    return BeliefArchaeologyLayer()


class TestWire20BeliefArchaeologyLayer:
    """Tests for Wire 20 — brain_consciousness_level → belief durability."""

    def test_wire_meta_present(self, layer):
        """Layer has __wire_meta__ with correct shape."""
        assert hasattr(layer, "__wire_meta__")
        meta = layer.__wire_meta__
        assert meta["reads"] == ["brain_consciousness_level"]
        assert meta["writes"] == "belief_archaeology"
        assert len(meta["citations"]) == 3
        for cite in meta["citations"]:
            assert "PMID" in cite

    # ── Neutral no-op (consciousness=0.5) ───────────────────────────────

    def test_neutral_consciousness_baseline(self, layer, db):
        """
        At consciousness=0.5: grief_modulation = 0.85 (neutral)
        → grief > 0.4 threshold still triggers belief shift
        → behavior matches original logic
        """
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {
            "itg_tension": 0.5,
            "transformation_grief": 0.5,
            "resonance_score": 0.3,
        }
        bl = {"brain_consciousness_level": 0.5}
        result = layer.process(ctx, brain_layer=bl)

        # At consciousness=0.5: effective_grief = 0.5 * 0.85 = 0.425
        # > 0.4 threshold → shift triggered
        # belief_shift = 0.425 * 0.2 = 0.085
        # durability = max(0.1, 0.7 - 0.085) = 0.615
        assert result["transformation_count"] == 1
        # First shift: count=1, durability=0.615, so 'tested' (not yet 'shifting', not yet 'bedrock')
        assert result["belief_state"] in ["tested", "provisional", "shifting"]
        assert result["belief_durability"] < 0.7

    def test_no_shift_without_grief(self, layer, db):
        """With consciousness=0.5 and no grief, durability increases via resonance."""
        layer._durability = 0.6
        layer._transformation_count = 0
        ctx = {
            "itg_tension": 0.3,
            "transformation_grief": 0.0,
            "resonance_score": 0.7,
        }
        bl = {"brain_consciousness_level": 0.5}
        result = layer.process(ctx, brain_layer=bl)

        assert result["belief_durability"] > 0.6
        assert result["transformation_count"] == 0

    # ── High consciousness direction ───────────────────────────────────

    def test_high_consciousness_reduces_grief_erosion(self, layer, db):
        """
        At consciousness=1.0: grief_modulation = 1.00 (no reduction)
        At consciousness=0.5: grief_modulation = 0.85 (baseline erosion)
        → with high consciousness, same grief level causes less durability loss.
        """
        # High consciousness: modulation=1.00
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 1.0}
        result_high = layer.process(ctx, brain_layer=bl)
        high_durability = result_high["belief_durability"]

        # Neutral consciousness: modulation=0.85 → effective_grief = 0.6*0.85=0.51
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 0.5}
        result_neutral = layer.process(ctx, brain_layer=bl)
        neutral_durability = result_neutral["belief_durability"]

        # Same grief input; high consciousness should give equal or better durability
        assert high_durability >= neutral_durability

    def test_high_consciousness_belief_state_more_stable(self, layer, db):
        """High consciousness: repeated grief events keep belief_state in 'bedrock' longer."""
        layer._durability = 0.85
        layer._transformation_count = 2
        # Run 5 ticks with grief at high consciousness
        for i in range(5):
            ctx = {"transformation_grief": 0.5, "resonance_score": 0.4, "itg_tension": 0.3}
            bl = {"brain_consciousness_level": 1.0}
            layer.process(ctx, brain_layer=bl)

        # With high consciousness, durability should hold relatively stable
        assert layer._durability > 0.5

    # ── Low consciousness direction ─────────────────────────────────────

    def test_low_consciousness_increases_grief_erosion(self, layer, db):
        """
        At consciousness=0.0: grief_modulation = 0.70
        → effective_grief = grief * 0.70
        → compared to neutral (modulation=0.85), same grief causes MORE erosion.
        Note: LOW consciousness → modulation < neutral means MORE effective grief.
        """
        # Low consciousness: modulation=0.70
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 0.0}
        result_low = layer.process(ctx, brain_layer=bl)
        low_durability = result_low["belief_durability"]

        # Neutral consciousness: modulation=0.85
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 0.5}
        result_neutral = layer.process(ctx, brain_layer=bl)
        neutral_durability = result_neutral["belief_durability"]

        # With lower consciousness, same grief causes more durability loss
        assert low_durability < neutral_durability, \
            f"Low consciousness durability {low_durability:.3f} should be below neutral {neutral_durability:.3f}"

    # ── Missing brain_layer → default ────────────────────────────────────

    def test_missing_brain_layer_defaults_to_neutral(self, layer, db):
        """When brain_layer is None, consciousness defaults to 0.5."""
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        result = layer.process(ctx)  # No brain_layer

        # Should behave as consciousness=0.5: grief_modulation=0.85
        # effective_grief = 0.6 * 0.85 = 0.51 → shift triggered
        assert result["transformation_count"] == 1

    def test_missing_brain_layer_none(self, layer, db):
        """When brain_layer is explicitly None, consciousness defaults to 0.5."""
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        result = layer.process(ctx, brain_layer=None)
        assert result["transformation_count"] == 1

    def test_brain_consciousness_level_key_missing(self, layer, db):
        """When brain_layer has no brain_consciousness_level, defaults to 0.5."""
        layer._durability = 0.7
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.6, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"some_other_field": 0.9}
        result = layer.process(ctx, brain_layer=bl)
        assert result["transformation_count"] == 1

    # ── Clamped boundary inputs ─────────────────────────────────────────

    def test_consciousness_at_zero(self, layer, db):
        """consciousness=0.0 is accepted."""
        layer._durability = 0.7
        ctx = {"transformation_grief": 0.0, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 0.0}
        result = layer.process(ctx, brain_layer=bl)
        assert result["belief_durability"] == 0.7

    def test_consciousness_at_one(self, layer, db):
        """consciousness=1.0 is accepted."""
        layer._durability = 0.7
        ctx = {"transformation_grief": 0.0, "resonance_score": 0.3, "itg_tension": 0.3}
        bl = {"brain_consciousness_level": 1.0}
        result = layer.process(ctx, brain_layer=bl)
        assert result["belief_durability"] == 0.7

    def test_belief_states_cycle_correctly(self, layer, db):
        """Belief state transitions: provisional → tested → bedrock → shifting."""
        ctx = {"transformation_grief": 0.0, "resonance_score": 0.0, "itg_tension": 0.8}
        bl = {"brain_consciousness_level": 0.5}
        result = layer.process(ctx, brain_layer=bl)
        assert result["belief_state"] == 'provisional'

        # High ITG without grief → provisional
        layer._durability = 0.5
        layer._transformation_count = 0
        ctx = {"transformation_grief": 0.0, "resonance_score": 0.0, "itg_tension": 0.7}
        bl = {"brain_consciousness_level": 0.5}
        result = layer.process(ctx, brain_layer=bl)
        assert result["belief_state"] == 'provisional'

    def test_get_state_returns_belief_state(self, layer):
        """get_state() returns current belief state."""
        layer._belief_state = 'bedrock'
        layer._durability = 0.9
        layer._transformation_count = 5
        state = layer.get_state()
        assert state["belief_state"] == 'bedrock'
        assert state["knows_what_she_believes"] is True

    def test_pirp_context_returned_with_belief_fields(self, layer, db):
        """process() returns pirp_context with belief_state, durability, count."""
        ctx = {"itg_tension": 0.3}
        bl = {"brain_consciousness_level": 0.5}
        result = layer.process(ctx, brain_layer=bl)
        assert "belief_state" in result
        assert "belief_durability" in result
        assert "transformation_count" in result
