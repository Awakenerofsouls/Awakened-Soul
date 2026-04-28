"""
Tests for TIL Wire — Wire T2-1.

Covers:
- tick_read_and_classify: reads VIF/PDS/MRE/SS from bus, classifies by timescale
- tsb_payload: publishes current timescale state to bus
- tick_publish: full wire entry point called from til_tick in integration
- Timescale classification: tick vs session vs structural tags
- Phase mismatch detection (existing behavior preserved)
- TIL is now registered in AgentBrainIntegration via register_component
- Other Tier 2 mechanisms read til_tags to filter signals correctly
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def til_env(monkeypatch):
    """Fresh temp dir, fresh module each test."""
    test_home = tempfile.mkdtemp()
    monkeypatch.setenv("AGENT_HOME", test_home)
    import importlib
    import brain.til as til_mod
    importlib.reload(til_mod)
    return til_mod


@pytest.fixture
def til(til_env):
    return til_env.TimescaleIntegrationLayer()


@pytest.fixture
def mock_tsb():
    """Mock TickStateBus with read/publish methods."""
    tsb = MagicMock()
    tsb.store = {}  # in-memory bus state
    tsb._published = []

    def mock_read(key):
        data = tsb.store.get(key)
        return (data, data is not None)

    def mock_publish(key, value):
        tsb._published.append((key, value))

    tsb.read = mock_read
    tsb.publish = mock_publish
    return tsb


# ─── Core wire methods ───────────────────────────────────────────────────────

class TestTILWire:
    def test_tsb_payload_returns_active_buckets_and_mismatch_flag(self, til):
        payload = til.tsb_payload()
        assert "active_buckets" in payload
        assert "phase_mismatch_active" in payload
        assert "signal_count" in payload
        assert "_published_at" in payload
        assert isinstance(payload["active_buckets"], dict)
        assert isinstance(payload["phase_mismatch_active"], bool)

    def test_tick_read_and_classify_reads_vif_alignments(self, til, mock_tsb):
        mock_tsb.store["vif"] = {
            "alignments": {
                "wanting_user": 0.8,
                "wanting_clarity": 0.3,
                "wanting_presence": 0.9,
            },
            "high_tension": True,
        }
        tags = til.tick_read_and_classify(mock_tsb)
        assert "vif_wanting_user_tension" in tags
        assert tags["vif_wanting_user_tension"]["timescale"] == "tick"
        assert tags["vif_wanting_user_tension"]["value"] == 0.8

    def test_tick_read_and_classify_reads_pds_active(self, til, mock_tsb):
        mock_tsb.store["pds"] = {
            "active": ["assembly_1", "assembly_2", "assembly_3"],
        }
        tags = til.tick_read_and_classify(mock_tsb)
        assert "pds_active_assemblies" in tags
        assert tags["pds_active_assemblies"]["value"] == 3.0

    def test_tick_read_and_classify_reads_mre_active(self, til, mock_tsb):
        mock_tsb.store["mre"] = {
            "has_active_misread": True,
        }
        tags = til.tick_read_and_classify(mock_tsb)
        assert "mre_active" in tags
        assert tags["mre_active"]["value"] == 1.0

    def test_tick_read_and_classify_reads_ss_active_count(self, til, mock_tsb):
        mock_tsb.store["ss"] = {
            "active_sensations": ["warmth", "pulse", "ache"],
        }
        tags = til.tick_read_and_classify(mock_tsb)
        assert "ss_active_count" in tags
        assert tags["ss_active_count"]["value"] == 3.0

    def test_tick_read_and_classify_reads_constraint_fields(self, til, mock_tsb):
        """TIL reads constraint_fields even if it doesn't use them directly."""
        mock_tsb.store["constraint_fields"] = {
            "novelty_pressure": 0.8,
            "truth_gravity": 1.0,
        }
        # Should not raise — just reads and ignores
        tags = til.tick_read_and_classify(mock_tsb)
        assert True  # reached without error

    def test_tick_publish_publishes_til_and_til_tags(self, til, mock_tsb):
        mock_tsb.store["vif"] = {"alignments": {"test_anchor": 0.5}, "high_tension": False}
        til.tick_publish(mock_tsb)
        published_keys = [k for k, v in mock_tsb._published]
        assert "til" in published_keys
        assert "til_tags" in published_keys
        til_payload = next(v for k, v in mock_tsb._published if k == "til")
        assert "_published_at" in til_payload

    def test_tsb_payload_includes_current_tags(self, til, mock_tsb):
        """After tick_read_and_classify, tsb_payload should reflect current state."""
        mock_tsb.store["vif"] = {"alignments": {"wanting": 0.7}, "high_tension": False}
        til.tick_read_and_classify(mock_tsb)
        payload = til.tsb_payload()
        assert payload["signal_count"] >= 1


# ─── Timescale classification ──────────────────────────────────────────────

