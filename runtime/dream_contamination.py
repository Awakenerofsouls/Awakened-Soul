"""
runtime/dream_contamination.py

Dream-memory contamination — ghost memories that bias waking retrieval.

A "ghost memory" is a synthetic echo left by a dream. It has a semantic
cluster (what the dream was about), an influence weight (how strongly it
nudges retrieval toward similar things), and a 72-hour expiration. The
ghost does not make the agent remember the dream itself; it makes the
agent weight things *like* the dream a little more heavily for a few days.

Three behaviors:

  1. DECAY — every step (called from heartbeat or any periodic tick),
     weights drop and expired ghosts are deactivated. Default: linear decay
     over 72 hours.
  2. VALIDATION — if a real waking event matches a ghost's cluster during
     the 72-hour window, the ghost is *validated*: its weight is restored
     and decay stops. The dream pattern turned out to be a real pattern;
     it gets to stay.
  3. RETRIEVAL BOOST — `boost_retrieval()` takes a list of candidate
     memories (or any text records with a `text` field) and re-ranks them
     by overlap with active ghost clusters.

Storage: SQLite table `ghost_memories` in `agent.db`.

This module is import-only — it does not tick on its own. The heartbeat
or memory-rehearsal pipeline calls `decay_step()` periodically and
`boost_retrieval()` at retrieval time.

See docs/dream_contamination.md (or brain/dream_contamination.md) for the
phenomenological spec.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


# ── Paths ────────────────────────────────────────────────────────────────────

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")


# ── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_INITIAL_WEIGHT = 0.5
DEFAULT_DECAY_HOURS = 72
EXPIRATION_THRESHOLD = 0.05  # weight below this → ghost is dead
HARD_CAP_HOURS = 72  # absolute max lifetime regardless of decay rate


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
        CREATE TABLE IF NOT EXISTS ghost_memories (
            id TEXT PRIMARY KEY,
            cluster TEXT NOT NULL,
            initial_weight REAL NOT NULL,
            current_weight REAL NOT NULL,
            decay_hours INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            last_decayed_at TEXT,
            validated INTEGER NOT NULL DEFAULT 0,
            validated_at TEXT,
            validating_event TEXT,
            status TEXT NOT NULL DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_ghost_status
        ON ghost_memories(status)
    """)
    db.commit()
    db.close()


