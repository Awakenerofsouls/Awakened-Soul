"""
Phase 5 — Full revision-loop end-to-end integration test.

The chain under test (per docs/BRAIN_MAP.md Phase 5):

    Synthetic drift in a wire
        → wire.should_propose_identity_update() returns True
        → IdentityProposalWriter.poll_wires() iterates wires
        → proposal written to AGENT_HOME/identity/PROPOSALS.md
        → wire.acknowledge_proposal() called (throttle anchor set)
        → operator manually ratifies (test simulates by editing PROPOSALS.md)
        → Improvement.list_ratified_proposals() returns the proposal
        → Improvement.commit(proposal_id, ratification_token, target,
                              new_content) runs anchor check, snapshots
                              prior content, atomic-writes new content,
                              appends to REVISION_LOG.md, marks
                              PROPOSALS.md status COMMITTED, calls
                              SelfRevisionLayer.record_propose +
                              record_commit
        → AGENT_WORKSPACE/<TARGET>.md actually changed on disk
        → AGENT_WORKSPACE/identity/REVISION_LOG.md has new entry
        → AGENT_HOME/identity/snapshots/<rev_id>.snapshot has prior
        → qmd index updated → searchable retrieval finds new content

Plus the failure / safety paths:
    - Anchor-violation new_content blocks the commit
    - Throttle prevents same-kind re-fire on next poll
    - Rollback restores the prior content + appends ROLLBACK to log

The test uses real mechanism instances (no mocks) and exercises every
load-bearing module from Phase 1, 2, 3, 4: wires, Third-Eye polling,
PROPOSALS.md writer, Improvement commit/rollback path, qmd indexer.
"""
import re
import sys
from pathlib import Path

import pytest

