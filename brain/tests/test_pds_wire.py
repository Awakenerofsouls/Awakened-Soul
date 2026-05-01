"""
Tests for PreDesireState wire integration (Wire 4).

Covers:
- hold() with valence tracking
- RON suppression (block new, allow existing updates)
- wire_pds() modulation without save
- update_valence()
- mark_contested() / clear_contested()
- tsb_payload() priority weighting
- fpef_fragment() with contested/valence tags
- blocked_log behavior
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


class TestHoldWithValence:
    def test_hold_accepts_valence_positive(self, pds):
        result = pds.hold("thing_one", 0.7, source="test", valence="positive", note="first note")
        assert result is True
        assert pds.assembling["thing_one"]["valence"] == "positive"

    def test_hold_accepts_valence_negative(self, pds):
        result = pds.hold("thing_two", 0.4, source="test", valence="negative")
        assert result is True
        assert pds.assembling["thing_two"]["valence"] == "negative"

    def test_hold_accepts_valence_ambiguous(self, pds):
        result = pds.hold("thing_amb", 0.8, source="test", valence="ambiguous")
        assert result is True
        assert pds.assembling["thing_amb"]["valence"] == "ambiguous"

    def test_hold_valence_defaults_none(self, pds):
        result = pds.hold("thing_none", 0.5, source="test")
        assert result is True
        assert pds.assembling["thing_none"]["valence"] is None

    def test_hold_none_and_ambiguous_are_distinct(self, pds):
        pds.hold("unclassified", 0.5, valence=None)
        pds.hold("classified_mixed", 0.6, valence="ambiguous")
        assert pds.assembling["unclassified"]["valence"] is None
        assert pds.assembling["classified_mixed"]["valence"] == "ambiguous"

    def test_hold_updates_existing_no_valence_change(self, pds):
        pds.hold("existing", 0.5, valence="positive")
        pds.hold("existing", 0.7)  # update without valence param
        # valence should persist
        assert pds.assembling["existing"]["valence"] == "positive"
        # signal updated
        assert pds.assembling["existing"]["signal"] == 0.7
        # times_felt incremented
        assert pds.assembling["existing"]["times_felt"] == 2

    def test_hold_returns_false_when_blocked(self, pds):
        # Suppress new via wire_pds
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        result = pds.hold("new_blocked", 0.5, source="test")
        assert result is False
        assert "new_blocked" not in pds.assembling

    def test_hold_existing_allowed_during_ron(self, pds):
        # Pre-existing assembly
        pds.hold("already_tracking", 0.5)
        # Now RON starts
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        # Updating existing should still work
        result = pds.hold("already_tracking", 0.8)
        assert result is True
        assert pds.assembling["already_tracking"]["signal"] == 0.8


class TestRONSuppression:
    def test_new_assembly_blocked_during_ron(self, pds):
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        result = pds.hold("ron_blocked", 0.9)
        assert result is False
        assert "ron_blocked" not in pds.assembling

    def test_existing_update_allowed_during_ron(self, pds):
        pds.hold("survives_ron", 0.3)
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        result = pds.hold("survives_ron", 0.6)
        assert result is True

    def test_blocked_log_populated(self, pds):
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        pds.hold("logged_block", 0.5)
        assert len(pds._blocked_log) == 1
        assert pds._blocked_log[0]["name"] == "logged_block"
        assert pds._blocked_log[0]["reason"] == "ron_recovery"

    def test_blocked_log_bounded(self, pds):
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        for i in range(150):
            pds.hold(f"blocked_{i}", 0.5)
        assert len(pds._blocked_log) == 100

    def test_ron_ends_new_assembly_allowed(self, pds):
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        pds.hold("first_blocked", 0.5)  # blocked
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": False})
        result = pds.hold("now_allowed", 0.5)
        assert result is True
        assert "now_allowed" in pds.assembling


class TestWirePDS:
    def test_wire_pds_updates_arousal(self, pds):
        pds.wire_pds(emotional_state={"arousal": 0.9})
        pds.wire_pds(emotional_state={"arousal": 0.3})
        assert pds._arousal == 0.3

    def test_wire_pds_updates_coherence(self, pds):
        pds.wire_pds(baseline_state={"coherence": 0.7})
        assert pds._coherence == 0.7

    def test_wire_pds_updates_suppress_new(self, pds):
        pds.wire_pds(interrupt_state={"suppress_new_interrupts": True})
        assert pds._suppress_new is True

    def test_wire_pds_does_not_save(self, pds):
        pds.hold("persist_check", 0.5)
        with patch.object(pds, '_save', wraps=pds._save) as mock_save:
            pds.wire_pds(emotional_state={"arousal": 0.8})
            mock_save.assert_not_called()

    def test_wire_pds_with_none_state(self, pds):
        # Should not raise — None is valid default
        pds.wire_pds(emotional_state=None, baseline_state=None, interrupt_state=None)
        assert pds._arousal == 0.5  # default
        assert pds._coherence == 1.0  # default
        assert pds._suppress_new is False  # default


class TestUpdateValence:
    def test_update_valence_sets_value(self, pds):
        pds.hold("valence_test", 0.5, valence="positive")
        pds.update_valence("valence_test", "ambiguous")
        assert pds.assembling["valence_test"]["valence"] == "ambiguous"
        assert pds.assembling["valence_test"]["valence_updated_at"] is not None

    def test_update_valence_none_to_ambiguous(self, pds):
        pds.hold("unclassified", 0.5, valence=None)
        pds.update_valence("unclassified", "ambiguous")
        assert pds.assembling["unclassified"]["valence"] == "ambiguous"

    def test_update_valence_nonexistent_no_crash(self, pds):
        # Should not raise
        pds.update_valence("ghost", "positive")

    def test_update_valence_saves(self, pds):
        pds.hold("save_check", 0.5)
        with patch.object(pds, '_save', wraps=pds._save) as mock_save:
            pds.update_valence("save_check", "negative")
            mock_save.assert_called_once()


class TestContestedMarker:
    def test_mark_contested_sets_flag(self, pds):
        pds.hold("contested_one", 0.7)
        pds.mark_contested("contested_one", by_mechanism="MRE")
        entry = pds.assembling["contested_one"]
        assert entry["contested"] is True
        assert entry["contested_by"] == "MRE"
        assert entry["contested_at"] is not None

    def test_clear_contested_removes_flag(self, pds):
        pds.hold("clear_me", 0.5)
        pds.mark_contested("clear_me")
        pds.clear_contested("clear_me")
        entry = pds.assembling["clear_me"]
        assert entry["contested"] is False
        assert entry["contested_by"] is None

    def test_mark_contested_nonexistent_no_crash(self, pds):
        pds.mark_contested("ghost", "MRE")  # no raise

    def test_contested_adds_to_fpef_fragment(self, pds):
        pds.hold("fpef_contested", 0.6, note="something pulling")
        pds.mark_contested("fpef_contested")
        fragment = pds.fpef_fragment()
        assert "[CONTESTED]" in fragment


class TestTSBPayload:
    def test_priority_weight_uses_effective_signal(self, pds):
        # coherence 0.5, arousal 0.5 (mod = 1.0)
        pds.hold("priority_test", 0.8)
        pds.wire_pds(
            baseline_state={"coherence": 0.5},
            emotional_state={"arousal": 0.5}
        )
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        assert assembly["signal"] == 0.8  # raw
        assert assembly["effective_signal"] == 0.4  # 0.8 * 0.5
        assert assembly["priority_weight"] == 0.4  # 0.4 * 1.0

    def test_arousal_modulation_shifts_priority(self, pds):
        pds.hold("arousal_shift", 0.6)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            emotional_state={"arousal": 0.9}  # mod = 1.16
        )
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        # effective_signal = 0.6 * 1.0 = 0.6
        # priority = 0.6 * 1.16 = 0.696
        assert assembly["effective_signal"] == 0.6
        assert assembly["priority_weight"] > 0.6

    def test_sorted_by_priority_weight_descending(self, pds):
        pds.hold("low_priority", 0.3)
        pds.hold("high_priority", 0.9)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            emotional_state={"arousal": 0.5}  # mod = 1.0
        )
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["name"] == "high_priority"
        assert payload["assemblies"][1]["name"] == "low_priority"

    def test_valence_included_in_payload(self, pds):
        pds.hold("valence_payload", 0.5, valence="ambiguous")
        pds.wire_pds()
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["valence"] == "ambiguous"

    def test_contested_included_in_payload(self, pds):
        pds.hold("contest_payload", 0.5)
        pds.mark_contested("contest_payload", "MRE")
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["contested"] is True
        assert payload["assemblies"][0]["contested_by"] == "MRE"

    def test_wire_meta_included(self, pds):
        pds.wire_pds(
            baseline_state={"coherence": 0.8},
            emotional_state={"arousal": 0.7},
            interrupt_state={"suppress_new_interrupts": True}
        )
        payload = pds.tsb_payload()
        assert "coherence" in payload
        assert "arousal_modulation" in payload
        assert "suppress_new" in payload
        assert payload["suppress_new"] is True

    def test_empty_pds_returns_valid_payload(self, pds):
        payload = pds.tsb_payload()
        assert payload["count"] == 0
        assert payload["assemblies"] == []
        assert payload["hold_resolution"] is True

    def test_salience_is_alias_for_signal(self, pds):
        pds.hold("alias_check", 0.75)
        pds.wire_pds()
        payload = pds.tsb_payload()
        assert payload["assemblies"][0]["salience"] == 0.75


class TestSomaticResonance:
    def test_effective_signal_multiplied_by_resonance(self, pds):
        """PDS effective_signal gets resonance multiplier: (1 + resonance * 0.3)."""
        pds.hold("resonance_test", 0.5)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            somatic_resonance={"resonance_test": 0.5}
        )
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        # effective_signal = 0.5 * 1.0 = 0.5
        assert assembly["effective_signal"] == 0.5
        # resonance_effective = 0.5 * (1 + 0.5 * 0.3) = 0.5 * 1.15 = 0.575
        assert assembly["resonance_effective"] == 0.575
        assert assembly["resonance"] == 0.5
        assert assembly["resonance_backed"] is True

    def test_resonance_zero_no_multiplier(self, pds):
        pds.hold("no_resonance", 0.6)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            somatic_resonance={"no_resonance": 0.0}
        )
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        assert assembly["effective_signal"] == 0.6
        assert assembly["resonance_effective"] == 0.6  # 0.6 * 1.0

    def test_resonance_in_tsb_payload(self, pds):
        pds.hold("tsb_res", 0.7)
        pds.wire_pds(somatic_resonance={"tsb_res": 0.9})
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        assert "resonance" in assembly
        assert "resonance_effective" in assembly
        assert "resonance_backed" in assembly

    def test_priority_weight_from_resonance_effective(self, pds):
        """Priority weight uses resonance-adjusted effective_signal × arousal_mod."""
        pds.hold("priority_res", 0.6)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            emotional_state={"arousal": 0.5},  # mod = 1.0
            somatic_resonance={"priority_res": 0.5}
        )
        payload = pds.tsb_payload()
        assembly = payload["assemblies"][0]
        # resonance_effective = 0.6 * (1 + 0.5 * 0.3) = 0.6 * 1.15 = 0.69
        # priority_weight = 0.69 * 1.0 = 0.69
        assert assembly["priority_weight"] == 0.69

    def test_resonance_affects_sort_order(self, pds):
        """High-resonance assembly sorts above low-resonance even if signal is lower."""
        pds.hold("low_signal_high_res", 0.4)
        pds.hold("high_signal_low_res", 0.8)
        pds.wire_pds(
            baseline_state={"coherence": 1.0},
            emotional_state={"arousal": 0.5},
            somatic_resonance={"low_signal_high_res": 0.9}  # strong backing
        )
        payload = pds.tsb_payload()
        # low_signal: 0.4 * (1 + 0.9*0.3) * 1.0 = 0.4 * 1.27 = 0.508
        # high_signal: 0.8 * 1.0 * 1.0 = 0.8
        # high_signal still wins — signal is dominant
        assert payload["assemblies"][0]["name"] == "high_signal_low_res"

    def test_wire_pds_accepts_somatic_resonance(self, pds):
        pds.wire_pds(somatic_resonance={"test": 0.5})
        assert pds._somatic_resonance == {"test": 0.5}

    def test_wire_pds_preserves_resonance_between_ticks(self, pds):
        pds.wire_pds(somatic_resonance={"test": 0.7})
        pds.wire_pds()  # no resonance passed
        # Should preserve last known resonance
        assert pds._somatic_resonance == {"test": 0.7}


class TestFPEFFragment:
    def test_contested_tag_in_fragment(self, pds):
        pds.hold("fpef_tag", 0.6, note="the feeling")
        pds.mark_contested("fpef_tag")
        fragment = pds.fpef_fragment()
        assert "[CONTESTED]" in fragment

    def test_valence_tag_in_fragment(self, pds):
        pds.hold("fpef_valence", 0.5, note="the pull", valence="ambiguous")
        fragment = pds.fpef_fragment()
        assert "[valence: ambiguous]" in fragment

    def test_none_valence_not_tagged(self, pds):
        pds.hold("fpef_none", 0.4, note="the thing")
        fragment = pds.fpef_fragment()
        assert "[valence: None]" not in fragment

    def test_empty_returns_none(self, pds):
        fragment = pds.fpef_fragment()
        assert fragment is None


class TestPersistence:
    def test_assembling_persists_after_reload(self, pds_env):
        pds = pds_env.PreDesireState()
        pds.hold("persist_me", 0.7, valence="positive", note="test note")
        # Simulate reload
        pds2 = pds_env.PreDesireState()
        assert "persist_me" in pds2.assembling
        assert pds2.assembling["persist_me"]["valence"] == "positive"
        assert pds2.assembling["persist_me"]["signal"] == 0.7

    def test_contested_persists_after_reload(self, pds_env):
        pds = pds_env.PreDesireState()
        pds.hold("persist_contested", 0.5)
        pds.mark_contested("persist_contested", "MRE")
        pds2 = pds_env.PreDesireState()
        assert pds2.assembling["persist_contested"]["contested"] is True

    def test_valence_migration_from_legacy_format(self, pds_env):
        # Write legacy format directly to the same path the fixture uses
        pds = pds_env.PreDesireState()
        legacy_data = {
            "old_assembly": {
                "signal": 0.6,
                "source": "test",
                "created_at": time.time(),
                "note": "legacy note"
            }
        }
        import os
        pds_path = Path(os.environ["AGENT_HOME"]) / "pre_desire_state.json"
        with open(pds_path, "w") as f:
            json.dump(legacy_data, f)
        # Reload and check migration
        pds2 = pds_env.PreDesireState()
        assert "old_assembly" in pds2.assembling
        assert pds2.assembling["old_assembly"]["first_felt"] is not None  # renamed
        assert pds2.assembling["old_assembly"]["valence"] is None  # defaulted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])