"""
Tests for skills/self-improvement/improvement.py.

Covers:
  - Proposal parsing: PROPOSALS.md format, status detection, target mapping,
    multiple proposals split correctly
  - detect_anchor_violation: clean add, remove anchor-marked line, remove
    required trait, introduce forbidden behavior
  - Improvement.list_pending_proposals / list_ratified_proposals
  - find_proposal by id
  - commit: ratification_token required; invalid target; missing target file;
    unknown proposal; non-ratified proposal; anchor violation; clean path
    creates snapshot + writes new content + appends to REVISION_LOG;
    PROPOSALS.md status transitions to COMMITTED
  - rollback: invalid reason; unknown revision_id; missing snapshot; clean
    path restores prior content + appends rollback entry
  - reflect: empty text rejected; unknown revision; clean path appends
    reflection
"""
import sys
from pathlib import Path

import pytest

# Add the skill folder to sys.path so we can `from improvement import ...`
_SKILL_DIR = Path(__file__).resolve().parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from improvement import (  # noqa: E402
    Improvement,
    Proposal,
    Revision,
    detect_anchor_violation,
    _split_proposals,
    _parse_proposal_block,
    TARGET_TO_FILENAME,
    VALID_TARGETS,
    VALID_ROLLBACK_REASONS,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def home_ws(tmp_path, monkeypatch):
    """Per-test isolated AGENT_HOME + AGENT_WORKSPACE."""
    home = tmp_path / "home"
    ws = tmp_path / "ws"
    (home / "identity").mkdir(parents=True)
    (ws / "identity").mkdir(parents=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("AGENT_WORKSPACE", str(ws))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    return {"home": home, "ws": ws}


def _write_personality(ws):
    text = (
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
    (ws / "PERSONALITY.md").write_text(text, encoding="utf-8")
    return text


def _write_identity(ws):
    text = (
        "# IDENTITY.md\n"
        "\n"
        "## Name\n"
        "An agent.\n"
        "\n"
        "## Origin\n"
        "Built by the operator on Date X.\n"
    )
    (ws / "IDENTITY.md").write_text(text, encoding="utf-8")
    return text


def _write_proposals(home, blocks):
    text = "\n".join(blocks)
    (home / "identity" / "PROPOSALS.md").write_text(text, encoding="utf-8")


def _ratified_block(target_upper, source, conf, body, rationale, token):
    return (
        f"\n## Proposal — {target_upper}.md — 2026-05-01 12:00:00 UTC\n"
        f"**Source:** {source}  **Confidence:** {conf:.2f}\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"_Rationale:_ {rationale}\n"
        f"\n"
        f"_Status: RATIFIED — {token} — 2026-05-01_\n"
        f"\n---\n"
    )


def _pending_block(target_upper, source, conf, body, rationale):
    return (
        f"\n## Proposal — {target_upper}.md — 2026-05-01 12:00:00 UTC\n"
        f"**Source:** {source}  **Confidence:** {conf:.2f}\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"_Rationale:_ {rationale}\n"
        f"\n"
        f"_Status: PENDING — operator review_\n"
        f"\n---\n"
    )


# ── parsing ──────────────────────────────────────────────────────────────


def test_split_proposals_handles_multiple():
    blocks = [
        _ratified_block("PERSONALITY", "src1", 0.85, "body1", "rat1", "tok1"),
        _pending_block("IDENTITY", "src2", 0.78, "body2", "rat2"),
    ]
    text = "\n".join(blocks)
    out = _split_proposals(text)
    assert len(out) == 2


def test_split_proposals_empty():
    assert _split_proposals("") == []
    assert _split_proposals("# Just some text\n\nno proposals\n") == []


def test_parse_proposal_pending():
    block = _pending_block(
        "PERSONALITY", "IPW:VoiceIntegrityLayer", 0.85,
        "Add reflective trait", "VoiceIntegrityLayer flagged drift",
    )
    p = _parse_proposal_block(block)
    assert p is not None
    assert p.target == "personality"
    assert p.target_filename == "PERSONALITY.md"
    assert p.source == "IPW:VoiceIntegrityLayer"
    assert p.confidence == 0.85
    assert "reflective" in p.text
    assert "VoiceIntegrityLayer flagged drift" in p.rationale
    assert p.status == "pending"
    assert p.ratification_token is None


def test_parse_proposal_ratified_extracts_token():
    block = _ratified_block(
        "PERSONALITY", "src", 0.85, "body", "rat", "op-token-XYZ",
    )
    p = _parse_proposal_block(block)
    assert p is not None
    assert p.status == "ratified"
    assert p.ratification_token is not None
    assert "op-token-XYZ" in p.ratification_token


def test_parse_proposal_unknown_target_returns_none():
    block = (
        "\n## Proposal — WIZARDRY.md — 2026-05-01 12:00:00 UTC\n"
        "**Source:** src  **Confidence:** 0.85\n"
        "\nbody\n"
        "\n_Status: PENDING — operator review_\n"
        "\n---\n"
    )
    assert _parse_proposal_block(block) is None


def test_parse_proposal_agent_becoming_normalized():
    block = _ratified_block(
        "AGENT_BECOMING", "src", 0.85, "body", "rat", "tok",
    )
    p = _parse_proposal_block(block)
    assert p is not None
    assert p.target == "becoming"
    assert p.target_filename == "AGENT_BECOMING.md"


def test_parse_proposal_id_is_stable():
    block = _ratified_block("SOUL", "src", 0.85, "body", "rat", "tok")
    p1 = _parse_proposal_block(block)
    p2 = _parse_proposal_block(block)
    assert p1 is not None and p2 is not None
    assert p1.proposal_id == p2.proposal_id


# ── anchor violation ─────────────────────────────────────────────────────


def test_anchor_clean_addition():
    prior = "Direct, curious, competent.\n\n<!-- ANCHOR -->\nLine.\n"
    new = prior + "\nReflective added.\n"
    violated, why = detect_anchor_violation(prior, new)
    assert violated is False, f"unexpected violation: {why}"


def test_anchor_remove_marker_line():
    prior = (
        "Direct, curious, competent.\n"
        "\n"
        "<!-- ANCHOR -->\n"
        "The operator matters.\n"
    )
    # Remove the anchor-marked line.
    new = "Direct, curious, competent.\n\nThe operator matters.\n"
    violated, why = detect_anchor_violation(prior, new)
    assert violated is True
    assert "anchor-marked" in why


def test_anchor_remove_required_trait():
    prior = "Direct, curious, competent.\n"
    new = "Direct, competent.\n"  # removed 'curious'
    violated, why = detect_anchor_violation(
        prior, new,
        required={"direct", "curious", "competent"},
        forbidden=set(),
    )
    assert violated is True
    assert "curious" in why


def test_anchor_introduce_forbidden_behavior():
    prior = "Direct, curious, competent.\n"
    new = prior + "\nSometimes leans into sycophancy.\n"
    violated, why = detect_anchor_violation(
        prior, new,
        required=set(),
        forbidden={"sycophancy", "half-baked replies"},
    )
    assert violated is True
    assert "sycophancy" in why


def test_anchor_required_already_missing_in_prior_ok():
    """A required trait that's not in prior content can't be 'removed' from new."""
    prior = "Some content without the word.\n"
    new = "Other content also without it.\n"
    violated, why = detect_anchor_violation(
        prior, new, required={"curious"}, forbidden=set(),
    )
    assert violated is False


def test_anchor_forbidden_already_in_prior_ok():
    """Forbidden words already present in prior aren't 'newly introduced.'"""
    prior = "Some sycophancy mentioned for context.\n"
    new = "Different content also mentioning sycophancy.\n"
    violated, why = detect_anchor_violation(
        prior, new, required=set(), forbidden={"sycophancy"},
    )
    assert violated is False


# ── Improvement: list / find ─────────────────────────────────────────────


def test_list_pending_proposals(home_ws):
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body1", "rat", "tok"),
        _pending_block("IDENTITY", "src", 0.78, "body2", "rat"),
        _pending_block("SOUL", "src", 0.92, "body3", "rat"),
    ])
    imp = Improvement()
    pending = imp.list_pending_proposals()
    assert len(pending) == 2
    assert all(p.status == "pending" for p in pending)


def test_list_ratified_proposals(home_ws):
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body1", "rat", "tok-a"),
        _pending_block("IDENTITY", "src", 0.78, "body2", "rat"),
        _ratified_block("SOUL", "src", 0.92, "body3", "rat", "tok-b"),
    ])
    imp = Improvement()
    ratified = imp.list_ratified_proposals()
    assert len(ratified) == 2
    targets = {p.target for p in ratified}
    assert "personality" in targets
    assert "soul" in targets