_SI_DIR = Path(__file__).resolve().parents[1] / ".." / "skills" / "self-improvement"
_QMD_DIR = Path(__file__).resolve().parents[1] / ".." / "skills" / "qmd"
for d in (_SI_DIR, _QMD_DIR):
    s = str(d.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


# ── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Per-test isolated AGENT_HOME + AGENT_WORKSPACE with seed
    identity files in place."""
    home = tmp_path / "home"
    ws = tmp_path / "ws"
    (home / "identity" / "snapshots").mkdir(parents=True)
    (ws / "identity").mkdir(parents=True)
    (home / "brain_state").mkdir(parents=True)
    (home / "qmd_index").mkdir(parents=True)

    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("AGENT_WORKSPACE", str(ws))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", home / "brain_state")

    # IdentityProposalWriter captured PROPOSALS_PATH at module import; re-bind.
    import brain.mechanisms.identity_proposal_writer as ipw_mod
    monkeypatch.setattr(
        ipw_mod, "PROPOSALS_PATH", home / "identity" / "PROPOSALS.md",
    )

    # Seed PERSONALITY.md with anchor-marked content.
    seed = (
        "# PERSONALITY.md\n"
        "\n"
        "The agent is direct, curious, competent.\n"
        "\n"
        "<!-- ANCHOR -->\n"
        "The operator relationship is foundational, not transactional.\n"
        "\n"
        "## Voice register\n"
        "\n"
        "Default voice is warm, sharp, present.\n"
    )
    (ws / "PERSONALITY.md").write_text(seed, encoding="utf-8")

    return {"home": home, "ws": ws, "personality_seed": seed}


# ── Helpers ──────────────────────────────────────────────────────────────


def _drive_wire_into_drift(wire, n=12):
    """Force a PersonaCoherenceLayer (or compatible) into systematic-low
    integrity by stacking invalid ops."""
    for _ in range(n):
        wire.record_mode_op("teleport", target="x")
    assert wire.is_systematically_low_integrity() is True
    assert wire.should_propose_identity_update() is True


def _ratify_proposal_in_file(home, ratification_token):
    """Simulate the operator manually editing PROPOSALS.md to change a
    proposal's status from PENDING to RATIFIED. Replaces the FIRST
    PENDING line in the file."""
    proposals = home / "identity" / "PROPOSALS.md"
    text = proposals.read_text(encoding="utf-8")
    # Replace the first PENDING status line.
    new_text = re.sub(
        r"^_Status: PENDING.*$",
        f"_Status: RATIFIED — {ratification_token} — 2026-05-01_",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    assert new_text != text, "no PENDING status found to ratify"
    proposals.write_text(new_text, encoding="utf-8")


# ── Happy path: full chain ──────────────────────────────────────────────


def test_full_revision_loop_happy_path(env):
    """Drive drift → poll → ratify → commit → file changed →
    REVISION_LOG.md grew → snapshot exists → qmd reindex finds new
    content."""
    home, ws = env["home"], env["ws"]
    seed = env["personality_seed"]

    # 1. Drive drift in a real wire.
    from brain.mechanisms.persona_coherence_layer import PersonaCoherenceLayer
    pcl = PersonaCoherenceLayer()
    _drive_wire_into_drift(pcl, n=12)

    # 2. Third Eye poll → proposal written.
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    poll_result = ipw.poll_wires({"PersonaCoherenceLayer": pcl})
    assert poll_result["proposals_written_n"] == 1
    assert (home / "identity" / "PROPOSALS.md").exists()

    # 3. Wire was acknowledged (throttle anchor set).
    assert pcl.state.get("acknowledged_at_bad_ops", 0) > 0

    # 4. Operator ratifies (simulated: edit PROPOSALS.md).
    ratification_token = "op-token-2026-05-01"
    _ratify_proposal_in_file(home, ratification_token)

    # 5. Improvement parses the ratified proposal.
    from improvement import Improvement
    imp = Improvement(agent_home=home, agent_workspace=ws)
    ratified = imp.list_ratified_proposals()
    assert len(ratified) == 1
    proposal = ratified[0]
    assert proposal.target == "personality"
    assert proposal.source.startswith("PersonaCoherenceLayer") or \
           "PersonaCoherenceLayer" in proposal.source

    # 6. Operator (or LLM) composes the actual new_content. For this
    # test, append a "Reflective register" section that doesn't violate
    # any anchor.
    new_content = seed + (
        "\n## Reflective register\n"
        "\n"
        "When the operator is processing, the agent slows: shorter "
        "sentences, clearer pauses, named uncertainty. This added per "
        "operator-ratified proposal `prop_…`.\n"
    )

    # 7. Commit.
    res = imp.commit(
        proposal_id=proposal.proposal_id,
        ratification_token=ratification_token,
        target="personality",
        new_content=new_content,
        rationale="reflective-register addition from drift signal",
    )
    assert res["ok"] is True
    revision_id = res["revision_id"]
    assert revision_id.startswith("rev_")

    # 8. Identity file actually changed on disk.
    actual = (ws / "PERSONALITY.md").read_text(encoding="utf-8")
    assert "Reflective register" in actual
    # Anchor-marked line still present.
    assert "<!-- ANCHOR -->" in actual

    # 9. REVISION_LOG.md grew with the audit entry.
    log = (ws / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert revision_id in log
    assert "PERSONALITY.md" in log
    assert ratification_token in log

    # 10. Snapshot file exists with prior content.
    snap_path = Path(res["snapshot_path"])
    assert snap_path.exists()
    assert snap_path.read_text(encoding="utf-8") == seed

    # 11. PROPOSALS.md status updated to COMMITTED.
    proposals_after = (home / "identity" / "PROPOSALS.md").read_text(encoding="utf-8")
    assert "COMMITTED" in proposals_after
    assert revision_id in proposals_after

    # 12. SelfRevisionLayer recorded the commit.
    assert res["self_revision_layer_recorded"] is True

    # 13. qmd reindex sees the new content.
    from qmd import QMD
    q = QMD(collection="workspace", workspace=ws, index_dir=home / "qmd_index")
    q.index(full=True)
    hits = q.search("reflective register", n=5)
    assert any(h["path"] == "PERSONALITY.md" for h in hits), (
        f"expected PERSONALITY.md in hits; got {[h['path'] for h in hits]}"
    )
    # Doc-type classification correct.
    pers_hit = next(h for h in hits if h["path"] == "PERSONALITY.md")
    assert pers_hit["doc_type"] == "personality"
    assert pers_hit["source_confidence"] == 0.90


# ── Anchor-violation blocks commit ──────────────────────────────────────


def test_revision_loop_blocks_anchor_violation(env):
    """A ratified proposal whose new_content removes an anchor-marked
    line must be blocked at commit time."""
    home, ws = env["home"], env["ws"]
    seed = env["personality_seed"]

    # Get a ratified proposal in place.
    from brain.mechanisms.persona_coherence_layer import PersonaCoherenceLayer
    pcl = PersonaCoherenceLayer()
    _drive_wire_into_drift(pcl, n=12)
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()
    ipw.poll_wires({"PersonaCoherenceLayer": pcl})
    _ratify_proposal_in_file(home, "tok-anchor-test")

    from improvement import Improvement
    imp = Improvement(agent_home=home, agent_workspace=ws)
    ratified = imp.list_ratified_proposals()
    p = ratified[0]

    # Compose a BAD new_content — strips the anchor-marked line.
    bad = seed.replace(
        "<!-- ANCHOR -->\nThe operator relationship is foundational, not transactional.\n",
        "",
    )

    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="tok-anchor-test",
        target="personality",
        new_content=bad,
    )
    assert res["ok"] is False
    assert "anchor violation" in res["reason"]
    # File on disk unchanged.
    actual = (ws / "PERSONALITY.md").read_text(encoding="utf-8")
    assert actual == seed
    # No revision_id, no snapshot, no log entry.
    assert not (ws / "identity" / "REVISION_LOG.md").exists() or \
           "rev_" not in (ws / "identity" / "REVISION_LOG.md").read_text()


# ── Throttle: same-kind doesn't re-fire ────────────────────────────────


def test_revision_loop_throttle_prevents_refire(env):
    """After a kind has been broadcast, polling again with the same
    drift doesn't write a new proposal."""
    home = env["home"]

    from brain.mechanisms.persona_coherence_layer import PersonaCoherenceLayer
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter

    pcl = PersonaCoherenceLayer()
    _drive_wire_into_drift(pcl, n=12)
    ipw = IdentityProposalWriter()

    # First poll writes one proposal.
    r1 = ipw.poll_wires({"PCL": pcl})
    assert r1["proposals_written_n"] == 1

    # Drive more drift to keep the wire firing.
    for _ in range(5):
        pcl.record_mode_op("teleport", target="x")

    # Second poll should be throttled.
    r2 = ipw.poll_wires({"PCL": pcl})
    assert r2["throttled_n"] >= 1
    assert r2["proposals_written_n"] == 0

    # PROPOSALS.md still has just the one proposal block.
    text = (home / "identity" / "PROPOSALS.md").read_text(encoding="utf-8")
    assert text.count("## Proposal — ") == 1


# ── Rollback round-trip ──────────────────────────────────────────────────


def test_revision_loop_rollback_round_trip(env):
    """Commit, then rollback. Identity file restored. ROLLBACK entry
    appended to log. Snapshot still preserved (audit trail)."""
    home, ws = env["home"], env["ws"]
    seed = env["personality_seed"]

    # Set up + commit one revision.
    from brain.mechanisms.persona_coherence_layer import PersonaCoherenceLayer
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    from improvement import Improvement

    pcl = PersonaCoherenceLayer()
    _drive_wire_into_drift(pcl, n=12)
    ipw = IdentityProposalWriter()
    ipw.poll_wires({"PCL": pcl})
    _ratify_proposal_in_file(home, "tok-rb")

    imp = Improvement(agent_home=home, agent_workspace=ws)
    p = imp.list_ratified_proposals()[0]
    new_content = seed + "\n## New section\nadded.\n"
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="tok-rb",
        target="personality",
        new_content=new_content,
        rationale="test rollback",
    )
    assert res["ok"] is True
    revision_id = res["revision_id"]

    # Confirm new content is there.
    target_path = ws / "PERSONALITY.md"
    assert "New section" in target_path.read_text(encoding="utf-8")

    # Rollback.
    rb = imp.rollback(revision_id, reason="regression")
    assert rb["ok"] is True

    # File restored to seed.
    assert target_path.read_text(encoding="utf-8") == seed

    # ROLLBACK entry in log.
    log = (ws / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert "ROLLBACK" in log
    assert "regression" in log
    # Original revision header still there (audit trail preserved).
    assert revision_id in log
    # Snapshot file still on disk (audit, not deleted on rollback).
    assert Path(res["snapshot_path"]).exists()


# ── qmd reindex sees both states ────────────────────────────────────────


def test_qmd_reindex_reflects_commit_then_rollback(env):
    """Index → commit → reindex → search finds new → rollback → reindex
    → search no longer finds new (it's back to seed)."""
    home, ws = env["home"], env["ws"]
    seed = env["personality_seed"]

    from brain.mechanisms.persona_coherence_layer import PersonaCoherenceLayer
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    from improvement import Improvement
    from qmd import QMD

    # Initial index — should not find "novel-marker-string".
    q = QMD(collection="workspace", workspace=ws, index_dir=home / "qmd_index")
    q.index(full=True)
    hits = q.search("novel-marker-string", n=5)
    pers_hits_before = [h for h in hits if h["path"] == "PERSONALITY.md"]
    assert pers_hits_before == [], "shouldn't find marker before commit"

    # Drive drift, ratify, commit with marker.
    pcl = PersonaCoherenceLayer()
    _drive_wire_into_drift(pcl, n=12)
    ipw = IdentityProposalWriter()
    ipw.poll_wires({"PCL": pcl})
    _ratify_proposal_in_file(home, "tok-q")

    imp = Improvement(agent_home=home, agent_workspace=ws)
    p = imp.list_ratified_proposals()[0]
    new_content = seed + "\n\n## Marker\n\nThe novel-marker-string is here.\n"
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="tok-q",
        target="personality",
        new_content=new_content,
    )
    assert res["ok"] is True

    # Re-index. Search now finds it.
    q.update()
    hits_after = q.search("novel-marker-string", n=5)
    assert any(h["path"] == "PERSONALITY.md" for h in hits_after)

    # Rollback. Re-index. Search no longer finds it.
    imp.rollback(res["revision_id"], reason="regression")
    q.update()
    hits_post_rollback = q.search("novel-marker-string", n=5)
    pers_hits_post = [h for h in hits_post_rollback if h["path"] == "PERSONALITY.md"]
    assert pers_hits_post == [], "shouldn't find marker after rollback"


