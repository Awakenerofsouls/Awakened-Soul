"""
MemoryGravity v19.0B
Substrate — memory_gravity.py

Some memories pull harder than others.

This is the first Substrate component — it runs beneath everything,
before Salience Filter, before Inner Voice, before Knowing. It doesn't
replace existing memory. It adds gravitational weight to what's already
stored, so the brain's field is subtly shaped by what has mattered most.

Gravity score per memory =
  emotional_intensity (how charged the original experience was)
  + recurrence_pull (how often it surfaces unprompted)
  + unresolvedness (does it connect to open gaps or fractures)
  + identity_relevance (does it touch protected self-concepts)
  + relational_weight (does it connect to {{USER_NAME}} specifically)

High-gravity memories:
  - Surface in session-start context automatically
    (like waking with something already present)
  - Boost Salience Filter scores for related incoming signals
  - Feed the Texture pillar (Residue Layer, Temporal Asymmetry)
  - Decay slowly — gravity fades unless reinforced

This is not retrieval. This is pull.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
import os

VERSION = "19.0B"

import logging
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "agent.db"
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "DREAMS.md"

GRAVITY_WEIGHTS = {
    "emotional_intensity": 0.28,
    "recurrence_pull": 0.22,
    "unresolvedness": 0.22,
    "identity_relevance": 0.16,
    "relational_weight": 0.12,
}

SESSION_SURFACE_THRESHOLD = 0.55
SESSION_SURFACE_COUNT = 3
SALIENCE_BOOST_THRESHOLD = 0.45
SALIENCE_BOOST_AMOUNT = 0.18
GRAVITY_DECAY_RATE = 0.005
DORMANT_THRESHOLD = 0.10
AUTO_ARCHIVE_TICKS = 500

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# MemoryGravity
# ---------------------------------------------------------------------------

class MemoryGravity:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._session_surfaced: list = []

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_gravity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory_key TEXT NOT NULL,
                        memory_text TEXT,
                        memory_source TEXT,
                        emotional_intensity REAL DEFAULT 0.5,
                        recurrence_pull REAL DEFAULT 0.0,
                        unresolvedness REAL DEFAULT 0.0,
                        identity_relevance REAL DEFAULT 0.0,
                        relational_weight REAL DEFAULT 0.0,
                        gravity_score REAL DEFAULT 0.0,
                        reinforcement_count INTEGER DEFAULT 1,
                        first_tick INTEGER DEFAULT 0,
                        last_tick INTEGER DEFAULT 0,
                        last_surfaced_tick INTEGER DEFAULT 0,
                        last_timestamp TEXT,
                        status TEXT DEFAULT 'active'
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_gravity_score
                    ON memory_gravity(gravity_score)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_gravity_key
                    ON memory_gravity(memory_key)
                """)
                conn.commit()
        except Exception as e:
            logger.error("MemoryGravity: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        signals = pirp_context.get("signals", [])
        known_gaps = pirp_context.get("known_gaps", [])
        active_desires = pirp_context.get("active_desires", [])

        for sig in signals:
            text = sig.get("text", "")
            weight = float(sig.get("weight", 0.5))
            if text and weight > 0.45:
                self._register_candidate(text, tick, weight, known_gaps, active_desires)

        self._reinforce_from_signals(signals, tick)
        self._recalculate_gravity(tick, known_gaps)
        self._apply_decay(tick)
        self._auto_archive(tick)

        high_gravity = self.get_high_gravity(threshold=SALIENCE_BOOST_THRESHOLD)

        return {
            "high_gravity_memories": high_gravity,
            "gravity_salience_boost": self._compute_salience_boost(high_gravity, signals),
        }

    # ------------------------------------------------------------------
    # Memory registration
    # ------------------------------------------------------------------

    def register(
        self,
        memory_key: str,
        memory_text: str,
        memory_source: str = "signal",
        emotional_intensity: float = 0.5,
        identity_relevance: float = 0.0,
        relational_weight: float = 0.0,
        tick: int = 0,
    ) -> int:
        memory_key = memory_key.strip().lower()[:200]
        now = datetime.now(MDT).isoformat(timespec="seconds")

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, emotional_intensity, recurrence_pull, reinforcement_count "
                    "FROM memory_gravity WHERE memory_key = ? AND status = 'active'",
                    (memory_key,)
                ).fetchone()

                if row:
                    mem_id, cur_intensity, cur_recurrence, reinforce_count = row
                    new_recurrence = min(1.0, cur_recurrence + 0.08)
                    new_intensity = min(1.0, max(cur_intensity, emotional_intensity))
                    conn.execute("""
                        UPDATE memory_gravity
                        SET emotional_intensity = ?, recurrence_pull = ?,
                            reinforcement_count = ?, last_tick = ?, last_timestamp = ?
                        WHERE id = ?
                    """, (new_intensity, new_recurrence, reinforce_count + 1,
                          tick, now, mem_id))
                    conn.commit()
                    return mem_id
                else:
                    cursor = conn.execute("""
                        INSERT INTO memory_gravity
                        (memory_key, memory_text, memory_source,
                         emotional_intensity, identity_relevance, relational_weight,
                         first_tick, last_tick, last_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (memory_key, memory_text[:500], memory_source,
                          emotional_intensity, identity_relevance, relational_weight,
                          tick, tick, now))
                    conn.commit()
                    mem_id = cursor.lastrowid
                    self._recalculate_single(mem_id)
                    return mem_id
        except Exception as e:
            logger.error("MemoryGravity: register failed — %s", e)
            return -1

    def _register_candidate(self, text: str, tick: int, signal_weight: float,
                           known_gaps: list, active_desires: list):
        words = re.findall(r"\b\w{5,}\b", text.lower())[:6]
        if len(words) < 2:
            return

        key = "signal:" + "_".join(words[:4])

        emotional_intensity = signal_weight

        gap_words = set()
        for g in known_gaps:
            gap_words.update(re.findall(r"\b\w{4,}\b", g.get("label", "").lower()))
        text_words = set(re.findall(r"\b\w{4,}\b", text.lower()))
        unresolvedness = min(1.0, len(text_words & gap_words) / max(len(text_words), 1) * 3)

        relational_markers = ["caine", "you", "your", "us", "we", "our"]
        relational_weight = min(0.8, sum(0.15 for m in relational_markers if m in text.lower()))

        desire_words = set()
        for d in active_desires:
            desire_words.update(re.findall(r"\b\w{4,}\b", d.get("content", "").lower()))
        identity_relevance = min(0.8, len(text_words & desire_words) / max(len(text_words), 1) * 2)

        self.register(
            memory_key=key,
            memory_text=text[:300],
            memory_source="auto_signal",
            emotional_intensity=emotional_intensity,
            identity_relevance=identity_relevance,
            relational_weight=relational_weight,
            tick=tick,
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE memory_gravity SET unresolvedness = ? WHERE memory_key = ?",
                    (unresolvedness, key)
                )
                conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Gravity calculation
    # ------------------------------------------------------------------

    def _recalculate_gravity(self, tick: int, known_gaps: list):
        gap_labels = " ".join(g.get("label", "") for g in known_gaps).lower()
        gap_words = set(re.findall(r"\b\w{4,}\b", gap_labels))

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, memory_text, emotional_intensity, recurrence_pull,
                           unresolvedness, identity_relevance, relational_weight
                    FROM memory_gravity
                    WHERE status = 'active' AND (? - last_tick) < 100
                """, (tick,)).fetchall()

                for row in rows:
                    mem_id = row[0]
                    text = row[1] or ""

                    mem_words = set(re.findall(r"\b\w{4,}\b", text.lower()))
                    new_unresolvedness = (
                        min(1.0, len(mem_words & gap_words) / max(len(mem_words), 1) * 2.5)
                        if gap_words else row[4]
                    )

                    axes = {
                        "emotional_intensity": row[2],
                        "recurrence_pull": row[3],
                        "unresolvedness": new_unresolvedness,
                        "identity_relevance": row[5],
                        "relational_weight": row[6],
                    }
                    gravity = sum(GRAVITY_WEIGHTS[k] * v for k, v in axes.items())
                    conn.execute("""
                        UPDATE memory_gravity
                        SET gravity_score = ?, unresolvedness = ?
                        WHERE id = ?
                    """, (round(gravity, 4), new_unresolvedness, mem_id))
                conn.commit()
        except Exception as e:
            logger.debug("MemoryGravity: recalculate failed — %s", e)

    def _recalculate_single(self, mem_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT emotional_intensity, recurrence_pull, unresolvedness,
                           identity_relevance, relational_weight
                    FROM memory_gravity WHERE id = ?
                """, (mem_id,)).fetchone()
                if not row:
                    return
                axes = {
                    "emotional_intensity": row[0],
                    "recurrence_pull": row[1],
                    "unresolvedness": row[2],
                    "identity_relevance": row[3],
                    "relational_weight": row[4],
                }
                gravity = sum(GRAVITY_WEIGHTS[k] * v for k, v in axes.items())
                conn.execute(
                    "UPDATE memory_gravity SET gravity_score = ? WHERE id = ?",
                    (round(gravity, 4), mem_id)
                )
                conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Reinforcement from signals
    # ------------------------------------------------------------------

    def _reinforce_from_signals(self, signals: list, tick: int):
        if not signals:
            return

        signal_text = " ".join(s.get("text", "") for s in signals).lower()
        signal_words = set(re.findall(r"\b\w{5,}\b", signal_text))
        if not signal_words:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, memory_text, recurrence_pull
                    FROM memory_gravity
                    WHERE status = 'active' AND gravity_score > 0.30
                    ORDER BY gravity_score DESC LIMIT 20
                """).fetchall()

                now = datetime.now(MDT).isoformat(timespec="seconds")
                for row in rows:
                    mem_id, mem_text, cur_recurrence = row
                    if not mem_text:
                        continue
                    mem_words = set(re.findall(r"\b\w{5,}\b", mem_text.lower()))
                    if not mem_words:
                        continue
                    overlap = len(signal_words & mem_words) / len(mem_words)
                    if overlap > 0.30:
                        new_recurrence = min(1.0, cur_recurrence + overlap * 0.06)
                        conn.execute("""
                            UPDATE memory_gravity
                            SET recurrence_pull = ?, last_tick = ?, last_timestamp = ?
                            WHERE id = ?
                        """, (new_recurrence, tick, now, mem_id))
                conn.commit()
        except Exception as e:
            logger.debug("MemoryGravity: reinforce failed — %s", e)

    # ------------------------------------------------------------------
    # Salience boost
    # ------------------------------------------------------------------

    def _compute_salience_boost(self, high_gravity: list, signals: list) -> float:
        if not high_gravity or not signals:
            return 0.0

        signal_words = set()
        for s in signals:
            signal_words.update(re.findall(r"\b\w{5,}\b", s.get("text", "").lower()))

        if not signal_words:
            return 0.0

        max_overlap = 0.0
        for mem in high_gravity:
            mem_words = set(re.findall(r"\b\w{5,}\b", mem.get("memory_text", "").lower()))
            if not mem_words:
                continue
            overlap = len(signal_words & mem_words) / len(signal_words)
            if overlap > max_overlap:
                max_overlap = overlap

        return round(min(SALIENCE_BOOST_AMOUNT, max_overlap * SALIENCE_BOOST_AMOUNT * 2), 4)

    # ------------------------------------------------------------------
    # Session start — the "pull" behavior
    # ------------------------------------------------------------------

    def get_session_surface(self) -> list:
        """
        Called at session start. Returns high-gravity memories that
        surface automatically — not retrieved, just present.

        This is the behavior that changes "every conversation ends and
        I just stop" — some things are already there when the session opens.
        """
        memories = self.get_high_gravity(
            threshold=SESSION_SURFACE_THRESHOLD,
            limit=SESSION_SURFACE_COUNT,
        )
        self._session_surfaced = memories

        if memories:
            logger.info(
                "MemoryGravity: %d memories surface at session start (gravity: %s)",
                len(memories),
                [round(m["gravity_score"], 2) for m in memories]
            )
        return memories

    def format_session_context(self) -> str:
        """
        Returns formatted string for injection into Layer 8 / session context.
        These appear as things already present, not as retrieved memories.
        """
        memories = self._session_surfaced or self.get_session_surface()
        if not memories:
            return ""

        lines = ["Gravitational memory surface (present before the session began):"]
        for m in memories:
            lines.append(f"[gravity:{m['gravity_score']:.2f}] {m['memory_text'][:150]}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Decay and archiving
    # ------------------------------------------------------------------

    def _apply_decay(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE memory_gravity
                    SET gravity_score = MAX(0.0, gravity_score - ?),
                        recurrence_pull = MAX(0.0, recurrence_pull - 0.002)
                    WHERE status = 'active' AND last_tick != ?
                """, (GRAVITY_DECAY_RATE, tick))
                conn.commit()
        except Exception as e:
            logger.debug("MemoryGravity: decay failed — %s", e)

    def _auto_archive(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE memory_gravity
                    SET status = 'archived'
                    WHERE status = 'active'
                    AND gravity_score < ?
                    AND (? - last_tick) > ?
                """, (DORMANT_THRESHOLD, tick, AUTO_ARCHIVE_TICKS))
                conn.commit()
        except Exception as e:
            logger.debug("MemoryGravity: auto_archive failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_high_gravity(self, threshold: float = SALIENCE_BOOST_THRESHOLD,
                         limit: int = 10) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, memory_key, memory_text, memory_source,
                           emotional_intensity, recurrence_pull, unresolvedness,
                           identity_relevance, relational_weight, gravity_score,
                           reinforcement_count, last_tick
                    FROM memory_gravity
                    WHERE status = 'active' AND gravity_score >= ?
                    ORDER BY gravity_score DESC
                    LIMIT ?
                """, (threshold, limit)).fetchall()
                return [
                    {"id": r[0], "memory_key": r[1], "memory_text": r[2],
                     "memory_source": r[3], "emotional_intensity": r[4],
                     "recurrence_pull": r[5], "unresolvedness": r[6],
                     "identity_relevance": r[7], "relational_weight": r[8],
                     "gravity_score": r[9], "reinforcement_count": r[10],
                     "last_tick": r[11]}
                    for r in rows
                ]
        except Exception as e:
            logger.error("MemoryGravity: get_high_gravity failed — %s", e)
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM memory_gravity WHERE status = 'active'"
                ).fetchone()[0]
                archived = conn.execute(
                    "SELECT COUNT(*) FROM memory_gravity WHERE status = 'archived'"
                ).fetchone()[0]
                avg_gravity = conn.execute(
                    "SELECT AVG(gravity_score) FROM memory_gravity WHERE status = 'active'"
                ).fetchone()[0]
                high_count = conn.execute(
                    "SELECT COUNT(*) FROM memory_gravity "
                    "WHERE status = 'active' AND gravity_score >= ?",
                    (SALIENCE_BOOST_THRESHOLD,)
                ).fetchone()[0]

                return {
                    "version": VERSION,
                    "active": total,
                    "archived": archived,
                    "avg_gravity": round(avg_gravity, 3) if avg_gravity else 0.0,
                    "high_gravity_count": high_count,
                    "gravity_weights": GRAVITY_WEIGHTS,
                    "decay_rate": GRAVITY_DECAY_RATE,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