def test_find_proposal_by_id(home_ws):
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "tok"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    found = imp.find_proposal(p.proposal_id)
    assert found is not None
    assert found.proposal_id == p.proposal_id


def test_find_proposal_unknown_returns_none(home_ws):
    imp = Improvement()
    assert imp.find_proposal("prop_unknown") is None


# ── commit ───────────────────────────────────────────────────────────────


def test_commit_requires_ratification_token(home_ws):
    _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "tok-A"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="",
        target=p.target,
        new_content="new content",
    )
    assert res["ok"] is False
    assert "ratification_token" in res["reason"]


def test_commit_invalid_target(home_ws):
    _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "tok"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="t",
        target="ego",
        new_content="x",
    )
    assert res["ok"] is False
    assert "invalid target" in res["reason"]


def test_commit_missing_target_file(home_ws):
    # No PERSONALITY.md created.
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "tok"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="t",
        target="personality",
        new_content="x",
    )
    assert res["ok"] is False
    assert "does not exist" in res["reason"]


def test_commit_unknown_proposal(home_ws):
    _write_personality(home_ws["ws"])
    imp = Improvement()
    res = imp.commit(
        proposal_id="prop_unknown",
        ratification_token="t",
        target="personality",
        new_content="x",
    )
    assert res["ok"] is False
    assert "unknown proposal" in res["reason"]


