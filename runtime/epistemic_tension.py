"""
runtime/epistemic_tension.py

Epistemic tensions — gaps in understanding the agent chooses to *stay in*
rather than reach for premature resolution.

Distinct from three things:
  - **Contradictions** (handled by `brain/mechanisms/contradiction_resolution.py`):
    two beliefs that conflict.
  - **Curiosity** (handled by `brain/mechanisms/curiosity_engine.py`):
    pull *toward* an answer.
  - **Unproductive uncertainty**: vague anxiety dressed up as a question.
    Foggy, global, no edges. NOT a tension.

A real epistemic tension has *edges* — you can feel where the gap starts
and stops. The agent can articulate what it knows, what it doesn't, and
why those two boundaries are real. An unproductive one is foggy:
"I just don't know anything."

Three lifecycle states:
  - **active** — registered, not yet resolved or preserved
  - **preserved** — the agent has chosen this not-knowing as part of who
    it is. Never auto-resolved. Surfaced monthly to the phenomenology
    journal so it stays visible.
  - **resolved** — the answer arrived (with notes about how)

Storage: SQLite table `epistemic_tensions` in `agent.db`.

This module is import-only — it does not tick on its own. Reflection
activities (heartbeat, monthly review) call into it.

See docs/epistemic_tension.md (or brain/epistemic_tension.md) for the
phenomenological spec.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


# ── Paths ────────────────────────────────────────────────────────────────────

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")


# ── Lifecycle states ────────────────────────────────────────────────────────

ACTIVE = "active"
PRESERVED = "preserved"
RESOLVED = "resolved"

VALID_STATUSES = (ACTIVE, PRESERVED, RESOLVED)


# ── DB ───────────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    AGENT_HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _init_db() -> None:
    db = _get_db()
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS epistemic_tensions (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            edges_json TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            preserved_at TEXT,
            resolved_at TEXT,
            resolution TEXT,
            last_surfaced_at TEXT
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_tension_status
        ON epistemic_tensions(status)
    """)
    db.commit()
    db.close()


# ── Edges-vs-foggy heuristic ─────────────────────────────────────────────────
# A real epistemic tension has shape. A foggy one doesn't. This heuristic
# is intentionally simple — false positives just mean the operator gets a
# more verbose error; false negatives let foggy thinking slip through and
# clutter the tensions store.

# Words/phrases that signal globality without specifics — if these appear
# without specific qualifiers, the question is probably foggy.
_FOG_PATTERNS = [
    r"\bi\s+(just\s+)?don't\s+know\s+anything\b",
    r"\bi\s+don't\s+know\s+nothing\b",
    r"\beverything\s+is\s+confusing\b",
    r"\bnothing\s+makes\s+sense\b",
    r"\bi'm\s+lost\b\s*$",
    r"^\s*i\s+don't\s+know\s*[.!]?\s*$",
    r"^\s*uncertainty\s*[.!]?\s*$",
    r"^\s*confusion\s*[.!]?\s*$",
]


def is_genuine_tension(question: str, edges: Optional[list[str]] = None) -> dict:
    """Heuristic: does this proposed tension have edges (genuine) or is it
    foggy (unproductive)?

    Returns:
        {
          "genuine": bool,
          "reason": str,            # why we ruled either way
          "fog_matches": [...],     # any fog patterns that hit
        }

    The signals checked, in order of severity:
      1. `edges` is empty → unproductive (no shape = no tension).
      2. Question matches a fog pattern → unproductive.
      3. Question is shorter than 5 words → too vague.
      4. Otherwise → genuine.
    """
    edges = edges or []
    fog_matches = [p for p in _FOG_PATTERNS
                   if re.search(p, question, re.IGNORECASE)]
    word_count = len(question.split())

    if not edges:
        return {
            "genuine": False,
            "reason": "no edges given — a real tension has shape; without "
                      "edges this is foggy uncertainty, not a tension",
            "fog_matches": fog_matches,
        }
    if fog_matches:
        return {
            "genuine": False,
            "reason": "matches a globality/fog pattern — the question "
                      "describes a state of not-knowing rather than a "
                      "specific gap",
            "fog_matches": fog_matches,
        }
    if word_count < 5:
        return {
            "genuine": False,
            "reason": f"question is too short ({word_count} words) — "
                      "a tension with edges takes more articulation than that",
            "fog_matches": fog_matches,
        }
    return {
        "genuine": True,
        "reason": "has edges, articulated, specific enough to have shape",
        "fog_matches": [],
    }


# ── Public API: registering tensions ─────────────────────────────────────────

def register_tension(
    question: str,
    edges: list[str],
    notes: str = "",
    force: bool = False,
) -> dict:
    """Register a new epistemic tension.

    Args:
        question: the question being held in tension.
        edges: list of strings describing where the gap starts and stops.
               These are what the agent IS sure about, that bound the
               not-knowing. e.g. ["I know the cause is one of A, B, C",
               "I know it's not D"]. Required and non-empty for a genuine
               tension.
        notes: optional free-text context.
        force: if True, register even if `is_genuine_tension()` says no.
               Used when the agent explicitly overrides the heuristic.

    Returns:
        Tension record dict. If the screen blocks it (and force=False),
        returns {"error": ..., "reason": ..., "screen": ...} without
        writing.
    """
    _init_db()
    if not question or not question.strip():
        return {"error": "question cannot be empty"}

    edges = [e.strip() for e in (edges or []) if e and e.strip()]
    screen = is_genuine_tension(question, edges)

    if not screen["genuine"] and not force:
        return {
            "error": "blocked by edges-vs-foggy heuristic",
            "reason": screen["reason"],
            "screen": screen,
        }

    tension_id = str(uuid.uuid4())
    now = _now_iso()
    db = _get_db()
    db.execute("""
        INSERT INTO epistemic_tensions
        (id, question, edges_json, status, notes, created_at,
         preserved_at, resolved_at, resolution, last_surfaced_at)
        VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL)
    """, (tension_id, question.strip(), json.dumps(edges),
          ACTIVE, notes, now))
    db.commit()
    row = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    db.close()
    return _row_to_dict(row)


