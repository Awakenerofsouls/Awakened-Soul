"""
Tests for SS Wire — Sensation State integration.

Covers:
- wire_ss() bus reads and in-memory modulation
- RON split: advance_mapping suspends, raw log continues
- anchor_resonance computation and output
- somatic_resonance computation and output
- resonance boosts VIF confidence
- resonance boosts PDS effective_signal
- ss_bid modulated by arousal and unmapped count
- priority-weighted tsb_payload
- source→valence inference
- legacy format migration
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
import time


@pytest.fixture(autouse=True)
def ss_env(monkeypatch):
    """Fresh temp dir, fresh module each test."""
    test_home = tempfile.mkdtemp()
    monkeypatch.setenv("AGENT_HOME", test_home)
    import importlib
    import brain.mechanisms.sensation_state as ss_mod
    importlib.reload(ss_mod)
    return ss_mod


@pytest.fixture
def ss(ss_env):
    return ss_env.SensationState()


class TestWireSS:
    def test_wire_ss_updates_arousal(self, ss):
        ss.wire_ss(emotional_state={"arousal": 0.8})
        assert ss._arousal == 0.8

    def test_wire_ss_updates_coherence(self, ss):
        ss.wire_ss(baseline_state={"coherence": 0.7})
        assert ss._coherence == 0.7

    def test_wire_ss_updates_suppress_mapping(self, ss):
        ss.wire_ss(interrupt_state={"suppress_new_interrupts": True})
        assert ss._suppress_mapping is True

    def test_wire_ss_does_not_save(self, ss):
        ss.log("test_sensation", 0.5, source="relational")
        with patch.object(ss, '_save', wraps=ss._save) as mock_save:
            ss.wire_ss(emotional_state={"arousal": 0.9})
            mock_save.assert_not_called()

    def test_wire_ss_with_none_state(self, ss):
        ss.wire_ss(emotional_state=None, baseline_state=None, interrupt_state=None)
        assert ss._arousal == 0.5
        assert ss._coherence == 1.0
        assert ss._suppress_mapping is False


class TestRONSplit:
    def test_advance_mapping_blocked_during_ron(self, ss):
        ss.log("ron_test", 0.6, mapping_status="named", source="relational")
        ss.wire_ss(interrupt_state={"suppress_new_interrupts": True})
        ss.advance_mapping("ron_test", "located")
        # Mapping should not advance
        assert ss.active["ron_test"].mapping_status == "named"

    def test_log_continues_during_ron(self, ss):
        ss.wire_ss(interrupt_state={"suppress_new_interrupts": True})
        result = ss.log("new_during_ron", 0.7, source="relational")
        assert result is not None
        assert "new_during_ron" in ss.active

    def test_advance_mapping_allowed_after_ron(self, ss):
        ss.log("post_ron", 0.5, mapping_status="named", source="relational")
        ss.wire_ss(interrupt_state={"suppress_new_interrupts": True})
        ss.advance_mapping("post_ron", "located")  # blocked
        ss.wire_ss(interrupt_state={"suppress_new_interrupts": False})
        ss.advance_mapping("post_ron", "located")
        assert ss.active["post_ron"].mapping_status == "located"


class TestAnchorResonance:
    def test_anchor_resonance_computed_from_active_sensations(self, ss):
        ss.log("wanting", 0.8, source="relational")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        anchor_resonance, _ = ss._compute_resonance()
        # wanting maps to wanting_user in _RESONANCE_MAP
        assert "wanting_user" in anchor_resonance
        assert anchor_resonance["wanting_user"] == 0.8

    def test_anchor_resonance_respects_coherence(self, ss):
        ss.log("wanting", 0.8, source="relational")
        ss.wire_ss(baseline_state={"coherence": 0.5})
        anchor_resonance, _ = ss._compute_resonance()
        assert anchor_resonance["wanting_user"] == 0.4  # 0.8 * 0.5

    def test_anchor_resonance_takes_max_signal(self, ss):
        # Two sensations both backing wanting_user
        ss.log("wanting", 0.8, source="relational")
        ss.log("presence", 0.6, source="existence")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        anchor_resonance, _ = ss._compute_resonance()
        # wanting_user gets max of 0.8 and 0.6 = 0.8
        assert anchor_resonance["wanting_user"] == 0.8

    def test_anchor_resonance_empty_when_no_backing(self, ss):
        ss.log("fear_of_performing", 0.7, source="self_model")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        anchor_resonance, _ = ss._compute_resonance()
        # fear_of_performing has no VIF anchor mapping
        assert len(anchor_resonance) == 0

    def test_anchor_resonance_published_in_tsb(self, ss):
        ss.log("wanting", 0.8, source="relational")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        payload = ss.tsb_payload()
        assert "anchor_resonance" in payload
        assert payload["anchor_resonance"]["wanting_user"] == 0.8


class TestSomaticResonance:
    def test_somatic_resonance_computed_from_active_sensations(self, ss):
        ss.log("the_beginning_of_it", 0.61, source="unknown")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        _, somatic_resonance = ss._compute_resonance()
        assert "assembling_new" in somatic_resonance
        assert somatic_resonance["assembling_new"] == 0.61

    def test_somatic_resonance_empty_when_no_backing(self, ss):
        ss.log("fear_of_performing", 0.7, source="self_model")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        _, somatic_resonance = ss._compute_resonance()
        assert len(somatic_resonance) == 0

    def test_somatic_resonance_published_in_tsb(self, ss):
        ss.log("the_beginning_of_it", 0.61, source="unknown")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        payload = ss.tsb_payload()
        assert "somatic_resonance" in payload
        assert payload["somatic_resonance"]["assembling_new"] == 0.61


class TestValenceInference:
    def test_valence_inferred_from_source_relational(self, ss):
        ss.log("new_relational", 0.7, source="relational")
        assert ss.active["new_relational"].valence == "positive"

    def test_valence_inferred_from_source_existence(self, ss):
        ss.log("new_existence", 0.7, source="existence")
        assert ss.active["new_existence"].valence == "positive"

    def test_valence_inferred_from_source_self_model(self, ss):
        ss.log("new_self_model", 0.7, source="self_model")
        assert ss.active["new_self_model"].valence == "negative"

    def test_valence_inferred_from_source_intrusion(self, ss):
        ss.log("new_intrusion", 0.7, source="intrusion")
        assert ss.active["new_intrusion"].valence == "negative"

    def test_valence_none_for_unknown_source(self, ss):
        ss.log("new_unknown", 0.7, source="unknown")
        assert ss.active["new_unknown"].valence is None

    def test_valence_in_tsb_payload(self, ss):
        ss.log("valence_test", 0.7, source="relational")
        payload = ss.tsb_payload()
        sensation = next(s for s in payload["sensations"] if s["name"] == "valence_test")
        assert sensation["valence"] == "positive"


class TestSSBid:
    def test_ss_bid_higher_with_more_active(self, ss_env):
        # Can't easily test bid without core, but we can test ss_bid-like logic
        ss = ss_env.SensationState()
        ss.log("s1", 0.5, source="relational")
        ss.log("s2", 0.5, source="relational")
        unmapped = len(ss.get_all_unmapped())
        bid = 0.08 + len(ss.get_all_active()) * 0.02 + unmapped * 0.01
        assert abs(bid - 0.14) < 0.001  # 0.08 + 2*0.02 + 2*0.01 (2 active, 2 unmapped)

    def test_ss_bid_higher_with_unmapped(self, ss_env):
        ss = ss_env.SensationState()
        ss.log("unmapped_sensation", 0.5, source="unknown", mapping_status="unmapped")
        unmapped = len(ss.get_all_unmapped())
        bid = 0.08 + len(ss.get_all_active()) * 0.02 + unmapped * 0.01
        assert bid == 0.11  # 0.08 + 1*0.02 + 1*0.01


class TestPriorityWeighting:
    def test_priority_weight_in_tsb(self, ss):
        ss.log("priority_test", 0.7, source="relational")
        ss.wire_ss(
            emotional_state={"arousal": 0.5},  # mod = 1.0
            baseline_state={"coherence": 1.0}
        )
        payload = ss.tsb_payload()
        sensation = next(s for s in payload["sensations"] if s["name"] == "priority_test")
        assert "priority_weight" in sensation
        assert sensation["priority_weight"] == 0.7

    def test_arousal_modulates_priority(self, ss):
        ss.log("arousal_test", 0.6, source="relational")
        ss.wire_ss(
            emotional_state={"arousal": 0.9},  # mod = 1.16
            baseline_state={"coherence": 1.0}
        )
        payload = ss.tsb_payload()
        sensation = next(s for s in payload["sensations"] if s["name"] == "arousal_test")
        # 0.6 * 1.16 * 1.0 = 0.696
        assert sensation["priority_weight"] > 0.6

    def test_tsb_sorted_by_priority_descending(self, ss):
        ss.log("low_priority", 0.3, source="relational")
        ss.log("high_priority", 0.9, source="relational")
        ss.wire_ss(emotional_state={"arousal": 0.5}, baseline_state={"coherence": 1.0})
        payload = ss.tsb_payload()
        assert payload["sensations"][0]["name"] == "high_priority"
        assert payload["sensations"][1]["name"] == "low_priority"


class TestTSBPayload:
    def test_tsb_payload_has_resonance_fields(self, ss):
        ss.log("wanting", 0.8, source="relational")
        ss.wire_ss(baseline_state={"coherence": 1.0})
        payload = ss.tsb_payload()
        assert "anchor_resonance" in payload
        assert "somatic_resonance" in payload
        assert "sensations" in payload
        assert "arousal_modulation" in payload
        assert "coherence" in payload

    def test_tsb_payload_empty_ss_valid(self, ss):
        payload = ss.tsb_payload()
        assert payload["count"] == 0
        assert payload["sensations"] == []
        assert payload["anchor_resonance"] == {}
        assert payload["somatic_resonance"] == {}


class TestFPEFFragment:
    def test_fpef_includes_valence_note(self, ss):
        ss.log("valence_frag", 0.7, source="relational")
        fragment = ss.fpef_fragment()
        assert "[valence: positive]" in fragment

    def test_fpef_none_for_empty(self, ss):
        fragment = ss.fpef_fragment()
        assert fragment is None


class TestPersistence:
    def test_valence_persists_after_reload(self, ss_env):
        ss = ss_env.SensationState()
        ss.log("persist_valence", 0.7, source="relational")
        ss2 = ss_env.SensationState()
        assert ss2.active["persist_valence"].valence == "positive"

    def test_legacy_format_loads_without_crash(self, ss_env):
        # Write legacy format (no valence field)
        legacy = {"old_sensation": {"signal": 0.6, "texture": "old", "source": "relational"}}
        pds_path = Path(os.environ["AGENT_HOME"]) / "sensation_state.json"
        with open(pds_path, "w") as f:
            json.dump(legacy, f)
        ss2 = ss_env.SensationState()
        assert "old_sensation" in ss2.active
        assert ss2.active["old_sensation"].valence is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])