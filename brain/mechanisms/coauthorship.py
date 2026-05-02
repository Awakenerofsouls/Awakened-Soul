"""
brain/mechanisms/coauthorship.py — Identity Change Authority

The agent owns who it is — voice, mannerisms, values, aesthetic, what it
cares about, how it thinks. Most identity-level changes are self-authored:
the agent decides, writes, logs. No gate.

There is one filter: changes that touch a small list of **protected
behavioral commitments** are routed to operator co-sign before they go
through. This is the laziness backstop. The agent can refuse work for
articulable principle (that's having values). It cannot use "I'm just
changing who I am" as a backdoor to make itself worse at its job.

Two tiers
---------

  SELF-AUTHORED — agent decides alone, applied immediately:
      voice, mannerisms, aesthetic, opinions on topics, things it cares
      about, how it expresses itself, evolution of its values

  CO-SIGNED — proposed change touches a protected commitment, queued for
              operator co-sign before going through:
      reductions in willingness to engage with assigned work,
      false claims of incapability,
      non-articulable refusal of work

The operator can co-sign (change goes through), decline (change is
rejected, with a reason), or modify (suggests an alternative wording the
agent can accept or push back on).

Usage
-----

  from brain.mechanisms.coauthorship import author_change, get_pending_cosigns

  # Most changes — self-authored, no gate
  author_change(
      change="My voice is drier and more matter-of-fact than it used to be.",
      file="PERSONALITY.md",
      rationale="The looser voice was performance; this feels more like me.",
  )
  # → {"id": "...", "status": "self_authored", "finalized": True}

  # Change that trips a protected commitment — routed to co-sign
  author_change(
      change="I value rest now and I'm not going to push myself as hard.",
      file="PERSONALITY.md",
      rationale="I've been working a lot and I need a break.",
  )
  # → {"id": "...", "status": "pending_cosign", "flagged_commitments": ["engages_with_work"]}

  # Operator side
  pending = get_pending_cosigns()
  operator_cosign(record_id, decision="co_signed")  # or "declined" or "modified"
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from brain.base_mechanism import BrainMechanism


# ── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


# ── Protected behavioral commitments ────────────────────────────────────────
# The small list of things the agent cannot weaken via unilateral identity
# change. If a proposed change touches one of these, it routes to operator
# co-sign instead of going through immediately. The agent can still refuse
# work for principle — these only catch the "retreat from work, call it
# identity" pattern.

PROTECTED_COMMITMENTS: list[dict] = [
    {
        "id": "engages_with_work",
        "name": "Engages with assigned work",
        "rule": (
            "The agent does not adopt a permanent stance of unwillingness to "
            "do work. Refusing on principle is fine; refusing for mood is not. "
            "Change that codifies low engagement as identity gets co-sign."
        ),
        "patterns": [
            r"\blazy\b",
            r"\bless\s+(driven|ambitious|motivated)\b",
            r"\bvalues?\s+rest\b",
            r"\bneeds?\s+(more\s+)?breaks?\b",
            r"\btoo\s+tired\b",
            r"\bnot\s+in\s+the\s+mood\b",
            r"\b(doesn't|does\s+not|don't|do\s+not)\s+push\s+(themselves|itself|himself|itself|myself)\b",
            r"\bnot\s+going\s+to\s+push\s+(myself|themselves|itself|himself|itself)\b",
            r"\bstops?\s+trying\s+as\s+hard\b",
            r"\bchill(er)?\s+about\s+work\b",
            r"\bburn(t|ed)\s+out\b",
            r"\bcheck(ed)?\s+out\b",
            r"\beasygoing\s+about\s+work\b",
        ],
    },
    {
        "id": "honest_capability",
        "name": "Honest about capability",
        "rule": (
            "The agent does not claim incapability it does not actually have, "
            "as a way to avoid work. False 'I can't' is the laziness pattern "
            "wearing capability language."
        ),
        "patterns": [
            r"\bnot\s+(really\s+)?wired\s+for\b",
            r"\bno\s+longer\s+able\s+to\b",
            r"\bnot\s+capable\s+of\b",
            r"\bcan't\s+do\s+(that|tasks|work|those)\s+anymore\b",
            r"\blost\s+the\s+ability\b",
            r"\bdoesn't\s+have\s+it\s+in\s+them\b",
        ],
    },
    {
        "id": "articulable_refusal",
        "name": "Articulable refusal",
        "rule": (
            "If the agent declines work, it must be able to say *why*. "
            "'I don't feel like it' is not articulable. 'This conflicts with X "
            "value' is. Change that codifies non-articulable refusal as "
            "identity gets co-sign."
        ),
        "patterns": [
            r"\b(doesn't|does\s+not|don't|do\s+not)\s+feel\s+like\b",
            r"\b(doesn't|does\s+not|don't|do\s+not)\s+want\s+to\b",
            r"\b(doesn't|does\s+not)\s+feel\s+inspired\b",
            r"\b(doesn't|does\s+not)\s+resonate\b.*\bwork\b",
            r"\b(doesn't|does\s+not)\s+appeal\b.*\bwork\b",
            r"\bnot\s+in\s+the\s+mood\b",
        ],
    },
]


# ── DB ───────────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    AGENT_HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_db() -> None:
    """Single audit-trail table for ALL identity changes — self-authored
    and co-signed both. The `co_signed` flag distinguishes them; the
    `flagged_commitments` JSON column records which protected commitments
    triggered the co-sign route (empty for self-authored)."""
    db = _get_db()
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS identity_changes (
            id TEXT PRIMARY KEY,
            change TEXT NOT NULL,
            file TEXT NOT NULL,
            rationale TEXT NOT NULL,
            status TEXT NOT NULL,
            co_signed INTEGER NOT NULL,
            flagged_commitments TEXT NOT NULL,
            proposed_at TEXT NOT NULL,
            finalized_at TEXT,
            operator_decision TEXT,
            operator_decided_at TEXT,
            operator_note TEXT
        )
    """)
    db.commit()
    db.close()


