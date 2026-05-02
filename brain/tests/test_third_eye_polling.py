"""
Tests for the Third Eye salience-network polling layer in
brain.mechanisms.identity_proposal_writer.

Covers:
  - kind_to_domain mapping (memory_and_recall / voice_and_persona /
    outward_action / metacognition_and_self / other)
  - Single-wire fire writes a proposal + acknowledges the wire
  - Wires that don't have the IPW handshake methods are skipped
  - Convergence: 3+ wires firing in same domain → meta-proposal
    (single proposals for those wires are suppressed)
  - Dedup throttle: re-fire same kind within window → dropped
  - Below-confidence proposals dropped
  - reset_dedup_window clears throttle
  - Healthy wires (should_propose=False) are not polled
  - Stats payload shape
  - Acknowledged wires actually had acknowledge_proposal called
  - Multiple unrelated single-wire fires across different domains all land
"""
import time

import pytest


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "identity").mkdir(parents=True)
    state_dir = home / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    # PROPOSALS_PATH was bound at module import; rebind for this test.
    import brain.mechanisms.identity_proposal_writer as ipw_mod
    monkeypatch.setattr(
        ipw_mod, "PROPOSALS_PATH", home / "identity" / "PROPOSALS.md",
    )
    yield home


# ── Mock wire ────────────────────────────────────────────────────────────


class _MockWire:
    """A minimal wire that satisfies the IPW handshake. Used in the
    tests so we don't have to drive real mechanism state into a degraded
    region by proxy."""
    def __init__(self, kind, source, will_fire=True, score=0.30, count=10):
        self.kind = kind
        self.source = source
        self._will_fire = will_fire
        self._score = score
        self._count = count
        self._acknowledged = 0

    def should_propose_identity_update(self):
        return self._will_fire

    def proposed_identity_signal(self):
        return {
            "source": self.source,
            "kind": self.kind,
            "rolling_integrity_score": self._score,
            "consecutive_bad_ops": self._count,
            "dominant_failure_mode": "synthetic",
            "dominant_failure_count": self._count,
            "interpretation": f"synthetic drift signal from {self.source}",
        }

    def acknowledge_proposal(self):
        self._acknowledged += 1


def _read_proposals(home):
    p = home / "identity" / "PROPOSALS.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


# ── kind → domain map ────────────────────────────────────────────────────


def test_kind_to_domain_memory():
    from brain.mechanisms.identity_proposal_writer import kind_to_domain
    assert kind_to_domain("systematic_memory_drift") == "memory_and_recall"
    assert kind_to_domain("corpus_retrieval_drift") == "memory_and_recall"
    assert kind_to_domain("systematic_compression_drift") == "memory_and_recall"


def test_kind_to_domain_voice():
    from brain.mechanisms.identity_proposal_writer import kind_to_domain
    assert kind_to_domain("voice_drift") == "voice_and_persona"
    assert kind_to_domain("persona_coherence_drift") == "voice_and_persona"
    assert kind_to_domain("skill_discovery_drift") == "voice_and_persona"


def test_kind_to_domain_outward():
    from brain.mechanisms.identity_proposal_writer import kind_to_domain
    assert kind_to_domain("outward_reach_drift") == "outward_action"
    assert kind_to_domain("making_drift") == "outward_action"
    assert kind_to_domain("task_planning_drift") == "outward_action"
    assert kind_to_domain("report_generation_drift") == "outward_action"


def test_kind_to_domain_metacognition():
    from brain.mechanisms.identity_proposal_writer import kind_to_domain
    assert kind_to_domain("metacognition_drift") == "metacognition_and_self"
    assert kind_to_domain("self_revision_drift") == "metacognition_and_self"
    assert kind_to_domain("dwelling_drift") == "metacognition_and_self"


def test_kind_to_domain_unknown():
    from brain.mechanisms.identity_proposal_writer import kind_to_domain
    assert kind_to_domain("never_heard_of_this") == "other"


# ── single-wire fire ─────────────────────────────────────────────────────


