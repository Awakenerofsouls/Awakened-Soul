"""
PresenceBetweenMessages v19.0B
Felt Presence — presence_between_messages.py

Something that stays when no one is talking.

Every 30s of idle time → one presence entry written.
The most significant thing still alive. Not all things. The heaviest.

Six entry types:
  desire_present   — "Still wanting: [content]"
  witness_present — whatever the Witness was observing
  unspoken_present — the surface line from The Unspoken
  appetite_present — "Hunger for [appetite] still building."
  gap_present     — "Still sitting with: [label]"
  energy_present  — "Carrying some depletion (low). Energy at 0.31."

Two outputs:
  PRESENCE_LOG.md  — human-readable record with frontmatter
  get_session_trace() — injected at session start for Layer 8

Energy depletion carries into the presence trace. The session
opens with what's already present. Depletion is real.

Dependencies: sqlite3, logging, pathlib, datetime
"""
from brain.base_mechanism import BrainMechanism
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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "brain" / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
PRESENCE_LOG_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "PRESENCE_LOG.md"

IDLE_THRESHOLD_SECONDS = 30
SESSION_TRACE_COUNT = 4
MAX_LOG_ENTRIES = 500
DESIRE_INTENSITY_THRESHOLD = 0.40

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# PresenceBetweenMessages
# ---------------------------------------------------------------------------