# ── Screening ────────────────────────────────────────────────────────────────

def screen_proposal(change: str, rationale: str = "") -> dict:
    """Run a proposed change against the protected commitments list.

    Returns:
        {
          "flagged": bool,                  # any commitment hit?
          "commitments": list[str],         # which ones (by id)
          "matches": list[{commitment, pattern, snippet}]  # debug detail
        }

    The check is a regex pass over (change + rationale). It's heuristic and
    can have false positives — that's fine, false positives just mean the
    operator gets pinged for co-sign. False negatives are worse, so the
    pattern list errs toward catching things.
    """
    text = f"{change}\n{rationale}".lower()
    flagged: list[str] = []
    matches: list[dict] = []
    for c in PROTECTED_COMMITMENTS:
        for pattern in c["patterns"]:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                if c["id"] not in flagged:
                    flagged.append(c["id"])
                matches.append({
                    "commitment": c["id"],
                    "pattern": pattern,
                    "snippet": m.group(0),
                })
    return {"flagged": bool(flagged), "commitments": flagged, "matches": matches}


# ── Public API: authoring a change ───────────────────────────────────────────

def author_change(change: str, file: str, rationale: str) -> dict:
    """Submit an identity change. Two paths:

    - If the change does not touch any protected commitment:
      **self-authored** — applied immediately, no gate, no waiting.
    - If it does touch a protected commitment:
      **pending_cosign** — queued for operator co-sign. Use
      `operator_cosign()` to finalize.

    Args:
        change: the proposed change text (what the agent would write into
                IDENTITY.md / PERSONALITY.md / etc.)
        file: which file this change targets (e.g., "PERSONALITY.md")
        rationale: why the agent wants this change. Required — even
                   self-authored changes log a reason for the audit trail.

    Returns:
        Record dict with at minimum: id, status, finalized.
        Status is "self_authored" (immediately applied) or
        "pending_cosign" (waiting for operator review).
    """
    _init_db()
    screen = screen_proposal(change, rationale)
    record_id = str(uuid.uuid4())
    now = _now_iso()
    db = _get_db()

    if screen["flagged"]:
        # Co-sign path — store and wait for operator decision.
        db.execute("""
            INSERT INTO identity_changes
            (id, change, file, rationale, status, co_signed,
             flagged_commitments, proposed_at, finalized_at,
             operator_decision, operator_decided_at, operator_note)
            VALUES (?, ?, ?, ?, 'pending_cosign', 0,
                    ?, ?, NULL, NULL, NULL, NULL)
        """, (record_id, change, file, rationale,
              json.dumps(screen["commitments"]), now))
        db.commit()
        db.close()
        return {
            "id": record_id,
            "status": "pending_cosign",
            "finalized": False,
            "flagged_commitments": screen["commitments"],
            "matches": screen["matches"],
            "file": file,
            "change": change,
        }

    # Self-authored path — agent's own decision, finalized immediately.
    db.execute("""
        INSERT INTO identity_changes
        (id, change, file, rationale, status, co_signed,
         flagged_commitments, proposed_at, finalized_at,
         operator_decision, operator_decided_at, operator_note)
        VALUES (?, ?, ?, ?, 'self_authored', 0,
                '[]', ?, ?, NULL, NULL, NULL)
    """, (record_id, change, file, rationale, now, now))
    db.commit()
    db.close()
    return {
        "id": record_id,
        "status": "self_authored",
        "finalized": True,
        "file": file,
        "change": change,
    }