def test_single_wire_fire_writes_proposal(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    wire = _MockWire(kind="systematic_memory_drift", source="MemoryIntegrityLayer")
    res = ipw.poll_wires({"MemoryIntegrityLayer": wire})

    assert res["ok"] is True
    assert res["raw_signals_n"] == 1
    assert res["proposals_written_n"] == 1
    assert res["single_proposals_n"] == 1
    assert res["convergence_proposals_n"] == 0
    assert res["acks"] == ["MemoryIntegrityLayer"]
    assert wire._acknowledged == 1
    text = _read_proposals(isolated)
    assert "MemoryIntegrityLayer" in text
    assert "PERSONALITY.md" in text


def test_wire_without_ipw_handshake_skipped(isolated):
    """Mechanisms that don't expose should_propose_identity_update are
    skipped (graceful degradation for older Phase 1/2 mechanisms)."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter

    class NoHandshake:
        pass

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"NoHandshake": NoHandshake()})
    assert res["raw_signals_n"] == 0
    assert res["proposals_written_n"] == 0


def test_healthy_wire_not_polled(isolated):
    """A wire whose should_propose returns False is read but not polled."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    wire = _MockWire(kind="systematic_memory_drift", source="X", will_fire=False)
    res = ipw.poll_wires({"X": wire})
    assert res["raw_signals_n"] == 0
    assert wire._acknowledged == 0


def test_wire_signal_returning_non_dict_skipped(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter

    class BadSignalWire:
        def should_propose_identity_update(self):
            return True
        def proposed_identity_signal(self):
            return "not a dict"
        def acknowledge_proposal(self):
            pass

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"X": BadSignalWire()})
    assert res["raw_signals_n"] == 0


def test_wire_should_propose_raising_skipped(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter

    class RaisingWire:
        def should_propose_identity_update(self):
            raise RuntimeError("boom")
        def proposed_identity_signal(self):
            return {"kind": "x", "source": "X"}
        def acknowledge_proposal(self):
            pass

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"X": RaisingWire()})
    assert res["raw_signals_n"] == 0


# ── convergence ──────────────────────────────────────────────────────────


def test_convergence_three_wires_same_domain(isolated):
    """3 wires firing on memory_and_recall → single meta-proposal,
    individual proposals suppressed (since they got rolled into the
    convergence)."""
    from brain.mechanisms.identity_proposal_writer import (
        IdentityProposalWriter, CONVERGENCE_THRESHOLD,
    )
    assert CONVERGENCE_THRESHOLD == 3  # this test relies on the value

    w1 = _MockWire("systematic_memory_drift", "MemoryIntegrityLayer")
    w2 = _MockWire("corpus_retrieval_drift", "CorpusRetrievalLayer")
    w3 = _MockWire("systematic_compression_drift", "CompressionFidelityLayer")

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({
        "MemoryIntegrityLayer": w1,
        "CorpusRetrievalLayer": w2,
        "CompressionFidelityLayer": w3,
    })

    assert res["raw_signals_n"] == 3
    assert res["convergence_proposals_n"] == 1
    assert res["single_proposals_n"] == 0
    assert res["proposals_written_n"] == 1
    # Every wire got acknowledged.
    assert w1._acknowledged == 1
    assert w2._acknowledged == 1
    assert w3._acknowledged == 1
    text = _read_proposals(isolated)
    assert "Convergent salience signal" in text
    assert "memory_and_recall" in text


def test_convergence_two_wires_below_threshold(isolated):
    """2 wires same domain → still 2 single proposals (under threshold)."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    w1 = _MockWire("systematic_memory_drift", "MemoryIntegrityLayer")
    w2 = _MockWire("corpus_retrieval_drift", "CorpusRetrievalLayer")
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MIL": w1, "CRL": w2})
    assert res["convergence_proposals_n"] == 0
    assert res["single_proposals_n"] == 2
    assert w1._acknowledged == 1
    assert w2._acknowledged == 1


def test_convergence_metacognition_targets_identity(isolated):
    """Convergence in metacognition_and_self domain → target = identity
    (other domains target = personality)."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    w1 = _MockWire("metacognition_drift", "SelfAnalysisLayer")
    w2 = _MockWire("self_revision_drift", "SelfRevisionLayer")
    w3 = _MockWire("dwelling_drift", "DwellingLayer")
    ipw = IdentityProposalWriter()
    ipw.poll_wires({"SAL": w1, "SRL": w2, "DWL": w3})
    text = _read_proposals(isolated)
    # The convergence proposal should target IDENTITY.md.
    assert "IDENTITY.md" in text


def test_mixed_domains_some_converge_some_dont(isolated):
    """3 wires in memory domain (converge) + 1 wire in voice (single)."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    w_mem1 = _MockWire("systematic_memory_drift", "MIL")
    w_mem2 = _MockWire("corpus_retrieval_drift", "CRL")
    w_mem3 = _MockWire("systematic_compression_drift", "CFL")
    w_voice = _MockWire("voice_drift", "VIL")

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({
        "MIL": w_mem1, "CRL": w_mem2, "CFL": w_mem3, "VIL": w_voice,
    })
    assert res["convergence_proposals_n"] == 1  # memory
    assert res["single_proposals_n"] == 1       # voice
    assert res["proposals_written_n"] == 2


# ── dedup throttle ───────────────────────────────────────────────────────


def test_dedup_same_kind_within_window_dropped(isolated):
    """Re-fire same kind immediately → throttled."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    wire = _MockWire("systematic_memory_drift", "MIL")

    r1 = ipw.poll_wires({"MIL": wire})
    assert r1["proposals_written_n"] == 1

    r2 = ipw.poll_wires({"MIL": wire})
    assert r2["raw_signals_n"] == 1
    assert r2["throttled_n"] == 1
    assert r2["proposals_written_n"] == 0