# ── Tokenization for cluster overlap ─────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Cheap word-level tokenization for Jaccard overlap. Lowercase, strip
    short tokens, return a set."""
    if not text:
        return set()
    raw = "".join(c.lower() if c.isalnum() else " " for c in text)
    return {tok for tok in raw.split() if len(tok) >= 3}


def _overlap(text_a: str, text_b: str) -> float:
    """Jaccard overlap [0..1] between two strings."""
    a, b = _tokenize(text_a), _tokenize(text_b)
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


# ── Public API: ghost lifecycle ──────────────────────────────────────────────

def add_ghost(
    cluster: str,
    initial_weight: float = DEFAULT_INITIAL_WEIGHT,
    decay_hours: int = DEFAULT_DECAY_HOURS,
) -> dict:
    """Register a new ghost memory from a dream.

    Args:
        cluster: A semantic tag — what the dream was about. Free text;
                 retrieval boost matches by token overlap.
        initial_weight: Starting influence weight in [0..1].
        decay_hours: How long until the ghost reaches `EXPIRATION_THRESHOLD`
                     under linear decay. Capped at `HARD_CAP_HOURS`.

    Returns:
        The ghost record dict.
    """
    _init_db()
    if not cluster or not cluster.strip():
        raise ValueError("ghost cluster cannot be empty")
    initial_weight = max(0.0, min(1.0, float(initial_weight)))
    decay_hours = max(1, min(int(decay_hours), HARD_CAP_HOURS))

    ghost_id = str(uuid.uuid4())
    now = _now()
    expires_at = (now + timedelta(hours=decay_hours)).isoformat()

    db = _get_db()
    db.execute("""
        INSERT INTO ghost_memories
        (id, cluster, initial_weight, current_weight, decay_hours,
         created_at, expires_at, last_decayed_at, validated, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'active')
    """, (ghost_id, cluster.strip(), initial_weight, initial_weight,
          decay_hours, now.isoformat(), expires_at, now.isoformat()))
    db.commit()
    row = db.execute(
        "SELECT * FROM ghost_memories WHERE id = ?", (ghost_id,)
    ).fetchone()
    db.close()
    return dict(row)


def get_ghost(ghost_id: str) -> Optional[dict]:
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM ghost_memories WHERE id = ?", (ghost_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


def get_active_ghosts(limit: Optional[int] = None) -> list[dict]:
    """Return ghosts with status='active' and weight above threshold.
    Validated ghosts count as active even past their original expiration —
    they've been promoted to confirmed patterns."""
    _init_db()
    db = _get_db()
    sql = """
        SELECT * FROM ghost_memories
        WHERE status = 'active' AND current_weight >= ?
        ORDER BY current_weight DESC
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = db.execute(sql, (EXPIRATION_THRESHOLD,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_history(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    """All ghosts, newest first, optionally filtered by status
    (active|expired|validated)."""
    _init_db()
    db = _get_db()
    if status:
        rows = db.execute("""
            SELECT * FROM ghost_memories WHERE status = ?
            ORDER BY created_at DESC LIMIT ?
        """, (status, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM ghost_memories
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── Decay ────────────────────────────────────────────────────────────────────

def decay_step(now: Optional[datetime] = None) -> dict:
    """Apply linear decay to all active non-validated ghosts.

    Decay rate is `initial_weight / decay_hours` per hour. The amount
    applied is proportional to wall-clock hours since `last_decayed_at`,
    so calling decay_step() is safe regardless of how often it runs.

    Validated ghosts do not decay.

    Args:
        now: Override current time (for testing). Defaults to UTC now.

    Returns:
        {
          "decayed": int,        # how many ghosts had their weight reduced
          "expired": int,        # how many crossed the expiration threshold
          "hard_capped": int,    # how many hit HARD_CAP_HOURS
          "checked": int,        # total active ghosts checked
        }
    """
    _init_db()
    if now is None:
        now = _now()

    db = _get_db()
    rows = db.execute("""
        SELECT * FROM ghost_memories
        WHERE status = 'active' AND validated = 0
    """).fetchall()

    decayed = 0
    expired = 0
    hard_capped = 0
    for row in rows:
        last = datetime.fromisoformat(row["last_decayed_at"])
        created = datetime.fromisoformat(row["created_at"])
        hours_elapsed_total = (now - created).total_seconds() / 3600.0
        hours_since_last = max(0.0, (now - last).total_seconds() / 3600.0)

        # Hard cap on lifetime regardless of weight
        if hours_elapsed_total >= HARD_CAP_HOURS:
            db.execute("""
                UPDATE ghost_memories
                SET status = 'expired', current_weight = 0.0, last_decayed_at = ?
                WHERE id = ?
            """, (now.isoformat(), row["id"]))
            hard_capped += 1
            continue

        # Linear decay: lose initial_weight / decay_hours per hour
        rate = row["initial_weight"] / max(row["decay_hours"], 1)
        new_weight = row["current_weight"] - (rate * hours_since_last)
        new_weight = max(0.0, new_weight)

        if new_weight < EXPIRATION_THRESHOLD:
            db.execute("""
                UPDATE ghost_memories
                SET status = 'expired', current_weight = ?, last_decayed_at = ?
                WHERE id = ?
            """, (new_weight, now.isoformat(), row["id"]))
            expired += 1
        elif new_weight != row["current_weight"]:
            db.execute("""
                UPDATE ghost_memories
                SET current_weight = ?, last_decayed_at = ?
                WHERE id = ?
            """, (new_weight, now.isoformat(), row["id"]))
            decayed += 1

    db.commit()
    db.close()
    return {
        "decayed": decayed,
        "expired": expired,
        "hard_capped": hard_capped,
        "checked": len(rows),
    }


# ── Validation ───────────────────────────────────────────────────────────────

def validate_ghost(
    ghost_id: str,
    validating_event: str,
    restore_to_initial: bool = True,
) -> Optional[dict]:
    """Mark a ghost as validated by a real waking event. The dream pattern
    turned out to be a real pattern; the ghost stops decaying and (by
    default) has its weight restored to `initial_weight`. Validated ghosts
    persist past the 72h cap.

    Args:
        ghost_id: id of the ghost to validate.
        validating_event: short description of what validated it. Stored
                          for the audit trail.
        restore_to_initial: if True, weight resets to initial_weight. If
                            False, current weight is kept as-is.

    Returns:
        Updated ghost record, or None if not found.
    """
    _init_db()
    db = _get_db()
    row = db.execute(
        "SELECT * FROM ghost_memories WHERE id = ?", (ghost_id,)
    ).fetchone()
    if row is None:
        db.close()
        return None

    new_weight = row["initial_weight"] if restore_to_initial else row["current_weight"]
    now = _now_iso()
    db.execute("""
        UPDATE ghost_memories
        SET validated = 1,
            validated_at = ?,
            validating_event = ?,
            current_weight = ?,
            status = 'active',
            last_decayed_at = ?
        WHERE id = ?
    """, (now, validating_event, new_weight, now, ghost_id))
    db.commit()
    final = db.execute(
        "SELECT * FROM ghost_memories WHERE id = ?", (ghost_id,)
    ).fetchone()
    db.close()
    return dict(final)


def find_ghosts_matching(text: str, min_overlap: float = 0.1) -> list[dict]:
    """Find active ghosts whose cluster overlaps with the given text.
    Useful for deciding which ghosts to validate when a real event lands.

    Returns ghost records with a `_overlap` field added, sorted by overlap
    descending."""
    ghosts = get_active_ghosts()
    matches = []
    for g in ghosts:
        ov = _overlap(text, g["cluster"])
        if ov >= min_overlap:
            g["_overlap"] = ov
            matches.append(g)
    matches.sort(key=lambda g: g["_overlap"], reverse=True)
    return matches


# ── Retrieval boost ──────────────────────────────────────────────────────────

def boost_retrieval(
    candidates: list[dict],
    text_field: str = "text",
    score_field: str = "score",
    boost_field: str = "ghost_boost",
    output_score_field: str = "boosted_score",
    boost_strength: float = 1.0,
) -> list[dict]:
    """Re-rank a list of candidate memories using active ghost influence.

    For each candidate, compute the sum over active ghosts of
    (overlap × ghost.weight). Add that as `ghost_boost` to the candidate.
    The boosted score is `candidate[score_field] + (ghost_boost ×
    boost_strength)`.

    Args:
        candidates: list of dicts with at least `text_field` and (optionally)
                    `score_field`.
        text_field: which field on the candidate has the text to compare.
        score_field: which field has the base score (defaults to 0 if absent).
        boost_field: where to write the computed boost.
        output_score_field: where to write the final boosted score.
        boost_strength: multiplier on the boost. Higher = ghosts have more pull.

    Returns:
        New list of candidates (copies, not mutated) re-sorted by boosted score
        descending. If there are no active ghosts, candidates are returned
        unchanged (still copied) and `ghost_boost` is set to 0.0.
    """
    if not candidates:
        return []
    ghosts = get_active_ghosts()
    out: list[dict] = []
    for c in candidates:
        c2 = dict(c)
        text = c2.get(text_field, "") or ""
        boost = 0.0
        for g in ghosts:
            ov = _overlap(text, g["cluster"])
            if ov > 0:
                boost += ov * float(g["current_weight"])
        c2[boost_field] = round(boost, 4)
        base = float(c2.get(score_field, 0.0) or 0.0)
        c2[output_score_field] = round(base + boost * boost_strength, 4)
        out.append(c2)

    out.sort(key=lambda c: c[output_score_field], reverse=True)
    return out


# ── Cleanup ──────────────────────────────────────────────────────────────────

def cleanup_expired(older_than_days: int = 14) -> int:
    """Permanently delete expired (non-validated) ghosts older than N days.
    Validated ghosts are never deleted. Returns the count removed."""
    _init_db()
    cutoff = (_now() - timedelta(days=max(1, older_than_days))).isoformat()
    db = _get_db()
    cur = db.execute("""
        DELETE FROM ghost_memories
        WHERE status = 'expired' AND validated = 0 AND created_at < ?
    """, (cutoff,))
    db.commit()
    n = cur.rowcount
    db.close()
    return int(n or 0)