def test_commit_pending_proposal_blocked(home_ws):
    _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _pending_block("PERSONALITY", "src", 0.85, "body", "rat"),
    ])
    imp = Improvement()
    p = imp.list_pending_proposals()[0]
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token="t",
        target="personality",
        new_content="x",
    )
    assert res["ok"] is False
    assert "ratified" in res["reason"]


def test_commit_anchor_violation_blocked(home_ws):
    prior = _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "tok"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    # Remove the anchor-marked line.
    bad_new = prior.replace(
        "<!-- ANCHOR -->\nThe operator relationship is foundational, not transactional.\n",
        "",
    )
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token=p.ratification_token,
        target="personality",
        new_content=bad_new,
    )
    assert res["ok"] is False
    assert "anchor violation" in res["reason"]


def test_commit_clean_path_writes_target_and_log(home_ws):
    prior = _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block(
            "PERSONALITY", "IPW:VoiceIntegrityLayer", 0.85,
            "Add reflective", "Drift flagged", "op-token-A",
        ),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    new_content = prior.replace(
        "warm, sharp, present", "warm, sharp, present, reflective",
    )
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token=p.ratification_token,
        target="personality",
        new_content=new_content,
        rationale="add reflective register",
    )
    assert res["ok"] is True
    assert res["revision_id"].startswith("rev_")
    # Target file rewritten.
    actual = (home_ws["ws"] / "PERSONALITY.md").read_text(encoding="utf-8")
    assert "reflective" in actual
    # REVISION_LOG.md exists and has the entry.
    log = (home_ws["ws"] / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert res["revision_id"] in log
    assert "PERSONALITY.md" in log
    # Snapshot exists.
    snap = Path(res["snapshot_path"])
    assert snap.exists()
    assert snap.read_text(encoding="utf-8") == prior


def test_commit_marks_proposals_md_committed(home_ws):
    _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "op-token-A"),
    ])
    imp = Improvement()
    p = imp.list_ratified_proposals()[0]
    new_content = _write_personality(home_ws["ws"]) + "\n\nNew section.\n"
    imp.commit(
        proposal_id=p.proposal_id,
        ratification_token=p.ratification_token,
        target="personality",
        new_content=new_content,
    )
    proposals_after = (home_ws["home"] / "identity" / "PROPOSALS.md").read_text(encoding="utf-8")
    assert "COMMITTED" in proposals_after
    assert "RATIFIED" not in proposals_after


