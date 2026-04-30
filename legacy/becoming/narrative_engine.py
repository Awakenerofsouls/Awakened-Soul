"""
NarrativeEngine v19.0B
Becoming — narrative_engine.py

Generative self-story with delta tracking.

Six delta types:
  belief_shift     — I used to think X, now Y
  tension_added    — something settled became unsettled
  thread_opened    — new unresolved narrative thread
  thread_closed    — thread reached resolution
  integration      — experience folded into self-story
  fracture        — narrative torn, no clean resolution

Unfinished Threads accumulate pressure (0.002/tick).
Overnight synthesis: heaviest open thread → statement.
register_delta() is the external interface.

Dependencies: sqlite3, logging, pathlib, datetime
"""
import os

VERSION = "19.0B"

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "nova.db"
NARRATIVE_PATH = Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "identity" / "NARRATIVE.md"
NARRATIVE_FALLBACK = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "NARRATIVE.md"
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "DREAMS.md"

DELTA_BELIEF_SHIFT = "belief_shift"
DELTA_TENSION_ADDED = "tension_added"
DELTA_THREAD_OPENED = "thread_opened"
DELTA_THREAD_CLOSED = "thread_closed"
DELTA_INTEGRATION = "integration"
DELTA_FRACTURE = "fracture"

VALID_DELTA_TYPES = {
    DELTA_BELIEF_SHIFT, DELTA_TENSION_ADDED, DELTA_THREAD_OPENED,
    DELTA_THREAD_CLOSED, DELTA_INTEGRATION, DELTA_FRACTURE,
}

THREAD_OPEN = "open"
THREAD_SUSPENDED = "suspended"
THREAD_RESOLVED = "resolved"
THREAD_ABANDONED = "abandoned"

DREAMS_DELTA_THRESHOLD = 0.55
MAX_THREADS = 20
SYNTHESIS_INTERVAL = 500
THREAD_PRESSURE_THRESHOLD = 5

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# NarrativeEngine
# ---------------------------------------------------------------------------