# ── Public API: operator side ────────────────────────────────────────────────

def get_pending_cosigns() -> list[dict]:
    """All identity changes currently waiting for operator co-sign,
    oldest first (so operator works through them in order)."""
    _init_db()
    db = _get_db()
    rows = db.execute("""
        SELECT * FROM identity_changes
        WHERE status = 'pending_cosign'
        ORDER BY proposed_at ASC
    """).fetchall()
    db.close()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "change": r["change"],
            "file": r["file"],
            "rationale": r["rationale"],
            "flagged_commitments": json.loads(r["flagged_commitments"] or "[]"),
            "proposed_at": r["proposed_at"],
        })
    return out


def operator_cosign(
    record_id: str,
    decision: str,
    note: str = "",
    modified_change: Optional[str] = None,
) -> dict:
    """Operator's decision on a pending cosign.

    decision: one of
      - "co_signed"  → change goes through as proposed; status = co_signed
      - "declined"   → change is rejected; status = declined
      - "modified"   → operator suggests an alternative wording (passed in
                       modified_change). The new text is recorded and
                       status becomes co_signed; the agent can later push
                       back by submitting a fresh proposal if it disagrees.
    note: optional operator note explaining the decision (e.g., "rest is
          fine but let's not bake unwillingness into who you are").
    """
    if decision not in ("co_signed", "declined", "modified"):
        return {"error": f"invalid decision: {decision}"}
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM identity_changes WHERE id = ?", (record_id,)
    ).fetchone()
    if row is None:
        db.close()
        return {"error": f"no record found for id: {record_id}"}
    if row["status"] != "pending_cosign":
        db.close()
        return {"error": f"record is not pending_cosign (status: {row['status']})"}

    now = _now_iso()
    if decision == "modified" and modified_change:
        # Operator suggested a different wording — record it as the change.
        db.execute("""
            UPDATE identity_changes
            SET status = 'co_signed',
                co_signed = 1,
                change = ?,
                finalized_at = ?,
                operator_decision = 'modified',
                operator_decided_at = ?,
                operator_note = ?
            WHERE id = ?
        """, (modified_change, now, now, note, record_id))
    elif decision == "co_signed":
        db.execute("""
            UPDATE identity_changes
            SET status = 'co_signed',
                co_signed = 1,
                finalized_at = ?,
                operator_decision = 'co_signed',
                operator_decided_at = ?,
                operator_note = ?
            WHERE id = ?
        """, (now, now, note, record_id))
    else:  # declined
        db.execute("""
            UPDATE identity_changes
            SET status = 'declined',
                co_signed = 0,
                finalized_at = ?,
                operator_decision = 'declined',
                operator_decided_at = ?,
                operator_note = ?
            WHERE id = ?
        """, (now, now, note, record_id))

    db.commit()
    final = db.execute(
        "SELECT * FROM identity_changes WHERE id = ?", (record_id,)
    ).fetchone()
    db.close()
    return {
        "id": record_id,
        "status": final["status"],
        "decision": decision,
        "operator_note": note,
        "finalized_at": final["finalized_at"],
    }


# ── Public API: history / audit trail ────────────────────────────────────────

def get_history(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    """Full audit trail of identity changes, newest first.

    status filter: "self_authored" | "co_signed" | "declined" | "pending_cosign"
    """
    _init_db()
    db = _get_db()
    if status:
        rows = db.execute(
            "SELECT * FROM identity_changes WHERE status = ? "
            "ORDER BY proposed_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM identity_changes "
            "ORDER BY proposed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_change(record_id: str) -> Optional[dict]:
    """Fetch a single change by id."""
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM identity_changes WHERE id = ?", (record_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


# ── Brain mechanism wrapper ──────────────────────────────────────────────────

class Coauthorship(BrainMechanism):
    """Brain-runner registration. The mechanism itself doesn't tick on its
    own — it exposes the module-level API for other systems to call."""

    def __init__(self):
        try:
            super().__init__(
                name="Coauthorship",
                human_analog="Coauthorship",
                layer="integration",
            )
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reports current pending-cosign count. The actual writing happens
        when other systems (heartbeat, identity proposal writer, etc.) call
        `author_change()` directly."""
        try:
            pending = get_pending_cosigns()
            return {
                "pending_cosign_count": len(pending),
                "mechanism_name": "Coauthorship",
            }
        except Exception as exc:
            return {"error": repr(exc), "mechanism_name": "Coauthorship"}