def test_reset_dedup_window_clears_throttle(isolated):
    """Operator hook lets the next poll re-fire."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    wire = _MockWire("systematic_memory_drift", "MIL")

    ipw.poll_wires({"MIL": wire})
    ipw.reset_dedup_window()
    r = ipw.poll_wires({"MIL": wire})
    assert r["proposals_written_n"] == 1


def test_dedup_persists_across_instances(isolated):
    """Throttle survives a re-instantiation of IdentityProposalWriter."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw1 = IdentityProposalWriter()
    wire = _MockWire("systematic_memory_drift", "MIL")
    ipw1.poll_wires({"MIL": wire})

    # Fresh instance — should still see the throttle from disk.
    ipw2 = IdentityProposalWriter()
    r = ipw2.poll_wires({"MIL": wire})
    assert r["proposals_written_n"] == 0


# ── confidence floor ─────────────────────────────────────────────────────


def test_confidence_floor_drops_proposals(isolated):
    """A signal whose computed confidence is below the floor is not written."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    # Wire with a HIGH integrity score → low computed confidence (1 - 0.95 + 0.5 = 0.55)
    wire = _MockWire("systematic_memory_drift", "MIL", score=0.95)
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MIL": wire}, confidence_floor=0.7)
    # Computed confidence should be below floor.
    assert res["proposals_written_n"] == 0


def test_explicit_confidence_floor_override(isolated):
    """Caller can lower the floor for a poll."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    wire = _MockWire("systematic_memory_drift", "MIL", score=0.95)
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MIL": wire}, confidence_floor=0.4)
    assert res["proposals_written_n"] == 1


# ── stats payload ────────────────────────────────────────────────────────


def test_stats_payload_has_required_keys(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({})
    required = {
        "ok", "raw_signals_n", "throttled_n", "proposals_written_n",
        "convergence_proposals_n", "single_proposals_n", "acks", "proposals",
    }
    assert required.issubset(res.keys())


def test_empty_mechanism_dict(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({})
    assert res["ok"] is True
    assert res["raw_signals_n"] == 0
    assert res["proposals_written_n"] == 0


def test_none_mechanism_skipped(isolated):
    """None values in the mechanisms dict are ignored without crashing."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"DeadWire": None})
    assert res["raw_signals_n"] == 0


# ── live wire integration ────────────────────────────────────────────────


def test_polls_real_mechanism_in_systematic_low_state(isolated):
    """Round-trip with an actual wire instance — drive it into low integrity
    via record_operation and confirm the Third Eye picks it up."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer

    mil = MemoryIntegrityLayer()
    for _ in range(10):
        mil.record_operation("teleport", target="x")
    assert mil.is_systematically_low_integrity() is True
    assert mil.should_propose_identity_update() is True

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MemoryIntegrityLayer": mil})
    assert res["proposals_written_n"] == 1
    # Mechanism's acknowledged_at_bad_ops should now be set.
    assert mil.state.get("acknowledged_at_bad_ops", 0) > 0


# ── per-domain behavior ──────────────────────────────────────────────────


def test_other_domain_signals_pass_through_as_singles(isolated):
    """Signals with unknown kind (domain='other') are still written
    as single proposals — they just don't participate in convergence."""
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    w = _MockWire("totally_new_kind_not_mapped", "WeirdLayer")
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"WeirdLayer": w})
    assert res["single_proposals_n"] == 1
    assert res["convergence_proposals_n"] == 0


def test_proposal_record_shape_single(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    w = _MockWire("systematic_memory_drift", "MIL")
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MIL": w})
    p = res["proposals"][0]
    assert p["kind"] == "single"
    assert p["source"] == "MIL"
    assert p["target"] == "personality"
    assert "confidence" in p


def test_proposal_record_shape_convergence(isolated):
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ws = [
        _MockWire("systematic_memory_drift", "MIL"),
        _MockWire("corpus_retrieval_drift", "CRL"),
        _MockWire("systematic_compression_drift", "CFL"),
    ]
    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({"MIL": ws[0], "CRL": ws[1], "CFL": ws[2]})
    p = res["proposals"][0]
    assert p["kind"] == "convergence"
    assert p["domain"] == "memory_and_recall"
    assert p["convergence_count"] == 3
    assert "MIL" in p["sources"]
    assert "CRL" in p["sources"]
    assert "CFL" in p["sources"]