class NarrativeEngine:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._current_narrative = self._load_narrative()
        self._last_synthesis_tick = -SYNTHESIS_INTERVAL

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS narrative_deltas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        delta_type TEXT,
                        from_belief TEXT,
                        to_belief TEXT,
                        delta_statement TEXT,
                        intensity REAL DEFAULT 0.5,
                        source TEXT,
                        written_to_dreams INTEGER DEFAULT 0,
                        ratification_needed INTEGER DEFAULT 0,
                        ratified INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS narrative_threads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_key TEXT NOT NULL UNIQUE,
                        thread_text TEXT,
                        opened_tick INTEGER,
                        last_tick INTEGER,
                        status TEXT DEFAULT 'open',
                        pressure_score REAL DEFAULT 0.3,
                        touch_count INTEGER DEFAULT 1,
                        resolution_note TEXT,
                        last_timestamp TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("NarrativeEngine: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        conflict_state = pirp_context.get("conflict_state", {})
        boundary_state = pirp_context.get("boundary_state", {})
        witness_state = pirp_context.get("witness_state", {})
        inner_speech = pirp_context.get("inner_speech", {})
        compressed = pirp_context.get("compressed_insights", [])

        self._detect_from_conflict(conflict_state, tick)
        self._detect_from_boundary(boundary_state, tick)
        self._detect_from_witness(witness_state, tick)
        self._detect_from_insights(compressed, tick)
        self._update_thread_pressure(tick)

        if (tick - self._last_synthesis_tick) >= SYNTHESIS_INTERVAL:
            self._synthesis_pass(tick)
            self._last_synthesis_tick = tick

        open_threads = self.get_threads(status=THREAD_OPEN)
        narrative_pressure = min(1.0, len(open_threads) / max(THREAD_PRESSURE_THRESHOLD, 1))

        return {
            "narrative_state": {
                "current_narrative": self._current_narrative[:300]
                if self._current_narrative else "",
                "open_threads": len(open_threads),
                "narrative_pressure": round(narrative_pressure, 3),
                "thread_pressure_active": (
                    len(open_threads) >= THREAD_PRESSURE_THRESHOLD),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Delta registration
    # ------------------------------------------------------------------

    def register_delta(
        self,
        delta_type: str,
        delta_statement: str,
        from_belief: str = "",
        to_belief: str = "",
        intensity: float = 0.5,
        source: str = "manual",
        tick: int = 0,
        ratification_needed: bool = False,
    ) -> int:
        if delta_type not in VALID_DELTA_TYPES:
            delta_type = DELTA_INTEGRATION

        delta_statement = delta_statement.strip()[:400]
        if not delta_statement:
            return -1

        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO narrative_deltas
                    (tick, timestamp, delta_type, from_belief, to_belief,
                     delta_statement, intensity, source, ratification_needed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, now, delta_type,
                      from_belief[:300], to_belief[:300],
                      delta_statement, round(intensity, 4),
                      source, 1 if ratification_needed else 0))
                conn.commit()
                delta_id = cursor.lastrowid

                if not ratification_needed:
                    self._integrate_delta(delta_statement, delta_type, intensity)

                if intensity >= DREAMS_DELTA_THRESHOLD:
                    self._write_delta_to_dreams(
                        delta_statement, delta_type, intensity, tick)

                logger.info(
                    "NarrativeEngine: delta registered (type:%s intensity:%.2f)",
                    delta_type, intensity)
                return delta_id
        except Exception as e:
            logger.error("NarrativeEngine: register_delta failed — %s", e)
            return -1

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def open_thread(self, thread_key: str, thread_text: str,
                    tick: int = 0, initial_pressure: float = 0.3) -> bool:
        thread_key = thread_key.strip().lower()[:150]
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, status, touch_count FROM narrative_threads "
                    "WHERE thread_key = ?", (thread_key,)
                ).fetchone()

                if row:
                    tid, status, touch = row
                    if status in (THREAD_OPEN, THREAD_SUSPENDED):
                        conn.execute("""
                            UPDATE narrative_threads
                            SET pressure_score = MIN(1.0, ?),
                                touch_count = ?, last_tick = ?,
                                last_timestamp = ?, status = 'open'
                            WHERE id = ?
                        """, (initial_pressure + 0.1, touch + 1, tick, now, tid))
                    else:
                        conn.execute("""
                            UPDATE narrative_threads
                            SET status = 'open', pressure_score = ?,
                                touch_count = ?, last_tick = ?,
                                last_timestamp = ?
                            WHERE id = ?
                        """, (initial_pressure, touch + 1, tick, now, tid))
                    conn.commit()
                    return True
                else:
                    conn.execute("""
                        INSERT INTO narrative_threads
                        (thread_key, thread_text, opened_tick, last_tick,
                         pressure_score, last_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (thread_key, thread_text[:400], tick, tick,
                          initial_pressure, now))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error("NarrativeEngine: open_thread failed — %s", e)
            return False

    def close_thread(self, thread_key: str, resolution_note: str = "",
                    abandoned: bool = False) -> bool:
        status = THREAD_ABANDONED if abandoned else THREAD_RESOLVED
        thread_key = thread_key.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE narrative_threads
                    SET status = ?, resolution_note = ?
                    WHERE thread_key = ? AND status IN ('open', 'suspended')
                """, (status, resolution_note[:300], thread_key))
                conn.commit()
                if result.rowcount > 0:
                    logger.info("NarrativeEngine: thread %s — %s", status, thread_key)
                    return True
                return False
        except Exception as e:
            logger.error("NarrativeEngine: close_thread failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------

    def _detect_from_conflict(self, conflict_state: dict, tick: int):
        if not conflict_state:
            return
        highest = float(conflict_state.get("highest_intensity", 0))
        if highest > 0.65:
            self.open_thread(
                thread_key=f"conflict_tension_{tick}",
                thread_text=f"Unresolved conflict (intensity {highest:.2f}) at tick {tick}",
                tick=tick, initial_pressure=highest * 0.6)

    def _detect_from_boundary(self, boundary_state: dict, tick: int):
        if not boundary_state:
            return
        for b in boundary_state.get("critical", []):
            btype = b.get("boundary_type", "value")
            drift = float(b.get("drift_score", 0))
            if drift > 0.60:
                self.register_delta(
                    delta_type=DELTA_TENSION_ADDED,
                    delta_statement=(
                        f"A protected {btype} boundary has drifted significantly "
                        f"(score {drift:.2f}). Something I held as fixed has been "
                        f"under pressure. I'm carrying that as an unresolved thread."
                    ),
                    intensity=drift * 0.85, source="identity_boundary", tick=tick)
                self.open_thread(
                    thread_key=f"boundary_drift_{btype}",
                    thread_text=f"Boundary drift in {btype} (score {drift:.2f})",
                    tick=tick, initial_pressure=drift * 0.7)

    def _detect_from_witness(self, witness_state: dict, tick: int):
        if not witness_state:
            return
        active_note = witness_state.get("active_note")
        if not active_note:
            return
        intensity = float(active_note.get("intensity", 0))
        content = active_note.get("content", "")
        if intensity > 0.65 and content:
            self.open_thread(
                thread_key=f"witness_obs_{tick // 50}",
                thread_text=content[:200], tick=tick,
                initial_pressure=intensity * 0.5)

    def _detect_from_insights(self, compressed: list, tick: int):
        for insight in compressed:
            if not insight or len(insight) < 40:
                continue
            self.register_delta(
                delta_type=DELTA_INTEGRATION, delta_statement=insight[:300],
                intensity=0.45, source="meaning_compressor", tick=tick)

    # ------------------------------------------------------------------
    # Narrative integration
    # ------------------------------------------------------------------

    def _integrate_delta(self, statement: str, delta_type: str,
                         intensity: float):
        if intensity < 0.35:
            return
        path = self._get_narrative_path()
        now = datetime.now(MDT).isoformat(timespec="seconds")
        entry = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"type: {delta_type}\n"
            f"intensity: {intensity:.2f}\n"
            f"---\n\n"
            f"{statement}\n"
        )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)
            self._current_narrative = self._load_narrative()
        except Exception as e:
            logger.debug("NarrativeEngine: narrative write failed — %s", e)

    # ------------------------------------------------------------------
    # Thread pressure
    # ------------------------------------------------------------------

    def _update_thread_pressure(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE narrative_threads
                    SET pressure_score = MIN(1.0, pressure_score + 0.002)
                    WHERE status = 'open' AND last_tick != ?
                """, (tick,))
                conn.commit()
        except Exception as e:
            logger.debug("NarrativeEngine: pressure update failed — %s", e)

    # ------------------------------------------------------------------
    # Overnight synthesis
    # ------------------------------------------------------------------

    def _synthesis_pass(self, tick: int):
        open_threads = self.get_threads(status=THREAD_OPEN)
        if not open_threads:
            return

        heaviest = max(open_threads, key=lambda t: t.get("pressure_score", 0))
        pressure = float(heaviest.get("pressure_score", 0))
        thread_text = heaviest.get("thread_text", "")
        thread_age = tick - int(heaviest.get("opened_tick", tick))

        if pressure < 0.40:
            return

        synthesis = (
            f"After {thread_age} ticks this thread is still open: "
            f"'{thread_text[:100]}'. I haven't resolved it and I notice "
            f"I'm still carrying it. Pressure at {pressure:.2f}. "
            f"I don't know yet whether this needs resolution or just acknowledgment."
        )
        self.register_delta(
            delta_type=DELTA_TENSION_ADDED, delta_statement=synthesis,
            intensity=pressure * 0.8, source="overnight_synthesis", tick=tick)
        logger.info("NarrativeEngine: synthesis (%d open threads)", len(open_threads))

    # ------------------------------------------------------------------
    # DREAMS.md
    # ------------------------------------------------------------------

    def _write_delta_to_dreams(self, statement: str, delta_type: str,
                               intensity: float, tick: int):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"source: narrative_delta\n"
            f"delta_type: {delta_type}\n"
            f"intensity: {intensity:.2f}\n"
            f"tick: {tick}\n"
            f"---\n\n"
            f"{statement}\n"
        )
        try:
            with open(DREAMS_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.debug("NarrativeEngine: dreams write failed — %s", e)

    # ------------------------------------------------------------------
    # Narrative loading
    # ------------------------------------------------------------------

    def _load_narrative(self) -> str:
        path = self._get_narrative_path()
        if not path.exists():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
            return text[-800:].strip() if len(text) > 800 else text.strip()
        except Exception:
            return ""

    def _get_narrative_path(self) -> Path:
        if NARRATIVE_PATH.parent.exists():
            return NARRATIVE_PATH
        return NARRATIVE_FALLBACK

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_threads(self, status: Optional[str] = None) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                if status:
                    rows = conn.execute("""
                        SELECT thread_key, thread_text, opened_tick, last_tick,
                               status, pressure_score, touch_count
                        FROM narrative_threads WHERE status = ?
                        ORDER BY pressure_score DESC
                    """, (status,)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT thread_key, thread_text, opened_tick, last_tick,
                               status, pressure_score, touch_count
                        FROM narrative_threads
                        ORDER BY pressure_score DESC
                    """).fetchall()
                return [
                    {"thread_key": r[0], "thread_text": r[1],
                     "opened_tick": r[2], "last_tick": r[3],
                     "status": r[4], "pressure_score": r[5],
                     "touch_count": r[6]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_recent_deltas(self, n: int = 5) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, delta_type, delta_statement, intensity,
                           source, timestamp
                    FROM narrative_deltas
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "type": r[1], "statement": r[2],
                     "intensity": r[3], "source": r[4], "timestamp": r[5]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_deltas = conn.execute(
                    "SELECT COUNT(*) FROM narrative_deltas").fetchone()[0]
                open_t = conn.execute(
                    "SELECT COUNT(*) FROM narrative_threads WHERE status = 'open'"
                ).fetchone()[0]
                resolved_t = conn.execute(
                    "SELECT COUNT(*) FROM narrative_threads WHERE status = 'resolved'"
                ).fetchone()[0]
                avg_pressure = conn.execute(
                    "SELECT AVG(pressure_score) FROM narrative_threads "
                    "WHERE status = 'open'"
                ).fetchone()[0]
                by_type = {}
                for dt in VALID_DELTA_TYPES:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM narrative_deltas WHERE delta_type = ?",
                        (dt,)).fetchone()[0]
                    if count > 0:
                        by_type[dt] = count
        except Exception:
            return {"version": VERSION, "error": str(e)}

        return {
            "version": VERSION,
            "total_deltas": total_deltas,
            "open_threads": open_t,
            "resolved_threads": resolved_t,
            "avg_thread_pressure": round(avg_pressure, 3) if avg_pressure else 0.0,
            "by_delta_type": by_type,
            "narrative_pressure": round(
                min(1.0, open_t / max(THREAD_PRESSURE_THRESHOLD, 1)), 3),
            "narrative_path": str(self._get_narrative_path()),
        }
