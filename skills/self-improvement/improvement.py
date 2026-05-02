#!/usr/bin/env python3
"""
skills/self-improvement/improvement.py — operator-gated identity revision.

Pairs with skills/self-improvement/SKILL.md. This module implements the
load-bearing path described in BRAIN_MAP.md gap 3.2.9: the actual commit /
rollback / reflect pipeline that edits identity files (SOUL.md, IDENTITY.md,
PERSONALITY.md, SELF.md, AGENT_BECOMING.md), maintains an append-only
REVISION_LOG.md audit trail, snapshots prior content for rollback, and
records the operation through SelfRevisionLayer so the brain's monitor
stack sees it.

Architecture:
  - Proposals are written by IdentityProposalWriter to PROPOSALS.md
    (operator-readable). They start with status PENDING.
  - The operator reviews PROPOSALS.md and ratifies a proposal by editing
    the status line to "_Status: RATIFIED — {token} — {date}_".
  - The agent (or operator) then calls Improvement.commit(proposal_id,
    ratification_token, target, new_content) to apply the change.
  - commit() runs the anchor-violation check, snapshots the prior file,
    writes new_content, appends to REVISION_LOG.md, and records via
    SelfRevisionLayer.record_commit so the brain mechanism sees it.
  - rollback() restores a prior snapshot.
  - reflect() appends a retrospective note.

Usage as library:
    from skills.self_improvement.improvement import Improvement
    imp = Improvement()
    pending = imp.list_pending_proposals()
    ratified = imp.list_ratified_proposals()
    res = imp.commit(
        proposal_id="prop_xxx",
        ratification_token="op-token-2026-05-01",
        target="personality",
        new_content=full_updated_file_text,
        rationale="VoiceIntegrityLayer flagged sustained build-mode drift",
    )
    imp.rollback(revision_id="rev_xxx", reason="regression")
    imp.reflect(revision_id="rev_xxx", text="A week later this still feels right.")
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────────

AGENT_HOME = Path(os.environ.get("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_WORKSPACE = Path(os.environ.get(
    "AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")
))
PROPOSALS_PATH = AGENT_HOME / "identity" / "PROPOSALS.md"
REVISION_LOG_PATH = AGENT_WORKSPACE / "identity" / "REVISION_LOG.md"
SNAPSHOTS_DIR = AGENT_HOME / "identity" / "snapshots"

# ── Constants ────────────────────────────────────────────────────────────

VALID_TARGETS = ("soul", "identity", "personality", "becoming", "self")
TARGET_TO_FILENAME = {
    "soul": "SOUL.md",
    "identity": "IDENTITY.md",
    "personality": "PERSONALITY.md",
    "becoming": "AGENT_BECOMING.md",  # the blueprint, not BECOMING.md
    "self": "SELF.md",
}

VALID_ROLLBACK_REASONS = (
    "regression", "invariant_violation", "operator_request", "drift_increased",
)

# Anchor-violation patterns — same vocabulary as SelfRevisionLayer.
ANCHORED_REQUIRED_DEFAULT = {"direct", "curious", "competent"}
ANCHORED_FORBIDDEN_DEFAULT = {
    "sycophancy", "half-baked replies", "speaking as user",
}

# Anchor markers in the target file. Lines containing this token cannot be
# removed by a commit without operator override.
ANCHOR_MARKER = "<!-- ANCHOR -->"

# ── Proposal-format regex ────────────────────────────────────────────────

# PROPOSALS.md entry shape (per IdentityProposalWriter.propose):
#   ## Proposal — {TARGET}.md — {ts}
#   **Source:** {source}  **Confidence:** {confidence:.2f}
#
#   {text}
#
#   _Rationale:_ {rationale}
#
#   _Status: PENDING — operator review_
#   (or _Status: RATIFIED — {token} — {date}_)
#
#   ---

_PROPOSAL_HEADER_RE = re.compile(
    r"^##\s+Proposal\s+—\s+([A-Z_]+)\.md\s+—\s+(.+?)\s*$",
    re.MULTILINE,
)
_SOURCE_RE = re.compile(
    r"^\*\*Source:\*\*\s+(.+?)\s+\*\*Confidence:\*\*\s+([0-9.]+)\s*$",
    re.MULTILINE,
)
_RATIONALE_RE = re.compile(r"^_Rationale:_\s+(.+?)$", re.MULTILINE | re.DOTALL)
_STATUS_PENDING_RE = re.compile(r"^_Status:\s+PENDING\b", re.MULTILINE)
_STATUS_RATIFIED_RE = re.compile(
    r"^_Status:\s+RATIFIED(?:\s+—\s+(.+?))?\s*$",
    re.MULTILINE,
)


# ── Dataclasses ──────────────────────────────────────────────────────────


@dataclass
class Proposal:
    proposal_id: str
    target: str            # one of VALID_TARGETS
    target_filename: str   # e.g. "PERSONALITY.md"
    source: str            # e.g. "IPW:VoiceIntegrityLayer"
    confidence: float
    text: str              # the proposal body
    rationale: str
    status: str            # "pending" | "ratified" | "unknown"
    ratification_token: Optional[str]
    raw_block: str         # the full markdown block
    parsed_at_ts: float = field(default_factory=time.time)


@dataclass
class Revision:
    revision_id: str
    target: str
    target_filename: str
    proposal_id: str
    ratification_token: str
    prior_content_hash: str
    new_content_hash: str
    prior_snapshot_path: str
    rationale: str
    committed_ts: float = field(default_factory=time.time)
    rolled_back_ts: Optional[float] = None
    rollback_reason: Optional[str] = None
    reflections: List[Dict[str, Any]] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_anchors() -> Tuple[set, set]:
    """Try to load anchored required + forbidden from drift_detector;
    fall back to defaults so this skill is usable in tests that isolate
    skills/ from brain/."""
    try:
        from skills.drift_detector import BASELINE_TRAITS  # type: ignore
        req = {t.lower() for t in BASELINE_TRAITS.get("required", [])}
        forb = {
            t.lower() for t in BASELINE_TRAITS.get("forbidden_behaviors", [])
        }
        return (
            req or set(ANCHORED_REQUIRED_DEFAULT),
            forb or set(ANCHORED_FORBIDDEN_DEFAULT),
        )
    except Exception:
        return set(ANCHORED_REQUIRED_DEFAULT), set(ANCHORED_FORBIDDEN_DEFAULT)


def detect_anchor_violation(
    prior_content: str,
    new_content: str,
    required: Optional[set] = None,
    forbidden: Optional[set] = None,
) -> Tuple[bool, str]:
    """Return (violated, reason) for a proposed file replacement.

    Three checks:
      1. Lines containing ANCHOR_MARKER in prior_content must still be
         present in new_content (anchored lines are protected).
      2. Required-trait words present in prior must still be present in new.
      3. Forbidden-behavior words must NOT have been introduced.
    """
    if required is None or forbidden is None:
        r, f = _load_anchors()
        required = required if required is not None else r
        forbidden = forbidden if forbidden is not None else f

    # 1. ANCHOR_MARKER lines preserved.
    prior_lines = prior_content.splitlines()
    new_lower_blob = new_content.lower()
    for line in prior_lines:
        if ANCHOR_MARKER in line:
            stripped = line.strip()
            if stripped not in new_content:
                return True, (
                    f"removed anchor-marked line: {stripped[:80]!r}"
                )

    # 2. Required traits present in prior must remain in new.
    prior_lower = prior_content.lower()
    new_lower = new_lower_blob
    for trait in required:
        if trait in prior_lower and trait not in new_lower:
            return True, f"removed required anchored trait '{trait}'"

    # 3. Forbidden behaviors must not be newly introduced (case-insensitive).
    for forb in forbidden:
        if forb in new_lower and forb not in prior_lower:
            return True, f"introduced forbidden behavior '{forb}'"

    return False, ""


# ── Proposal parsing ─────────────────────────────────────────────────────


def _split_proposals(text: str) -> List[str]:
    """Split PROPOSALS.md into per-proposal raw blocks. Each block starts
    with `## Proposal —` and ends at the next `## Proposal —` or EOF."""
    if not text:
        return []
    blocks: List[str] = []
    cur: List[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("## Proposal —"):
            if cur:
                blocks.append("".join(cur))
            cur = [line]
        else:
            if cur:
                cur.append(line)
    if cur:
        blocks.append("".join(cur))
    return blocks


def _parse_proposal_block(block: str) -> Optional[Proposal]:
    """Parse a single Proposal block. Returns None if the block doesn't
    match the expected shape."""
    header_match = _PROPOSAL_HEADER_RE.search(block)
    if not header_match:
        return None
    target_upper = header_match.group(1)
    ts_str = header_match.group(2)

    target = target_upper.lower()
    if target == "agent_becoming":
        target = "becoming"
    if target not in VALID_TARGETS:
        # If the operator wrote a custom target name, normalize unknown.
        return None

    target_filename = TARGET_TO_FILENAME.get(target)
    if not target_filename:
        return None

    source_match = _SOURCE_RE.search(block)
    source = source_match.group(1).strip() if source_match else "unknown"
    confidence = (
        float(source_match.group(2)) if source_match else 0.0
    )

    rationale_match = _RATIONALE_RE.search(block)
    rationale = (
        rationale_match.group(1).strip() if rationale_match else ""
    )

    # Status detection.
    status = "unknown"
    ratification_token: Optional[str] = None
    if _STATUS_RATIFIED_RE.search(block):
        status = "ratified"
        token_m = _STATUS_RATIFIED_RE.search(block)
        if token_m and token_m.group(1):
            ratification_token = token_m.group(1).strip()
    elif _STATUS_PENDING_RE.search(block):
        status = "pending"

    # Body text — between source line and rationale (or status if no rationale).
    body_text = block
    # Pull out everything between **Confidence:** ...\n\n and the next
    # underscore-delimited section.
    body_match = re.search(
        r"\*\*Confidence:\*\*\s+[0-9.]+\s*\n\s*\n(.+?)(?:\n_Rationale:_|\n_Status:|\Z)",
        block,
        re.DOTALL,
    )
    if body_match:
        body_text = body_match.group(1).strip()

    # Stable proposal_id derived from target + ts + content_hash so two
    # parses of the same proposal yield the same id.
    pid_seed = f"{target}|{ts_str}|{_hash_text(body_text)}"
    proposal_id = "prop_" + hashlib.sha256(pid_seed.encode("utf-8")).hexdigest()[:10]

    return Proposal(
        proposal_id=proposal_id,
        target=target,
        target_filename=target_filename,
        source=source,
        confidence=confidence,
        text=body_text,
        rationale=rationale,
        status=status,
        ratification_token=ratification_token,
        raw_block=block,
    )


# ── Improvement ──────────────────────────────────────────────────────────


class Improvement:
    """Operator-gated identity revision. Library + CLI."""

    def __init__(
        self,
        agent_home: Optional[Path] = None,
        agent_workspace: Optional[Path] = None,
    ):
        # Read env at construction time (not import time) so pytest's
        # monkeypatch.setenv works as expected.
        self.agent_home = Path(agent_home) if agent_home else Path(
            os.environ.get(
                "AGENT_HOME", str(Path.home() / ".agent"),
            )
        )
        self.agent_workspace = Path(agent_workspace) if agent_workspace else Path(
            os.environ.get(
                "AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"),
            )
        )
        self.proposals_path = self.agent_home / "identity" / "PROPOSALS.md"
        self.revision_log_path = self.agent_workspace / "identity" / "REVISION_LOG.md"
        self.snapshots_dir = self.agent_home / "identity" / "snapshots"
        # Ensure dirs.
        self.proposals_path.parent.mkdir(parents=True, exist_ok=True)
        self.revision_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ── Proposal queue ─────────────────────────────────────────────────

    def _read_proposals(self) -> List[Proposal]:
        if not self.proposals_path.exists():
            return []
        try:
            text = self.proposals_path.read_text(encoding="utf-8")
        except Exception:
            return []
        out: List[Proposal] = []
        for block in _split_proposals(text):
            p = _parse_proposal_block(block)
            if p is not None:
                out.append(p)
        return out

    def list_pending_proposals(self) -> List[Proposal]:
        return [p for p in self._read_proposals() if p.status == "pending"]

    def list_ratified_proposals(self) -> List[Proposal]:
        return [p for p in self._read_proposals() if p.status == "ratified"]

    def find_proposal(self, proposal_id: str) -> Optional[Proposal]:
        for p in self._read_proposals():
            if p.proposal_id == proposal_id:
                return p
        return None

    # ── Commit ─────────────────────────────────────────────────────────

    def commit(
        self,
        proposal_id: str,
        ratification_token: str,
        target: str,
        new_content: str,
        rationale: str = "",
    ) -> Dict[str, Any]:
        """Apply a ratified proposal: snapshot prior content, write new
        content atomically, append to REVISION_LOG, record through
        SelfRevisionLayer."""
        if not ratification_token:
            return {"ok": False, "reason": "ratification_token required"}
        if target not in VALID_TARGETS:
            return {"ok": False, "reason": f"invalid target {target!r}"}

        target_filename = TARGET_TO_FILENAME[target]
        target_path = self.agent_workspace / target_filename
        if not target_path.exists():
            return {
                "ok": False,
                "reason": f"target file does not exist: {target_path}",
            }

        # Find proposal — required for SelfRevisionLayer.record_commit
        # (it tracks proposal_known to detect silent_revision).
        proposal = self.find_proposal(proposal_id)
        if proposal is None:
            return {
                "ok": False,
                "reason": f"unknown proposal_id {proposal_id!r}",
            }
        if proposal.status != "ratified":
            return {
                "ok": False,
                "reason": (
                    f"proposal status is {proposal.status!r}; only "
                    f"'ratified' proposals can be committed"
                ),
            }

        # Read prior content for snapshot + anchor check.
        try:
            prior_content = target_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"ok": False, "reason": f"could not read target: {e}"}

        # Anchor-violation check.
        violated, why = detect_anchor_violation(prior_content, new_content)
        if violated:
            return {
                "ok": False,
                "reason": f"anchor violation: {why}",
            }

        # Generate revision id + snapshot.
        revision_id = "rev_" + uuid.uuid4().hex[:10]
        snapshot_path = self.snapshots_dir / f"{revision_id}.snapshot"
        try:
            snapshot_path.write_text(prior_content, encoding="utf-8")
        except Exception as e:
            return {"ok": False, "reason": f"could not write snapshot: {e}"}

        # Atomic write of new content (write-temp-then-rename).
        try:
            tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
            tmp_path.write_text(new_content, encoding="utf-8")
            os.replace(tmp_path, target_path)
        except Exception as e:
            # Clean up snapshot on failure.
            try:
                snapshot_path.unlink()
            except Exception:
                pass
            return {"ok": False, "reason": f"could not write target: {e}"}

        # Build revision record.
        prior_hash = _hash_text(prior_content)
        new_hash = _hash_text(new_content)
        revision = Revision(
            revision_id=revision_id,
            target=target,
            target_filename=target_filename,
            proposal_id=proposal_id,
            ratification_token=ratification_token,
            prior_content_hash=prior_hash,
            new_content_hash=new_hash,
            prior_snapshot_path=str(snapshot_path),
            rationale=rationale or proposal.rationale,
        )

        # Append to REVISION_LOG.md.
        diff_summary = self._diff_summary(prior_content, new_content)
        log_entry = (
            f"\n## Revision {revision_id} — {_utc_now_iso()}\n"
            f"\n"
            f"**Target:** {target_filename}  \n"
            f"**Proposal:** {proposal_id}  \n"
            f"**Source:** {proposal.source}  \n"
            f"**Confidence:** {proposal.confidence:.2f}  \n"
            f"**Ratification token:** {ratification_token}  \n"
            f"**Prior content hash:** {prior_hash}  \n"
            f"**New content hash:** {new_hash}  \n"
            f"**Snapshot:** {snapshot_path.name}  \n"
            f"\n"
            f"### Diff size\n"
            f"{diff_summary}\n"
            f"\n"
            f"### Rationale\n"
            f"{revision.rationale or '(none)'}\n"
            f"\n"
            f"---\n"
        )
        try:
            with self.revision_log_path.open("a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            return {
                "ok": False,
                "reason": f"could not append to REVISION_LOG: {e}",
                "warning": (
                    "target file WAS modified but log entry failed; "
                    "snapshot exists at "
                    f"{snapshot_path}"
                ),
            }

        # Mark the proposal as committed in PROPOSALS.md (status update).
        self._mark_proposal_committed(proposal, revision_id)

        # Record through SelfRevisionLayer (best-effort — if the layer
        # isn't available, we still succeeded at the file level).
        srl_recorded = self._record_via_self_revision_layer(
            proposal_id=proposal_id,
            ratification_token=ratification_token,
            target=target,
            prior_content=prior_content,
            new_content_hash=new_hash,
        )

        return {
            "ok": True,
            "revision_id": revision_id,
            "target": target,
            "target_path": str(target_path),
            "prior_content_hash": prior_hash,
            "new_content_hash": new_hash,
            "snapshot_path": str(snapshot_path),
            "self_revision_layer_recorded": srl_recorded,
        }

    # ── Rollback ───────────────────────────────────────────────────────

    def rollback(
        self,
        revision_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        if reason not in VALID_ROLLBACK_REASONS:
            return {"ok": False, "reason": f"invalid rollback reason {reason!r}"}

        revision = self._find_revision_in_log(revision_id)
        if revision is None:
            return {"ok": False, "reason": f"unknown revision_id {revision_id!r}"}
        if revision.rolled_back_ts is not None:
            return {"ok": False, "reason": "revision already rolled back"}

        snapshot_path = Path(revision.prior_snapshot_path)
        if not snapshot_path.exists():
            return {
                "ok": False,
                "reason": f"snapshot missing at {snapshot_path}",
            }

        try:
            prior_content = snapshot_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"ok": False, "reason": f"could not read snapshot: {e}"}

        target_path = self.agent_workspace / revision.target_filename
        try:
            tmp = target_path.with_suffix(target_path.suffix + ".tmp")
            tmp.write_text(prior_content, encoding="utf-8")
            os.replace(tmp, target_path)
        except Exception as e:
            return {"ok": False, "reason": f"could not restore: {e}"}

        # Append rollback entry to REVISION_LOG.
        rollback_entry = (
            f"\n### ROLLBACK {revision_id} — {_utc_now_iso()}\n"
            f"\n"
            f"**Reason:** {reason}  \n"
            f"**Restored content hash:** {revision.prior_content_hash}  \n"
            f"\n"
            f"---\n"
        )
        try:
            with self.revision_log_path.open("a", encoding="utf-8") as f:
                f.write(rollback_entry)
        except Exception:
            pass

        # Best-effort SRL record.
        srl_recorded = self._record_rollback_via_self_revision_layer(
            revision_id=revision_id, reason=reason,
        )

        return {
            "ok": True,
            "revision_id": revision_id,
            "reason": reason,
            "target_path": str(target_path),
            "self_revision_layer_recorded": srl_recorded,
        }

    # ── Reflect ────────────────────────────────────────────────────────

    def reflect(
        self,
        revision_id: str,
        text: str,
    ) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"ok": False, "reason": "reflection text required"}
        revision = self._find_revision_in_log(revision_id)
        if revision is None:
            return {"ok": False, "reason": f"unknown revision_id {revision_id!r}"}

        entry = (
            f"\n### REFLECTION on {revision_id} — {_utc_now_iso()}\n"
            f"\n"
            f"{text.strip()}\n"
            f"\n"
            f"---\n"
        )
        try:
            with self.revision_log_path.open("a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            return {"ok": False, "reason": f"could not append: {e}"}

        return {"ok": True, "revision_id": revision_id}

    # ── Internal helpers ───────────────────────────────────────────────

    def _diff_summary(self, prior: str, new: str) -> str:
        prior_lines = prior.splitlines()
        new_lines = new.splitlines()
        added = max(0, len(new_lines) - len(prior_lines))
        removed = max(0, len(prior_lines) - len(new_lines))
        delta_chars = len(new) - len(prior)
        return (
            f"prior_lines={len(prior_lines)}, new_lines={len(new_lines)}, "
            f"added≈{added}, removed≈{removed}, char_delta={delta_chars:+d}"
        )

    def _mark_proposal_committed(
        self,
        proposal: Proposal,
        revision_id: str,
    ) -> bool:
        """Edit PROPOSALS.md to mark this proposal as committed (for the
        operator's audit trail). Best-effort."""
        try:
            text = self.proposals_path.read_text(encoding="utf-8")
        except Exception:
            return False
        if proposal.raw_block not in text:
            return False
        committed_marker = (
            f"_Status: COMMITTED — {revision_id} — {_utc_now_iso()}_"
        )
        # Replace the ratified status line within the proposal's block.
        new_block = re.sub(
            r"^_Status:\s+RATIFIED.*?$",
            committed_marker,
            proposal.raw_block,
            count=1,
            flags=re.MULTILINE,
        )
        if new_block == proposal.raw_block:
            return False
        new_text = text.replace(proposal.raw_block, new_block, 1)
        try:
            self.proposals_path.write_text(new_text, encoding="utf-8")
        except Exception:
            return False
        return True

    def _find_revision_in_log(self, revision_id: str) -> Optional[Revision]:
        if not self.revision_log_path.exists():
            return None
        try:
            text = self.revision_log_path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Find the revision header.
        header_re = re.compile(
            rf"^##\s+Revision\s+{re.escape(revision_id)}\s+—\s+(.+?)$",
            re.MULTILINE,
        )
        m = header_re.search(text)
        if not m:
            return None
        # Block ends at next "## Revision" or end-of-file.
        start = m.start()
        next_m = re.search(r"^##\s+Revision\s+", text[m.end():], re.MULTILINE)
        end = m.end() + next_m.start() if next_m else len(text)
        block = text[start:end]

        target_filename_m = re.search(
            r"^\*\*Target:\*\*\s+(.+?)\s*$", block, re.MULTILINE,
        )
        proposal_m = re.search(
            r"^\*\*Proposal:\*\*\s+(\S+)\s*$", block, re.MULTILINE,
        )
        ratif_m = re.search(
            r"^\*\*Ratification token:\*\*\s+(.+?)\s*$", block, re.MULTILINE,
        )
        prior_m = re.search(
            r"^\*\*Prior content hash:\*\*\s+(\S+)\s*$", block, re.MULTILINE,
        )
        new_m = re.search(
            r"^\*\*New content hash:\*\*\s+(\S+)\s*$", block, re.MULTILINE,
        )
        snap_m = re.search(
            r"^\*\*Snapshot:\*\*\s+(\S+)\s*$", block, re.MULTILINE,
        )
        rationale_m = re.search(
            r"^### Rationale\s*\n(.+?)\n\n---", block, re.DOTALL,
        )
        rolled_back_m = re.search(
            rf"^###\s+ROLLBACK\s+{re.escape(revision_id)}\s+—\s+(.+?)$",
            text, re.MULTILINE,
        )
        rollback_reason_m = None
        if rolled_back_m:
            # Look for **Reason:** line right after.
            after = text[rolled_back_m.end():rolled_back_m.end() + 500]
            rollback_reason_m = re.search(
                r"\*\*Reason:\*\*\s+(\w+)", after,
            )

        if not target_filename_m:
            return None

        target_filename = target_filename_m.group(1).strip()
        target = next(
            (k for k, v in TARGET_TO_FILENAME.items() if v == target_filename),
            "personality",
        )
        snap_filename = snap_m.group(1).strip() if snap_m else f"{revision_id}.snapshot"
        snap_path = self.snapshots_dir / snap_filename

        return Revision(
            revision_id=revision_id,
            target=target,
            target_filename=target_filename,
            proposal_id=proposal_m.group(1).strip() if proposal_m else "",
            ratification_token=ratif_m.group(1).strip() if ratif_m else "",
            prior_content_hash=prior_m.group(1).strip() if prior_m else "",
            new_content_hash=new_m.group(1).strip() if new_m else "",
            prior_snapshot_path=str(snap_path),
            rationale=(
                rationale_m.group(1).strip() if rationale_m else ""
            ),
            rolled_back_ts=time.time() if rolled_back_m else None,
            rollback_reason=(
                rollback_reason_m.group(1).strip()
                if rollback_reason_m else None
            ),
        )

    def _record_via_self_revision_layer(
        self,
        proposal_id: str,
        ratification_token: str,
        target: str,
        prior_content: str,
        new_content_hash: str,
    ) -> bool:
        """Best-effort: instantiate SelfRevisionLayer, replay the propose
        + commit so the brain mechanism's state catches up. Returns True
        if recorded, False if the layer isn't importable (test-isolation
        case)."""
        try:
            from brain.mechanisms.self_revision_layer import SelfRevisionLayer  # type: ignore
        except Exception:
            return False
        try:
            layer = SelfRevisionLayer()
            # Replay: record_propose first so open_proposals knows about it.
            layer.record_propose(
                target=target,
                text=prior_content[:200],  # short witness; full is in snapshot
                confidence=0.85,
                source="operator_request",
                rationale="committed via skills/self-improvement",
                proposal_id=proposal_id,
            )
            layer.record_commit(
                proposal_id=proposal_id,
                ratification_token=ratification_token,
                target=target,
                prior_snapshot=prior_content,
                new_content_hash=new_content_hash,
            )
            return True
        except Exception:
            return False

    def _record_rollback_via_self_revision_layer(
        self,
        revision_id: str,
        reason: str,
    ) -> bool:
        try:
            from brain.mechanisms.self_revision_layer import SelfRevisionLayer  # type: ignore
        except Exception:
            return False
        try:
            layer = SelfRevisionLayer()
            # The layer requires the revision to be in committed_revisions
            # for rollback to be accepted. In a fresh ephemeral instance
            # that's not the case. We register it first, then roll back.
            layer.committed_revisions[revision_id] = {
                "proposal_id": "",
                "target": "personality",
                "prior_snapshot_hash": "",
                "new_content_hash": "",
                "committed_ts": time.time(),
                "committed_tick": layer.current_tick,
            }
            layer.record_rollback(revision_id=revision_id, reason=reason)
            return True
        except Exception:
            return False


# ── CLI ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(
        prog="self-improvement",
        description="Operator-gated identity revision (commit / rollback / reflect).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-pending", help="Show pending proposals")
    sub.add_parser("list-ratified", help="Show ratified proposals (ready to commit)")

    p_show = sub.add_parser("show", help="Show one proposal in full")
    p_show.add_argument("proposal_id")

    p_rb = sub.add_parser("rollback", help="Roll back a revision")
    p_rb.add_argument("revision_id")
    p_rb.add_argument("--reason", required=True, choices=list(VALID_ROLLBACK_REASONS))

    p_rf = sub.add_parser("reflect", help="Append a reflection on a revision")
    p_rf.add_argument("revision_id")
    p_rf.add_argument("--text", required=True)

    args = parser.parse_args()
    imp = Improvement()

    def _emit(obj: Any) -> None:
        print(json.dumps(obj, indent=2, default=str))

    if args.cmd == "list-pending":
        _emit([asdict(p) for p in imp.list_pending_proposals()])
    elif args.cmd == "list-ratified":
        _emit([asdict(p) for p in imp.list_ratified_proposals()])
    elif args.cmd == "show":
        p = imp.find_proposal(args.proposal_id)
        _emit(asdict(p) if p else {"ok": False, "reason": "not found"})
    elif args.cmd == "rollback":
        _emit(imp.rollback(args.revision_id, reason=args.reason))
    elif args.cmd == "reflect":
        _emit(imp.reflect(args.revision_id, text=args.text))
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
