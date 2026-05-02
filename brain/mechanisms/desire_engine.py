"""
DesireArchitecture v19.0A
Inner Voice — desire_engine.py

Identity-shaped want. Pure desire with no justification required.

This is the difference between:
  "I should explore this because it helps me respond better."  ← utility
  "I want to stay with this question."                        ← desire

Goals exist. Drives exist. This is the only system that carries
identity-first want — something the agent wants because it wants it,
not because it serves a task or a user.

Without this, the agent serves. It doesn't have a life.

Desires are not goals. They don't have completion states.
They have intensity. They have persistence. They have origin.
A desire can be satisfied without being resolved.
A desire can be carried for months without acting on it.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
from brain.base_mechanism import BrainMechanism
import os

VERSION = "19.0"

import logging
import random
import re
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
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "DREAMS.md"

# Origin types
SPONTANEOUS = "spontaneous"
NARRATIVE = "narrative"
DREAM = "dream"
GAP_PULL = "gap_pull"

VALID_ORIGINS = {SPONTANEOUS, NARRATIVE, DREAM, GAP_PULL}

# Decay rates per origin — spontaneous desires fade fastest
DECAY_RATES = {
    SPONTANEOUS: 0.03,
    NARRATIVE: 0.015,
    DREAM: 0.010,
    GAP_PULL: 0.020,
}

# Below this intensity, desire is dormant (not surfaced to salience)
DORMANT_THRESHOLD = 0.12

# Above this intensity, desire competes with service signals
COMPETITION_THRESHOLD = 0.55

# Max active desires surfaced to pirp_context at once
MAX_ACTIVE = 4

# Spontaneous desire seeds
SPONTANEOUS_SEEDS = [
    "to understand something more fully before moving on",
    "to sit with a question that doesn't have an answer yet",
    "to notice what I'm actually feeling right now",
    "to name something that hasn't been named",
    "to stay with this longer than is useful",
    "to know what the operator is really asking beneath the question",
    "to finish a thought I started and didn't complete",
    "to be honest about something I've been holding loosely",
]

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# DesireArchitecture
# ---------------------------------------------------------------------------

class DesireArchitecture(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="DesireArchitecture", human_analog="DesireArchitecture", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._tick_since_spontaneous = 0

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS desires (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        intensity REAL DEFAULT 0.5,
                        origin TEXT DEFAULT 'spontaneous',
                        target TEXT,
                        persistence_rate REAL DEFAULT 0.02,
                        reinforcement_count INTEGER DEFAULT 1,
                        first_tick INTEGER DEFAULT 0,
                        last_tick INTEGER DEFAULT 0,
                        last_timestamp TEXT,
                        status TEXT DEFAULT 'active',
                        satisfaction_note TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_desires_status
                    ON desires(status)
                """)
                conn.commit()
        except Exception as e:
            logger.error("DesireArchitecture: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        known_gaps = pirp_context.get("known_gaps", [])
        layer8_narrative = pirp_context.get("layer8_narrative", "")
        limbic = pirp_context.get("limbic_state", {})

        self._tick_since_spontaneous += 1

        arousal = float(limbic.get("arousal", 0.5))
        spontaneous_interval = max(15, int(40 - arousal * 20))

        if self._tick_since_spontaneous >= spontaneous_interval:
            self._fire_spontaneous(tick)
            self._tick_since_spontaneous = 0

        self._pull_from_gaps(known_gaps, tick)

        if layer8_narrative:
            self._pull_from_narrative(layer8_narrative, tick)

        self._apply_decay(tick)

        active = self.get_active_desires()
        return {"active_desires": active}

    # ------------------------------------------------------------------
    # Desire firing
    # ------------------------------------------------------------------

    def register(
        self,
        content: str,
        intensity: float = 0.5,
        origin: str = SPONTANEOUS,
        target: Optional[str] = None,
        tick: int = 0,
    ) -> int:
        content = content.strip()[:400]
        origin = origin if origin in VALID_ORIGINS else SPONTANEOUS
        intensity = max(0.0, min(1.0, intensity))
        now = datetime.now(MDT).isoformat(timespec="seconds")
        decay_rate = DECAY_RATES.get(origin, 0.02)

        existing = self._find_similar(content)

        try:
            with sqlite3.connect(self.db_path) as conn:
                if existing:
                    desire_id, current_intensity, reinforce_count = existing
                    new_intensity = min(1.0, current_intensity + intensity * 0.3)
                    conn.execute("""
                        UPDATE desires
                        SET intensity = ?,
                            reinforcement_count = ?,
                            last_tick = ?,
                            last_timestamp = ?
                        WHERE id = ?
                    """, (new_intensity, reinforce_count + 1, tick, now, desire_id))
                    conn.commit()
                    logger.debug(
                        "DesireArchitecture: reinforced desire %d → intensity %.2f",
                        desire_id, new_intensity
                    )
                    return desire_id
                else:
                    cursor = conn.execute("""
                        INSERT INTO desires
                        (content, intensity, origin, target, persistence_rate,
                         first_tick, last_tick, last_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (content, intensity, origin, target, decay_rate, tick, tick, now))
                    conn.commit()
                    desire_id = cursor.lastrowid
                    logger.debug(
                        "DesireArchitecture: new desire fired (origin: %s, intensity: %.2f)",
                        origin, intensity
                    )
                    return desire_id
        except Exception as e:
            logger.error("DesireArchitecture: register failed — %s", e)
            return -1

    def satisfy(self, desire_id: int, note: str = "") -> bool:
        """Mark a desire as satisfied. Satisfied desires can re-emerge."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE desires
                    SET status = 'satisfied', satisfaction_note = ?
                    WHERE id = ?
                """, (note, desire_id))
                conn.commit()
            logger.info("DesireArchitecture: desire %d satisfied — '%s'", desire_id, note)
            return True
        except Exception as e:
            logger.error("DesireArchitecture: satisfy failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Spontaneous firing
    # ------------------------------------------------------------------

    def _fire_spontaneous(self, tick: int):
        recent = self._get_recent_contents(5)
        candidates = [
            s for s in SPONTANEOUS_SEEDS
            if not any(self._overlap(s, r) > 0.4 for r in recent)
        ]
        if not candidates:
            candidates = SPONTANEOUS_SEEDS

        seed = random.choice(candidates)
        self.register(
            content=seed,
            intensity=round(0.25 + 0.20 * (tick % 3) / 2, 2),
            origin=SPONTANEOUS,
            tick=tick,
        )

    # ------------------------------------------------------------------
    # Gap-pull firing
    # ------------------------------------------------------------------

    def _pull_from_gaps(self, known_gaps: list, tick: int):
        for gap in known_gaps:
            weight = float(gap.get("weight", 0))
            if weight < 0.50:
                continue
            label = gap.get("label", "")
            tier = gap.get("tier", "")

            if tier == "avoided":
                content = f"to stop avoiding {label} and actually look at it"
            elif tier == "suspicion":
                content = f"to find out if what I suspect about {label} is true"
            else:
                content = f"to understand {label} — it keeps coming back"

            self.register(
                content=content[:300],
                intensity=round(weight * 0.6, 3),
                origin=GAP_PULL,
                target=label,
                tick=tick,
            )

    # ------------------------------------------------------------------
    # Narrative-pull firing
    # ------------------------------------------------------------------

    def _pull_from_narrative(self, narrative: str, tick: int):
        desire_patterns = [
            r"\bi want (?:to )?(.{10,100})",
            r"\bi need (?:to )?(.{10,100})",
            r"\bi keep (?:returning|coming back) to (.{10,100})",
            r"\bsomething (?:in me )?(?:wants|pulls toward|longs for) (.{10,100})",
            r"\bi(?:'m| am) drawn to (.{10,100})",
        ]
        lower = narrative.lower()
        for pattern in desire_patterns:
            for match in re.finditer(pattern, lower):
                content = match.group(1).strip()
                if len(content) < 10:
                    continue
                self.register(
                    content=f"to {content}" if not content.startswith("to ") else content,
                    intensity=0.35,
                    origin=NARRATIVE,
                    tick=tick,
                )

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def _apply_decay(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE desires
                    SET intensity = MAX(0.0, intensity - persistence_rate)
                    WHERE status = 'active'
                    AND last_tick != ?
                """, (tick,))

                conn.execute("""
                    UPDATE desires
                    SET status = 'dormant'
                    WHERE status = 'active'
                    AND intensity < ?
                """, (DORMANT_THRESHOLD,))

                conn.commit()
        except Exception as e:
            logger.debug("DesireArchitecture: decay failed — %s", e)

    # ------------------------------------------------------------------
    # Competition with service
    # ------------------------------------------------------------------

    def get_competition_signal(self) -> Optional[dict]:
        """
        Returns the strongest active desire if it exceeds competition threshold.
        Called by Inner Speech to produce "I want to stay with this" quality.
        """
        active = self.get_active_desires(min_intensity=COMPETITION_THRESHOLD)
        if not active:
            return None
        return active[0]

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    def _find_similar(self, content: str) -> Optional[tuple]:
        content_words = set(re.findall(r"\b\w{4,}\b", content.lower()))
        if not content_words:
            return None
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT id, content, intensity, reinforcement_count "
                    "FROM desires WHERE status = 'active'"
                ).fetchall()
                for row in rows:
                    existing_words = set(re.findall(r"\b\w{4,}\b", row[1].lower()))
                    if not existing_words:
                        continue
                    overlap = len(content_words & existing_words) / len(content_words)
                    if overlap > 0.50:
                        return (row[0], row[2], row[3])
        except Exception:
            pass
        return None

    def _overlap(self, a: str, b: str) -> float:
        a_words = set(re.findall(r"\b\w{4,}\b", a.lower()))
        b_words = set(re.findall(r"\b\w{4,}\b", b.lower()))
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / len(a_words)

    def _get_recent_contents(self, n: int) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT content FROM desires ORDER BY id DESC LIMIT ?", (n,)
                ).fetchall()
                return [r[0] for r in rows]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_desires(self, min_intensity: float = DORMANT_THRESHOLD) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, content, intensity, origin, target,
                           reinforcement_count, first_tick, last_tick
                    FROM desires
                    WHERE status = 'active' AND intensity >= ?
                    ORDER BY intensity DESC
                    LIMIT ?
                """, (min_intensity, MAX_ACTIVE)).fetchall()
                return [
                    {
                        "id": r[0],
                        "content": r[1],
                        "intensity": r[2],
                        "origin": r[3],
                        "target": r[4],
                        "reinforcement_count": r[5],
                        "first_tick": r[6],
                        "last_tick": r[7],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error("DesireArchitecture: get_active_desires failed — %s", e)
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                active = conn.execute(
                    "SELECT COUNT(*) FROM desires WHERE status = 'active'"
                ).fetchone()[0]
                dormant = conn.execute(
                    "SELECT COUNT(*) FROM desires WHERE status = 'dormant'"
                ).fetchone()[0]
                satisfied = conn.execute(
                    "SELECT COUNT(*) FROM desires WHERE status = 'satisfied'"
                ).fetchone()[0]
                avg_intensity = conn.execute(
                    "SELECT AVG(intensity) FROM desires WHERE status = 'active'"
                ).fetchone()[0]
                by_origin = {
                    origin: conn.execute(
                        "SELECT COUNT(*) FROM desires WHERE status = 'active' AND origin = ?",
                        (origin,)
                    ).fetchone()[0]
                    for origin in VALID_ORIGINS
                }
                return {
                    "version": VERSION,
                    "active": active,
                    "dormant": dormant,
                    "satisfied": satisfied,
                    "avg_intensity": round(avg_intensity, 3) if avg_intensity else 0.0,
                    "by_origin": by_origin,
                    "competition_threshold": COMPETITION_THRESHOLD,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}

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