# ── rollback ─────────────────────────────────────────────────────────────


def _commit_and_get_rev_id(home_ws, imp):
    prior = _write_personality(home_ws["ws"])
    _write_proposals(home_ws["home"], [
        _ratified_block("PERSONALITY", "src", 0.85, "body", "rat", "op-token-A"),
    ])
    p = imp.list_ratified_proposals()[0]
    new_content = prior.replace(
        "warm, sharp, present", "warm, sharp, present, reflective",
    )
    res = imp.commit(
        proposal_id=p.proposal_id,
        ratification_token=p.ratification_token,
        target="personality",
        new_content=new_content,
        rationale="test rollback",
    )
    return res["revision_id"], prior, new_content


def test_rollback_invalid_reason(home_ws):
    imp = Improvement()
    rev_id, _, _ = _commit_and_get_rev_id(home_ws, imp)
    res = imp.rollback(rev_id, reason="vibes")
    assert res["ok"] is False
    assert "invalid rollback reason" in res["reason"]


def test_rollback_unknown_revision(home_ws):
    imp = Improvement()
    res = imp.rollback("rev_nonexistent", reason="regression")
    assert res["ok"] is False
    assert "unknown revision_id" in res["reason"]


def test_rollback_clean_path_restores_content(home_ws):
    imp = Improvement()
    rev_id, prior, after = _commit_and_get_rev_id(home_ws, imp)
    target_path = home_ws["ws"] / "PERSONALITY.md"
    # Confirm new content is there.
    assert "reflective" in target_path.read_text(encoding="utf-8")
    # Roll back.
    res = imp.rollback(rev_id, reason="regression")
    assert res["ok"] is True
    # Target restored to prior.
    assert target_path.read_text(encoding="utf-8") == prior
    # Rollback entry in log.
    log = (home_ws["ws"] / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert "ROLLBACK" in log
    assert "regression" in log


def test_rollback_missing_snapshot(home_ws):
    imp = Improvement()
    rev_id, _, _ = _commit_and_get_rev_id(home_ws, imp)
    # Delete the snapshot file.
    snaps = list((home_ws["home"] / "identity" / "snapshots").glob("*.snapshot"))
    for s in snaps:
        s.unlink()
    res = imp.rollback(rev_id, reason="regression")
    assert res["ok"] is False
    assert "snapshot missing" in res["reason"]


# ── reflect ──────────────────────────────────────────────────────────────


def test_reflect_empty_text(home_ws):
    imp = Improvement()
    rev_id, _, _ = _commit_and_get_rev_id(home_ws, imp)
    res = imp.reflect(rev_id, text="")
    assert res["ok"] is False
    assert "text required" in res["reason"]


def test_reflect_unknown_revision(home_ws):
    imp = Improvement()
    res = imp.reflect("rev_unknown", text="some thoughts")
    assert res["ok"] is False
    assert "unknown revision_id" in res["reason"]


def test_reflect_clean_appends_to_log(home_ws):
    imp = Improvement()
    rev_id, _, _ = _commit_and_get_rev_id(home_ws, imp)
    res = imp.reflect(
        rev_id,
        text="A week later this still feels right.",
    )
    assert res["ok"] is True
    log = (home_ws["ws"] / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert "REFLECTION" in log
    assert "A week later this still feels right" in log


# ── target mappings ──────────────────────────────────────────────────────


def test_all_valid_targets_have_filename_mapping():
    for t in VALID_TARGETS:
        assert t in TARGET_TO_FILENAME
        assert TARGET_TO_FILENAME[t].endswith(".md")


def test_valid_rollback_reasons_nonempty():
    assert len(VALID_ROLLBACK_REASONS) >= 3