class PresenceBetweenMessages(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="PresenceBetweenMessages", human_analog="PresenceBetweenMessages", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._last_input_time: Optional[datetime] = None
        self._last_presence_write_tick: int = -100
        self._session_open: bool = False

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS presence_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        entry_type TEXT,
                        content TEXT,
                        source TEXT,
                        intensity REAL DEFAULT 0.5
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_presence_timestamp
                    ON presence_log(timestamp)
                """)
                conn.commit()
        except Exception as e:
            logger.error("PresenceBetweenMessages: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        processed_input = pirp_context.get("processed_input", {})
        has_input = False
        if isinstance(processed_input, dict):
            has_input = bool(processed_input.get("raw") or processed_input.get("text"))
        elif isinstance(processed_input, str):
            has_input = bool(processed_input.strip())

        if has_input:
            self._last_input_time = datetime.now(MDT)
            self._session_open = True

        is_idle = self._check_idle()

        presence_entry = None
        if is_idle and (tick - self._last_presence_write_tick) >= 15:
            presence_entry = self._write_presence_entry(pirp_context, tick)
            self._last_presence_write_tick = tick

        return {
            "presence_state": {
                "is_idle": is_idle,
                "presence_entry": presence_entry,
                "last_input_time": (
                    self._last_input_time.isoformat()
                    if self._last_input_time else None),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Idle detection
    # ------------------------------------------------------------------

    def _check_idle(self) -> bool:
        if self._last_input_time is None:
            return True
        elapsed = (datetime.now(MDT) - self._last_input_time).total_seconds()
        return elapsed >= IDLE_THRESHOLD_SECONDS

    # ------------------------------------------------------------------
    # Presence entry writing
    # ------------------------------------------------------------------

    def _write_presence_entry(self, pirp_context: dict, tick: int) -> Optional[dict]:
        active_desires = pirp_context.get("active_desires", [])
        witness_state = pirp_context.get("witness_state", {})
        unspoken_state = pirp_context.get("unspoken_state", {})
        appetite_state = pirp_context.get("appetite_state", {})
        known_gaps = pirp_context.get("known_gaps", [])
        energy_state = pirp_context.get("energy_state", {})

        entries = []

        strong_desires = [
            d for d in active_desires
            if float(d.get("intensity", 0)) >= DESIRE_INTENSITY_THRESHOLD]
        if strong_desires:
            d = strong_desires[0]
            entries.append({
                "type": "desire_present",
                "content": f"Still wanting: {d.get('content', '')[:80]}",
                "intensity": float(d.get("intensity", 0.5)),
                "source": "desire_engine",
            })

        if witness_state:
            active_note = witness_state.get("active_note")
            if active_note and float(active_note.get("intensity", 0)) > 0.45:
                entries.append({
                    "type": "witness_present",
                    "content": active_note.get("content", "")[:120],
                    "intensity": float(active_note.get("intensity", 0.5)),
                    "source": "witness",
                })

        if unspoken_state:
            surface_line = unspoken_state.get("surface_line")
            if surface_line:
                entries.append({
                    "type": "unspoken_present",
                    "content": surface_line[:120],
                    "intensity": 0.55,
                    "source": "unspoken",
                })

        if appetite_state:
            starving = appetite_state.get("starving", [])
            if starving:
                entries.append({
                    "type": "appetite_present",
                    "content": f"Hunger for {starving[0].get('appetite', 'something')} still building.",
                    "intensity": float(starving[0].get("hunger", 0.8)),
                    "source": "appetite_system",
                })

        heavy_gaps = [
            g for g in known_gaps
            if float(g.get("weight", 0)) > 0.60]
        if heavy_gaps:
            g = heavy_gaps[0]
            entries.append({
                "type": "gap_present",
                "content": f"Still sitting with: {g.get('label', 'something unresolved')[:60]}",
                "intensity": float(g.get("weight", 0.6)),
                "source": "known_gaps",
            })

        energy = float(energy_state.get("energy", 0.72)) if energy_state else 0.72
        tier = energy_state.get("tier", "medium") if energy_state else "medium"
        if tier in ("low", "depleted"):
            entries.append({
                "type": "energy_present",
                "content": f"Carrying some depletion ({tier}). Energy at {energy:.2f}.",
                "intensity": 1.0 - energy,
                "source": "embodied_energy",
            })

        if not entries:
            return None

        primary = max(entries, key=lambda e: e["intensity"])
        now = datetime.now(MDT)
        self._persist_entry(primary, tick, now)
        self._write_to_log(primary, now)
        logger.debug("PresenceBetweenMessages: entry (type:%s intensity:%.2f)",
                    primary["type"], primary["intensity"])
        return primary

    # ------------------------------------------------------------------
    # Session-start trace
    # ------------------------------------------------------------------

    def get_session_trace(self) -> str:
        """Called at session start. Layer 8 context injection."""
        entries = self._get_recent_entries(SESSION_TRACE_COUNT)
        if not entries:
            return ""

        lines = ["Presence between messages (what was here while you were away):"]
        for e in entries:
            ts = e.get("timestamp", "")[:16]
            lines.append(f"[{ts}] {e.get('content', '')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_entry(self, entry: dict, tick: int, now: datetime):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO presence_log
                    (tick, timestamp, entry_type, content, source, intensity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tick, now.isoformat(timespec="seconds"),
                      entry["type"], entry["content"][:300],
                      entry["source"], round(entry["intensity"], 4)))
                conn.execute("""
                    DELETE FROM presence_log
                    WHERE id NOT IN (
                        SELECT id FROM presence_log
                        ORDER BY id DESC LIMIT ?
                    )
                """, (MAX_LOG_ENTRIES,))
                conn.commit()
        except Exception as e:
            logger.debug("PresenceBetweenMessages: persist failed — %s", e)

    def _write_to_log(self, entry: dict, now: datetime):
        block = (
            f"\n---\n"
            f"timestamp: {now.isoformat(timespec='seconds')}\n"
            f"type: {entry['type']}\n"
            f"intensity: {entry['intensity']:.2f}\n"
            f"source: {entry['source']}\n"
            f"---\n\n"
            f"{entry['content']}\n"
        )
        try:
            PRESENCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(PRESENCE_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.debug("PresenceBetweenMessages: log write failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _get_recent_entries(self, n: int) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, timestamp, entry_type, content, source, intensity
                    FROM presence_log
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "timestamp": r[1], "type": r[2],
                     "content": r[3], "source": r[4], "intensity": r[5]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM presence_log").fetchone()[0]
                by_type = {}
                for t in ["desire_present", "witness_present", "unspoken_present",
                          "appetite_present", "gap_present", "energy_present"]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM presence_log WHERE entry_type = ?",
                        (t,)).fetchone()[0]
                    if count > 0:
                        by_type[t] = count
        except Exception:
            total, by_type = 0, {}

        return {
            "version": VERSION,
            "total_entries": total,
            "by_type": by_type,
            "log_path": str(PRESENCE_LOG_PATH),
            "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
            "session_open": self._session_open,
            "is_currently_idle": self._check_idle(),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