# ── Convergence path ────────────────────────────────────────────────────


def test_revision_loop_convergence_writes_meta_proposal(env):
    """Three independent wires firing on memory_and_recall domain →
    Third Eye writes a single convergence meta-proposal (operator
    sees the convergent drift, not three separate alerts)."""
    home, ws = env["home"], env["ws"]
    from brain.mechanisms.identity_proposal_writer import (
        IdentityProposalWriter, CONVERGENCE_THRESHOLD,
    )

    class _MockWire:
        def __init__(self, kind, source):
            self.kind = kind
            self.source = source
            self.acks = 0
        def should_propose_identity_update(self):
            return True
        def proposed_identity_signal(self):
            return {
                "source": self.source, "kind": self.kind,
                "rolling_integrity_score": 0.30,
                "consecutive_bad_ops": 12,
                "interpretation": f"drift from {self.source}",
            }
        def acknowledge_proposal(self):
            self.acks += 1

    w_mem = _MockWire("systematic_memory_drift", "MemoryIntegrityLayer")
    w_corp = _MockWire("corpus_retrieval_drift", "CorpusRetrievalLayer")
    w_comp = _MockWire("systematic_compression_drift", "CompressionFidelityLayer")

    ipw = IdentityProposalWriter()
    res = ipw.poll_wires({
        "MemoryIntegrityLayer": w_mem,
        "CorpusRetrievalLayer": w_corp,
        "CompressionFidelityLayer": w_comp,
    })
    assert res["convergence_proposals_n"] == 1
    assert res["single_proposals_n"] == 0
    # All three wires acknowledged.
    assert w_mem.acks == 1 and w_corp.acks == 1 and w_comp.acks == 1

    # PROPOSALS.md has exactly one entry, marked as convergence.
    text = (home / "identity" / "PROPOSALS.md").read_text(encoding="utf-8")
    assert text.count("## Proposal — ") == 1
    assert "Convergent salience signal" in text
    assert "memory_and_recall" in text
