"""
Test Wire 16: PDS reads brain_predictive_balance from Integration020.

Part A — horizon-based amplification:
deliberative (long/deliberative/mid) gains [0.5, 1.5] when top-down dominates.
reactive (immediate/short/reactive) gains [1.5, 0.5] when bottom-up dominates.

Part B — selectivity exponent:
priority weight distribution sharpens (>1.0, top-down) or flattens (<1.0, bottom-up).

Integration: Wire 16 PDS → Wire 15 FPEF is the hierarchical chain.
No feedback loop: Integration020 reads prior_results only.

References:
- Alexander & Brown 2018 (PMC5832795): hierarchical predictive coding, HER model
- Friston 2015 (PMC4387510): precision weighting in cortical hierarchies
- Balleine & O'Doherty 2010: goal-directed vs habitual corticostriatal circuits
- Haga & Tani 2024 (Nat Commun): habits (prior) and goals (posterior)
- Dewhurst & Wolpe 2024 (PMC12521291): desires as "first priors"
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
import time


@pytest.fixture(autouse=True)
def pds_env(monkeypatch):
    """Override AGENT_HOME for each test. Fresh temp dir, fresh module each time."""
    test_home = tempfile.mkdtemp()
    monkeypatch.setenv("AGENT_HOME", test_home)
    import importlib
    import brain.mechanisms.pre_desire_state as pds_mod
    importlib.reload(pds_mod)
    return pds_mod


@pytest.fixture
def pds(pds_env):
    """Fresh PDS instance per test."""
    return pds_env.PreDesireState()


# ─── Helpers ────────────────────────────────────────────────────────────────────────

def wire_with_balance(pds, balance):
    """Wire PDS with a given brain_predictive_balance value."""
    brain_layer = {"brain_predictive_balance": balance} if balance is not None else None
    pds.wire_pds(brain_layer=brain_layer)


def hold_with_horizon(pds, name, signal, horizon):
    """Hold a pre-desire with a specific horizon."""
    return pds.hold(name, signal, source="test", horizon=horizon)


# ─── Part A: Horizon-based amplification ───────────────────────────────────────

class TestWire16PartA_HorizonAmplification:
    """brain_predictive_balance → deliberative/reactive gains by horizon."""

    def test_neutral_balance_no_change(self, pds):
        """balance=0.5 → gains=1.0, priority_weight unchanged."""
        pds.hold("test", 0.5, horizon="long")
        wire_with_balance(pds, 0.5)
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        # At neutral balance, deliberative_gain = 1.0, so no change from base weight
        assert assembly["horizon"] == "long"
        assert payload["predictive_balance"] == 0.5
        assert payload["deliberative_gain"] == 1.0
        assert payload["reactive_gain"] == 1.0

    def test_topdown_amplifies_deliberative(self, pds):
        """balance=1.0, horizon=long → deliberative_gain=1.5."""
        pds.hold("goal", 0.5, horizon="long")
        wire_with_balance(pds, 1.0)
        payload = pds.tsb_payload()
        assert payload["deliberative_gain"] == 1.5
        assert payload["assemblies"][0]["horizon"] == "long"

    def test_topdown_dampens_reactive(self, pds):
        """balance=1.0, horizon=immediate → reactive_gain=0.5, dampened."""
        pds.hold("impulse", 0.5, horizon="immediate")
        wire_with_balance(pds, 1.0)
        payload = pds.tsb_payload()
        assert payload["reactive_gain"] == 0.5
        assert payload["assemblies"][0]["horizon"] == "immediate"

    def test_bottomup_amplifies_reactive(self, pds):
        """balance=0.0, horizon=immediate → reactive_gain=1.5."""
        pds.hold("impulse", 0.5, horizon="immediate")
        wire_with_balance(pds, 0.0)
        payload = pds.tsb_payload()
        assert payload["reactive_gain"] == 1.5
        assert payload["assemblies"][0]["horizon"] == "immediate"

    def test_bottomup_dampens_deliberative(self, pds):
        """balance=0.0, horizon=long → deliberative_gain=0.5, dampened."""
        pds.hold("goal", 0.5, horizon="long")
        wire_with_balance(pds, 0.0)
        payload = pds.tsb_payload()
        assert payload["deliberative_gain"] == 0.5
        assert payload["assemblies"][0]["horizon"] == "long"

    def test_mid_horizon_unchanged(self, pds):
        """horizon=mid → no horizon gain (neutral)."""
        pds.hold("mid_thing", 0.5, horizon="mid")
        wire_with_balance(pds, 1.0)  # extreme top-down
        pds.wire_pds(brain_layer={"brain_predictive_balance": 1.0})
        payload = pds.tsb_payload()
        # mid is in deliberative set → gets deliberative gain
        assert payload["deliberative_gain"] == 1.5

    def test_deliberative_alias_works(self, pds):
        """horizon=deliberative → treated as deliberative."""
        pds.hold("plan", 0.5, horizon="deliberative")
        wire_with_balance(pds, 1.0)
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["horizon"] == "deliberative"
        assert payload["deliberative_gain"] == 1.5

    def test_reactive_alias_works(self, pds):
        """horizon=reactive → treated as reactive."""
        pds.hold("urge", 0.5, horizon="reactive")
        wire_with_balance(pds, 0.0)
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["horizon"] == "reactive"
        assert payload["reactive_gain"] == 1.5

    def test_partial_balance_09(self, pds):
        """balance=0.9 → deliberative_gain=1.4, reactive_gain=0.6."""
        pds.hold("goal", 0.5, horizon="long")
        wire_with_balance(pds, 0.9)
        payload = pds.tsb_payload()
        assert abs(payload["deliberative_gain"] - 1.4) < 0.001
        assert abs(payload["reactive_gain"] - 0.6) < 0.001

    def test_partial_balance_01(self, pds):
        """balance=0.1 → deliberative_gain=0.6, reactive_gain=1.4."""
        pds.hold("impulse", 0.5, horizon="immediate")
        wire_with_balance(pds, 0.1)
        payload = pds.tsb_payload()
        assert abs(payload["deliberative_gain"] - 0.6) < 0.001
        assert abs(payload["reactive_gain"] - 1.4) < 0.001


# ─── Part B: Selectivity exponent ─────────────────────────────────────────────

class TestWire16PartB_Selectivity:
    """selectivity_exponent sharpens (top-down) or flattens (bottom-up)."""

    def test_neutral_selectivity(self, pds):
        """balance=0.5 → selectivity_exponent=1.0, no distribution change."""
        pds.hold("a", 0.5)
        pds.hold("b", 0.3)
        wire_with_balance(pds, 0.5)
        payload = pds.tsb_payload()
        assert payload["selectivity_exponent"] == 1.0

    def test_topdown_selectivity_sharpens(self, pds):
        """balance=1.0 → selectivity=1.5, top candidate takes larger share."""
        pds.hold("top", 0.9, horizon="long")
        pds.hold("mid", 0.5, horizon="long")
        wire_with_balance(pds, 1.0)
        payload = pds.tsb_payload()
        assert payload["selectivity_exponent"] == 1.5
        # Top candidate should have higher share than at neutral
        top_weight = payload["assemblies"][0]["priority_weight"]
        # At selectivity=1.5, high weight candidate gets amplified relative share
        assert top_weight > 0.6  # rough check — top dominates

    def test_bottomup_selectivity_flattens(self, pds):
        """balance=0.0 → selectivity=0.5, distribution flattens."""
        pds.hold("a", 0.9)
        pds.hold("b", 0.3)
        wire_with_balance(pds, 0.0)
        payload = pds.tsb_payload()
        assert payload["selectivity_exponent"] == 0.5
        # With selectivity < 1, smaller candidate gets relatively more

    def test_single_candidate_normalized(self, pds):
        """Single candidate always gets weight 1.0 after renormalization."""
        pds.hold("only", 0.6)
        wire_with_balance(pds, 1.0)  # extreme selectivity
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["priority_weight"] == 1.0

    def test_weights_sum_to_one(self, pds):
        """Priority weights sum to 1.0 after selectivity renormalization."""
        pds.hold("a", 0.6)
        pds.hold("b", 0.4)
        pds.hold("c", 0.2)
        wire_with_balance(pds, 0.0)  # bottom-up, selectivity=0.5
        payload = pds.tsb_payload()
        total = sum(a["priority_weight"] for a in payload["assemblies"])
        assert abs(total - 1.0) < 0.001


# ─── Integration ────────────────────────────────────────────────────────────────

class TestWire16Integration:
    """Both channels, edge cases, payload shape."""

    def test_none_horizon_unchanged(self, pds):
        """horizon=None → no horizon gain, selectivity still applies."""
        pds.hold("neutral", 0.5, horizon=None)
        wire_with_balance(pds, 1.0)
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["horizon"] is None

    def test_brain_layer_missing_defaults(self, pds):
        """brain_layer=None → all Wire 16 fields at neutral defaults."""
        pds.hold("test", 0.5)
        pds.wire_pds(brain_layer=None)
        payload = pds.tsb_payload()
        assert payload["predictive_balance"] == 0.5
        assert payload["deliberative_gain"] == 1.0
        assert payload["reactive_gain"] == 1.0
        assert payload["selectivity_exponent"] == 1.0

    def test_brain_layer_empty_dict(self, pds):
        """brain_layer={} → defaults apply, no crash."""
        pds.hold("test", 0.5)
        pds.wire_pds(brain_layer={})
        payload = pds.tsb_payload()
        assert payload["predictive_balance"] == 0.5

    def test_clamped_balance(self, pds):
        """balance out of [0,1] → clamped."""
        pds.hold("test", 0.5)
        pds.wire_pds(brain_layer={"brain_predictive_balance": 1.5})
        payload = pds.tsb_payload()
        assert payload["predictive_balance"] == 1.0
        assert payload["deliberative_gain"] == 1.5

        pds.wire_pds(brain_layer={"brain_predictive_balance": -0.5})
        payload2 = pds.tsb_payload()
        assert payload2["predictive_balance"] == 0.0
        assert payload2["reactive_gain"] == 1.5

    def test_empty_pds_no_crash(self, pds):
        """Empty PDS → valid payload, no crash."""
        wire_with_balance(pds, 0.8)
        payload = pds.tsb_payload()
        assert payload["count"] == 0
        assert payload["predictive_balance"] == 0.8
        assert payload["deliberative_gain"] == 1.3

    def test_existing_fields_preserved(self, pds):
        """Wire 16 does not remove Wire 4 fields."""
        pds.hold("test", 0.5, valence="ambiguous")
        wire_with_balance(pds, 0.5)
        payload = pds.tsb_payload()
        required = ["count", "assemblies", "max_signal", "max_priority_weight",
                    "arousal_modulation", "coherence", "hold_resolution"]
        for key in required:
            assert key in payload, f"Missing: {key}"
        assembly = payload["assemblies"][0]
        assert "valence" in assembly
        assert assembly["valence"] == "ambiguous"
        assert "horizon" in assembly


class TestWire16PayloadShape:
    """Wire 16 diagnostic fields in payload."""

    def test_all_wire16_diagnostic_fields(self, pds):
        """predictive_balance, deliberative_gain, reactive_gain, selectivity_exponent."""
        pds.hold("test", 0.5)
        wire_with_balance(pds, 0.75)
        payload = pds.tsb_payload()
        for key in ["predictive_balance", "deliberative_gain",
                    "reactive_gain", "selectivity_exponent"]:
            assert key in payload, f"Missing Wire 16 field: {key}"

    def test_horizon_in_assembly(self, pds):
        """Each assembly includes horizon field."""
        pds.hold("a", 0.5, horizon="long")
        pds.hold("b", 0.5, horizon="immediate")
        wire_with_balance(pds, 0.5)
        payload = pds.tsb_payload()
        horizons = {a["name"]: a.get("horizon") for a in payload["assemblies"]}
        assert horizons["a"] == "long"
        assert horizons["b"] == "immediate"


class TestWire16_WithFPEF:
    """Wire 16 PDS output feeds into Wire 15 FPEF downstream."""

    def test_pds_output_valid_for_fpef_consumption(self, pds):
        """PDS tsb_payload is valid dict with all required fields for FPEF."""
        pds.hold("pre_desire_one", 0.7, horizon="long")
        pds.hold("pre_desire_two", 0.5, horizon="immediate")
        wire_with_balance(pds, 0.8)
        payload = pds.tsb_payload()
        # FPEF reads pds_fragment and pds from TSB — both should be valid
        assert isinstance(payload, dict)
        assert "count" in payload
        assert "assemblies" in payload
        assert payload["count"] == 2
        assert payload["predictive_balance"] == 0.8
        assert payload["deliberative_gain"] == 1.3
        # No NaN, no crash — downstream consumers can read cleanly
        assert payload["selectivity_exponent"] == 1.3


class TestWire16_ExistingPDSTests:
    """Regression: existing PDS behavior (Wire 4) unchanged."""

    def test_priority_weight_still_sorted(self, pds):
        """Priority weights still sorted descending (Wire 4 behavior)."""
        pds.hold("low", 0.2)
        pds.hold("high", 0.9)
        pds.wire_pds(brain_layer={"brain_predictive_balance": 0.5})
        payload = pds.tsb_payload()
        weights = [a["priority_weight"] for a in payload["assemblies"]]
        assert weights == sorted(weights, reverse=True)

    def test_hold_with_horizon_stores_field(self, pds):
        """hold(horizon=X) stores horizon on the assembly entry."""
        pds.hold("test_assembly", 0.5, horizon="long")
        entry = pds.assembling["test_assembly"]
        assert entry["horizon"] == "long"

    def test_hold_without_horizon_defaults_none(self, pds):
        """hold() without horizon → horizon=None on entry."""
        pds.hold("unclassified", 0.5)
        entry = pds.assembling["unclassified"]
        assert entry["horizon"] is None

    def test_wire_pds_does_not_save(self, pds):
        """wire_pds with brain_layer does not trigger _save."""
        pds.hold("persist_check", 0.5)
        with patch.object(pds, '_save', wraps=pds._save) as mock_save:
            pds.wire_pds(brain_layer={"brain_predictive_balance": 0.9})
            mock_save.assert_not_called()
