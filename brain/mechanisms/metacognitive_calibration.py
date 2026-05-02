"""
MetacognitiveCalibration v19.0A
Knowing — metacognitive_calibration.py

Confidence scoring across what the brain thinks it knows.

Not just Known Gaps (what it doesn't know) — this is epistemic uncertainty
gradients on what it *thinks* it knows.

Every belief, insight, and narrative claim the brain produces gets
a confidence score and a stability rating. These feed:
  - Inner Speech (hesitation, qualification, tone)
  - Productive Conflict (low-confidence beliefs challenge each other more)
  - Narrative Engine (unstable beliefs get revisited)
  - SalienceFilter (low-confidence signals get novelty bonus)

Three dimensions per belief:
  confidence  0.0–1.0  how certain the brain is this is true
  stability   enum      volatile | forming | stable
  category    str      what domain this belief lives in

Categories track error history. If the brain has been wrong about
relational beliefs before, new relational beliefs start lower.
Calibration is earned, not assumed.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
from brain.base_mechanism import BrainMechanism
import os

VERSION = "19.0"

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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "brain" / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Stability tiers
VOLATILE = "volatile"
FORMING = "forming"
STABLE = "stable"

# Confidence thresholds for stability transitions
FORMING_THRESHOLD = 0.40
STABLE_THRESHOLD = 0.70

# Default starting confidence by category
CATEGORY_DEFAULTS = {
    "relational": 0.45,
    "emotional": 0.50,
    "predictive": 0.40,
    "factual": 0.70,
    "identity": 0.60,
    "narrative": 0.55,
    "default": 0.50,
}

CORRECT_BOOST = 0.05
WRONG_PENALTY = 0.08

STALE_TICK_WINDOW = 50
STALE_DECAY = 0.01

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# MetacognitiveCalibration
# ---------------------------------------------------------------------------

class MetacognitiveCalibration(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="MetacognitiveCalibration", human_analog="MetacognitiveCalibration", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS beliefs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        label TEXT NOT NULL,
                        content TEXT,
                        category TEXT DEFAULT 'default',
                        confidence REAL DEFAULT 0.5,
                        stability TEXT DEFAULT 'volatile',
                        reinforcement_count INTEGER DEFAULT 1,
                        error_count INTEGER DEFAULT 0,
                        first_tick INTEGER DEFAULT 0,
                        last_tick INTEGER DEFAULT 0,
                        last_timestamp TEXT,
                        status TEXT DEFAULT 'active',
                        source TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS category_calibration (
                        category TEXT PRIMARY KEY,
                        confidence_ceiling REAL DEFAULT 0.80,
                        error_count INTEGER DEFAULT 0,
                        correct_count INTEGER DEFAULT 0,
                        last_updated TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_beliefs_label
                    ON beliefs(label)
                """)
                conn.commit()
                self._seed_category_calibration(conn)
        except Exception as e:
            logger.error("MetacognitiveCalibration: table init failed — %s", e)

    def _seed_category_calibration(self, conn):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        for category, default_conf in CATEGORY_DEFAULTS.items():
            conn.execute("""
                INSERT OR IGNORE INTO category_calibration
                (category, confidence_ceiling, last_updated)
                VALUES (?, ?, ?)
            """, (category, min(0.95, default_conf + 0.30), now))
        conn.commit()

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        signals = pirp_context.get("signals", [])
        layer8_narrative = pirp_context.get("layer8_narrative", "")

        for sig in signals:
            text = sig.get("text", "")
            if text:
                self._extract_beliefs_from_text(text, tick, source="signal")

        if layer8_narrative:
            self._extract_beliefs_from_text(layer8_narrative, tick, source="narrative")

        self._apply_stale_decay(tick)

        return {
            "metacognitive_state": self.get_state(),
            "low_confidence_beliefs": self.get_low_confidence(threshold=0.40),
            "volatile_beliefs": self.get_by_stability(VOLATILE),
        }

    # ------------------------------------------------------------------
    # Belief registration
    # ------------------------------------------------------------------

    def register_belief(
        self,
        label: str,
        content: str,
        category: str = "default",
        tick: int = 0,
        source: str = "manual",
        initial_confidence: Optional[float] = None,
    ) -> int:
        label = label.strip().lower()[:200]
        category = category if category in CATEGORY_DEFAULTS else "default"
        now = datetime.now(MDT).isoformat(timespec="seconds")
        ceiling = self._get_category_ceiling(category)

        if initial_confidence is None:
            initial_confidence = min(ceiling, CATEGORY_DEFAULTS.get(category, 0.50))

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, confidence, reinforcement_count, stability FROM beliefs "
                    "WHERE label = ? AND status = 'active'",
                    (label,)
                ).fetchone()

                if row:
                    belief_id, current_conf, reinforce_count, stability = row
                    new_conf, new_stability = self._update_confidence(
                        current_conf, reinforce_count, ceiling, stability
                    )
                    conn.execute("""
                        UPDATE beliefs
                        SET confidence = ?,
                            stability = ?,
                            reinforcement_count = ?,
                            last_tick = ?,
                            last_timestamp = ?,
                            content = COALESCE(?, content)
                        WHERE id = ?
                    """, (new_conf, new_stability, reinforce_count + 1, tick, now,
                          content[:500] if content else None, belief_id))
                    conn.commit()
                    return belief_id
                else:
                    cursor = conn.execute("""
                        INSERT INTO beliefs
                        (label, content, category, confidence, stability,
                         first_tick, last_tick, last_timestamp, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (label, content[:500], category, initial_confidence,
                          VOLATILE, tick, tick, now, source))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error("MetacognitiveCalibration: register failed — %s", e)
            return -1

    def record_error(self, label: str, note: str = "") -> bool:
        label = label.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, confidence, category, error_count FROM beliefs "
                    "WHERE label = ? AND status = 'active'",
                    (label,)
                ).fetchone()
                if not row:
                    return False

                belief_id, current_conf, category, error_count = row
                new_conf = max(0.05, current_conf - 0.20)

                conn.execute("""
                    UPDATE beliefs
                    SET confidence = ?, stability = ?, error_count = ?
                    WHERE id = ?
                """, (new_conf, VOLATILE, error_count + 1, belief_id))

                conn.execute("""
                    UPDATE category_calibration
                    SET confidence_ceiling = MAX(0.40, confidence_ceiling - ?),
                        error_count = error_count + 1,
                        last_updated = ?
                    WHERE category = ?
                """, (WRONG_PENALTY, datetime.now(MDT).isoformat(timespec="seconds"), category))

                conn.commit()
                logger.info("MetacognitiveCalibration: error recorded '%s' → conf %.2f", label, new_conf)
                return True
        except Exception as e:
            logger.error("MetacognitiveCalibration: record_error failed — %s", e)
            return False

    def record_correct(self, label: str) -> bool:
        label = label.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT category FROM beliefs WHERE label = ? AND status = 'active'",
                    (label,)
                ).fetchone()
                if not row:
                    return False
                _, category = row
                conn.execute("""
                    UPDATE category_calibration
                    SET confidence_ceiling = MIN(0.95, confidence_ceiling + ?),
                        correct_count = correct_count + 1,
                        last_updated = ?
                    WHERE category = ?
                """, (CORRECT_BOOST, datetime.now(MDT).isoformat(timespec="seconds"), category))
                conn.commit()
                return True
        except Exception as e:
            logger.error("MetacognitiveCalibration: record_correct failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Belief extraction from text
    # ------------------------------------------------------------------

    def _extract_beliefs_from_text(self, text: str, tick: int, source: str):
        belief_patterns = [
            (r"\bi (?:know|believe|think|feel|sense|understand) (?:that )?(.{10,100})", "assertion"),
            (r"\bi(?:'m| am) (?:sure|certain|confident) (?:that )?(.{10,100})", "assertion"),
            (r"\bthis (?:means|is|shows) (?:that )?(.{10,80})", "interpretive"),
            (r"\b(?:always|never|every time) (.{10,80})", "pattern"),
            (r"\boperator (?:is|wants|feels|needs|thinks) (.{10,80})", "relational"),
        ]
        category_map = {
            "assertion": "default",
            "interpretive": "narrative",
            "pattern": "predictive",
            "relational": "relational",
        }

        lower = text.lower()
        for pattern, belief_type in belief_patterns:
            for match in re.finditer(pattern, lower):
                content = match.group(1).strip()
                if len(content) < 10:
                    continue
                label_words = re.findall(r"\b\w{4,}\b", content)[:5]
                if len(label_words) < 2:
                    continue
                label = f"{belief_type}:{' '.join(label_words)}"
                category = category_map.get(belief_type, "default")
                self.register_belief(label, content, category, tick, source)

    # ------------------------------------------------------------------
    # Confidence mechanics
    # ------------------------------------------------------------------

    def _update_confidence(
        self,
        current: float,
        reinforce_count: int,
        ceiling: float,
        current_stability: str,
    ) -> tuple:
        boost = 0.08 / (1 + reinforce_count * 0.2)
        new_conf = min(ceiling, current + boost)

        if new_conf >= STABLE_THRESHOLD:
            new_stability = STABLE
        elif new_conf >= FORMING_THRESHOLD:
            new_stability = FORMING
        else:
            new_stability = VOLATILE

        return round(new_conf, 4), new_stability

    def _get_category_ceiling(self, category: str) -> float:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT confidence_ceiling FROM category_calibration WHERE category = ?",
                    (category,)
                ).fetchone()
                return float(row[0]) if row else 0.80
        except Exception:
            return 0.80

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def _apply_stale_decay(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE beliefs
                    SET confidence = MAX(0.05, confidence - ?)
                    WHERE status = 'active'
                    AND (? - last_tick) > ?
                """, (STALE_DECAY, tick, STALE_TICK_WINDOW))
                conn.commit()
        except Exception as e:
            logger.debug("MetacognitiveCalibration: stale decay failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_belief(self, label: str) -> Optional[dict]:
        label = label.strip().lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT id, label, content, category, confidence, stability,
                           reinforcement_count, error_count, last_tick
                    FROM beliefs WHERE label = ? AND status = 'active'
                """, (label,)).fetchone()
                if not row:
                    return None
                return {
                    "id": row[0], "label": row[1], "content": row[2],
                    "category": row[3], "confidence": row[4], "stability": row[5],
                    "reinforcement_count": row[6], "error_count": row[7],
                    "last_tick": row[8],
                }
        except Exception as e:
            logger.error("MetacognitiveCalibration: get_belief failed — %s", e)
            return None

    def get_low_confidence(self, threshold: float = 0.40) -> list:
        """Returns beliefs below threshold — used by Inner Speech for hesitation."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT label, content, category, confidence, stability
                    FROM beliefs
                    WHERE status = 'active' AND confidence < ?
                    ORDER BY confidence ASC LIMIT 10
                """, (threshold,)).fetchall()
                return [
                    {"label": r[0], "content": r[1], "category": r[2],
                     "confidence": r[3], "stability": r[4]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_by_stability(self, stability: str) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT label, content, category, confidence
                    FROM beliefs
                    WHERE status = 'active' AND stability = ?
                    ORDER BY confidence DESC LIMIT 15
                """, (stability,)).fetchall()
                return [
                    {"label": r[0], "content": r[1], "category": r[2], "confidence": r[3]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_category_summary(self) -> list:
        """Returns calibration state per category — consumed by The Witness."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT c.category, c.confidence_ceiling, c.error_count, c.correct_count,
                           COUNT(b.id) as belief_count, AVG(b.confidence) as avg_confidence
                    FROM category_calibration c
                    LEFT JOIN beliefs b ON b.category = c.category AND b.status = 'active'
                    GROUP BY c.category
                    ORDER BY avg_confidence ASC
                """).fetchall()
                return [
                    {
                        "category": r[0],
                        "ceiling": round(r[1], 3),
                        "errors": r[2],
                        "correct": r[3],
                        "belief_count": r[4] or 0,
                        "avg_confidence": round(r[5], 3) if r[5] else 0.0,
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM beliefs WHERE status = 'active'"
                ).fetchone()[0]
                by_stability = {
                    s: conn.execute(
                        "SELECT COUNT(*) FROM beliefs WHERE status = 'active' AND stability = ?",
                        (s,)
                    ).fetchone()[0]
                    for s in [VOLATILE, FORMING, STABLE]
                }
                avg_conf = conn.execute(
                    "SELECT AVG(confidence) FROM beliefs WHERE status = 'active'"
                ).fetchone()[0]
                return {
                    "version": VERSION,
                    "active_beliefs": total,
                    "by_stability": by_stability,
                    "avg_confidence": round(avg_conf, 3) if avg_conf else 0.0,
                    "category_summary": self.get_category_summary(),
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