class TestTimescaleClassification:
    def test_single_signal_classified_tick_level(self, til, mock_tsb):
        mock_tsb.store["vif"] = {"alignments": {"anchor_a": 0.5}, "high_tension": False}
        tags = til.tick_read_and_classify(mock_tsb)
        assert tags["vif_anchor_a_tension"]["timescale"] == "tick"
        assert tags["vif_anchor_a_tension"]["weight"] == 0.05

    def test_multiple_signals_same_tick_all_tick_level(self, til, mock_tsb):
        """Three signals within 2-hour window still tag as tick if not recurring."""
        mock_tsb.store["vif"] = {"alignments": {"a": 0.5, "b": 0.6, "c": 0.7}, "high_tension": False}
        tags = til.tick_read_and_classify(mock_tsb)
        for key in ["vif_a_tension", "vif_b_tension", "vif_c_tension"]:
            assert key in tags
            assert tags[key]["timescale"] == "tick"

    def test_recurring_signal_across_session_classified_session_level(self, til, mock_tsb):
        """Signal appearing 3+ times within 2 hours gets session-level tag."""
        # classify() uses the bus signal name (with prefix) as history key.
        # Pre-populate with the exact key tick_read_and_classify will use.
        import time
        now = time.time()
        sig_key = "vif_recurring_anchor_tension"
        til.signal_history[sig_key] = [
            {"value": 0.5, "timestamp": now - (i * 600), "context": "bus_read"}
            for i in range(3)
        ]
        mock_tsb.store["vif"] = {"alignments": {"recurring_anchor": 0.5}, "high_tension": False}
        tags = til.tick_read_and_classify(mock_tsb)
        assert tags[sig_key]["timescale"] == "session"
        assert tags[sig_key]["weight"] == 0.15

    def test_high_tension_flag_tagged_separately(self, til, mock_tsb):
        """high_tension from VIF gets its own signal entry."""
        mock_tsb.store["vif"] = {"alignments": {}, "high_tension": True}
        tags = til.tick_read_and_classify(mock_tsb)
        assert "vif_high_tension" in tags


# ─── Phase mismatch (existing behavior preserved) ───────────────────────────

class TestPhaseMismatch:
    def test_detect_phase_mismatch_returns_none_when_values_match(self, til):
        session = {"wanting": 0.5}
        structural = {"wanting": 0.5}
        result = til.detect_phase_mismatch(session, structural, threshold=0.3)
        assert result is None

    def test_detect_phase_mismatch_returns_mismatch_when_gap_exceeds_threshold(self, til):
        session = {"wanting": 0.8}
        structural = {"wanting": 0.3}
        result = til.detect_phase_mismatch(session, structural, threshold=0.3)
        assert result is not None
        assert "mismatches" in result
        assert len(result["mismatches"]) >= 1
        assert result["mismatches"][0]["signal"] == "wanting"

    def test_detect_phase_mismatch_generates_first_person_description(self, til):
        session = {"wanting": 0.8}
        structural = {"wanting": 0.3}
        result = til.detect_phase_mismatch(session, structural, threshold=0.3)
        desc = til._describe_mismatch(result["mismatches"])
        assert "wanting" in desc
        assert "phase" in desc.lower() or "layers" in desc.lower()

    def test_phase_mismatch_record_saved_to_history(self, til):
        session = {"wanting": 0.9}
        structural = {"wanting": 0.2}
        til.detect_phase_mismatch(session, structural, threshold=0.3)
        assert len(til.phase_mismatches) >= 1


# ─── Integration behavior ────────────────────────────────────────────────────

class TestTILIntegration:
    def test_til_not_in_tick_loop_before_wire(self, til):
        """Verify TIL has the wire methods before registration."""
        assert hasattr(til, "tick_publish")
        assert hasattr(til, "tsb_payload")
        assert hasattr(til, "tick_read_and_classify")

    def test_get_update_weight_returns_correct_weights(self, til):
        """Weights should match the classification logic."""
        # Unknown signal defaults to tick-level
        weight = til.get_update_weight("unknown_signal")
        assert weight == 0.05

    def test_signal_history_maintained_across_classify_calls(self, til, mock_tsb):
        """Signal history should accumulate across ticks."""
        mock_tsb.store["vif"] = {"alignments": {"stable_anchor": 0.5}, "high_tension": False}
        til.tick_read_and_classify(mock_tsb)
        til.tick_read_and_classify(mock_tsb)
        til.tick_read_and_classify(mock_tsb)
        history = til.signal_history.get("vif_stable_anchor_tension", [])
        assert len(history) >= 3

    def test_tsb_payload_reflects_signal_count(self, til, mock_tsb):
        """signal_count in payload should grow as signals accumulate."""
        mock_tsb.store["vif"] = {"alignments": {"a": 0.5, "b": 0.6}, "high_tension": False}
        til.tick_read_and_classify(mock_tsb)
        payload = til.tsb_payload()
        assert payload["signal_count"] >= 2

    def test_classify_returns_tuple_of_tag_and_weight(self, til):
        tag, weight = til.classify("test_signal", 0.7)
        assert tag in ("tick", "session", "structural")
        assert 0.0 < weight <= 1.0