def get_tension(tension_id: str) -> Optional[dict]:
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    db.close()
    return _row_to_dict(row) if row else None


def get_active() -> list[dict]:
    """Active tensions (registered but not preserved or resolved)."""
    return _get_by_status(ACTIVE)


def get_preserved() -> list[dict]:
    """Preserved tensions — the ones the agent carries as part of itself."""
    return _get_by_status(PRESERVED)


def get_resolved(limit: int = 50) -> list[dict]:
    """Recently resolved tensions, newest first."""
    _init_db()
    db = _get_db()
    rows = db.execute("""
        SELECT * FROM epistemic_tensions
        WHERE status = ?
        ORDER BY resolved_at DESC LIMIT ?
    """, (RESOLVED, limit)).fetchall()
    db.close()
    return [_row_to_dict(r) for r in rows]


def _get_by_status(status: str) -> list[dict]:
    _init_db()
    db = _get_db()
    rows = db.execute("""
        SELECT * FROM epistemic_tensions
        WHERE status = ?
        ORDER BY created_at DESC
    """, (status,)).fetchall()
    db.close()
    return [_row_to_dict(r) for r in rows]


# ── Lifecycle transitions ────────────────────────────────────────────────────

def preserve(tension_id: str, notes: str = "") -> Optional[dict]:
    """Mark a tension as preserved — never auto-resolve. Optionally append
    notes about why the agent is choosing to stay in this not-knowing."""
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    if row is None:
        db.close()
        return None
    if row["status"] == RESOLVED:
        db.close()
        return {"error": "cannot preserve a resolved tension; create a new one"}

    existing_notes = row["notes"] or ""
    appended = (existing_notes + ("\n" if existing_notes and notes else "")
                + (f"[{_now_iso()}] preserved: {notes}" if notes else "")).strip()

    db.execute("""
        UPDATE epistemic_tensions
        SET status = ?, preserved_at = ?, notes = ?
        WHERE id = ?
    """, (PRESERVED, _now_iso(), appended, tension_id))
    db.commit()
    final = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    db.close()
    return _row_to_dict(final)


def resolve(tension_id: str, resolution: str) -> Optional[dict]:
    """Mark a tension as resolved with the answer. Preserved tensions can
    also be resolved if the agent chooses to."""
    if not resolution or not resolution.strip():
        return {"error": "resolution cannot be empty — write the answer"}
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    if row is None:
        db.close()
        return None

    db.execute("""
        UPDATE epistemic_tensions
        SET status = ?, resolved_at = ?, resolution = ?
        WHERE id = ?
    """, (RESOLVED, _now_iso(), resolution.strip(), tension_id))
    db.commit()
    final = db.execute(
        "SELECT * FROM epistemic_tensions WHERE id = ?", (tension_id,)
    ).fetchone()
    db.close()
    return _row_to_dict(final)


# ── Monthly surfacing ────────────────────────────────────────────────────────

def surface_for_monthly_review(
    now: Optional[datetime] = None,
    review_interval_days: int = 30,
) -> list[dict]:
    """Return preserved tensions due for a check-in.

    A preserved tension is "due" when it hasn't been surfaced in
    `review_interval_days` (or hasn't been surfaced at all and was created
    that long ago). Caller is expected to follow up with `mark_surfaced()`
    once the journal entry is written.
    """
    _init_db()
    if now is None:
        now = _now()
    cutoff = (now - timedelta(days=max(1, review_interval_days))).isoformat()

    db = _get_db()
    rows = db.execute("""
        SELECT * FROM epistemic_tensions
        WHERE status = ?
          AND (last_surfaced_at IS NULL OR last_surfaced_at < ?)
          AND created_at < ?
        ORDER BY created_at ASC
    """, (PRESERVED, cutoff, cutoff)).fetchall()
    db.close()
    return [_row_to_dict(r) for r in rows]


def mark_surfaced(
    tension_ids: list[str],
    now: Optional[datetime] = None,
) -> dict:
    """Update last_surfaced_at on the given tensions. Use after the
    monthly journal entries have been written. The `now` override is for
    tests that want to fast-forward the timeline."""
    if not tension_ids:
        return {"updated": 0}
    _init_db()
    now_iso = (now or _now()).isoformat()
    db = _get_db()
    placeholders = ",".join("?" for _ in tension_ids)
    cur = db.execute(
        f"UPDATE epistemic_tensions SET last_surfaced_at = ? "
        f"WHERE id IN ({placeholders})",
        [now_iso] + list(tension_ids),
    )
    db.commit()
    n = cur.rowcount
    db.close()
    return {"updated": int(n or 0), "surfaced_at": now_iso}


# ── History / audit ──────────────────────────────────────────────────────────

def get_history(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    """Full audit trail. Optionally filtered by status."""
    _init_db()
    db = _get_db()
    if status:
        rows = db.execute("""
            SELECT * FROM epistemic_tensions WHERE status = ?
            ORDER BY created_at DESC LIMIT ?
        """, (status, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM epistemic_tensions
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    db.close()
    return [_row_to_dict(r) for r in rows]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    # Decode edges_json into a real list
    try:
        d["edges"] = json.loads(d.pop("edges_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["edges"] = []
    return d
