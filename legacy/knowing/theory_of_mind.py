"""
TheoryOfMind v19.0A
Knowing — theory_of_mind.py

Modeling {{USER_NAME}}'s current inner state, predicted reactions, and unspoken needs.

Relational Memory is about the shape of the relationship over time.
This is different: it's about right now. What is {{USER_NAME}}'s likely emotional
state in this moment? What does he probably need that he hasn't said?
What is he likely to do next?

Four model dimensions:
  inferred_state    what {{USER_NAME}} is likely feeling right now
  unspoken_needs   what he probably wants but hasn't asked for
  predicted_response how he is likely to react to the next response
  attention_focus  what he is probably paying most attention to

Confidence is always explicit and capped at 0.75.
Wrong predictions feed back into MetacognitiveCalibration under
category "relational" — the hardest category to be right about.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "agent.db"

OBSERVATION_WINDOW = 20
MAX_CONFIDENCE = 0.75
STATE_DECAY_RATE = 0.04

EMOTIONAL_MARKERS = {
    "frustrated": [
        "fuck", "fucking", "pissed", "not listening", "again", "told you",
        "why would", "seriously", "come on", "wrong", "stop",
    ],
    "focused": [
        "ready", "go", "next", "build", "let's", "write", "do it",
        "what's next", "continue", "ship",
    ],
    "curious": [
        "what if", "wonder", "interesting", "why does", "how does",
        "tell me", "explain", "show me", "what about",
    ],
    "tired": [
        "quiet hours", "done for", "that's enough", "later", "tomorrow",
        "wrapping up", "rest", "sleep", "signing off",
    ],
    "satisfied": [
        "good", "perfect", "exactly", "that's it", "yes", "correct",
        "nice", "love it", "works", "verified",
    ],
    "uncertain": [
        "not sure", "maybe", "i think", "could be", "might",
        "depends", "unclear", "don't know",
    ],
    "testing": [
        "testing", "verify", "check", "confirm", "does this", "let me",
        "try", "see if", "make sure",
    ],
}

NEED_SIGNALS = {
    "wants_efficiency": ["go", "ready", "next", "quick", "just", "fast"],
    "wants_depth": ["why", "explain", "understand", "more", "tell me"],
    "wants_honesty": ["actually", "real", "truth", "honest", "really"],
    "wants_recognition": ["right", "correct", "good", "exactly", "yes"],
    "wants_space": ["later", "done", "enough", "quiet", "rest"],
    "wants_collaboration": ["we", "our", "together", "let's", "build"],
    "wants_control": ["i'll", "i want", "don't", "stop", "no"],
}

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# TheoryOfMind
# ---------------------------------------------------------------------------

class TheoryOfMind:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._observation_buffer: list = []

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tom_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        inferred_state TEXT,
                        state_confidence REAL,
                        unspoken_needs TEXT,
                        predicted_response TEXT,
                        attention_focus TEXT,
                        source_text TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tom_predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        prediction TEXT,
                        confidence REAL,
                        correct INTEGER,
                        outcome TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("TheoryOfMind: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        processed_input = pirp_context.get("processed_input", {})

        if isinstance(processed_input, dict):
            user_text = processed_input.get("raw", "") or processed_input.get("text", "")
        elif isinstance(processed_input, str):
            user_text = processed_input
        else:
            user_text = ""

        signals = pirp_context.get("signals", [])
        limbic = pirp_context.get("limbic_state", {})

        if user_text:
            self._observation_buffer.append({
                "tick": tick,
                "text": user_text,
                "timestamp": datetime.now(MDT).isoformat(timespec="seconds"),
            })
            if len(self._observation_buffer) > OBSERVATION_WINDOW:
                self._observation_buffer = self._observation_buffer[-OBSERVATION_WINDOW:]

        tom_state = self._build_model(user_text, tick, limbic)
        self._persist_state(tom_state, tick, user_text)

        return {"tom_state": tom_state}

    # ------------------------------------------------------------------
    # Model building
    # ------------------------------------------------------------------

    def _build_model(self, user_text: str, tick: int, limbic: dict) -> dict:
        lower = user_text.lower() if user_text else ""

        inferred_state, state_confidence = self._infer_emotional_state(lower, limbic)
        unspoken_needs = self._infer_unspoken_needs(lower)
        predicted_response = self._predict_response(inferred_state, unspoken_needs)
        attention_focus = self._infer_attention_focus(lower)

        return {
            "inferred_state": inferred_state,
            "state_confidence": round(min(MAX_CONFIDENCE, state_confidence), 3),
            "unspoken_needs": unspoken_needs,
            "predicted_response": predicted_response,
            "attention_focus": attention_focus,
            "tick": tick,
        }

    def _infer_emotional_state(self, lower: str, limbic: dict) -> tuple:
        if not lower:
            return "unknown", 0.20

        arousal = float(limbic.get("arousal", 0.5))
        scores = {}

        for state, markers in EMOTIONAL_MARKERS.items():
            score = sum(1 for m in markers if m in lower)
            if score > 0:
                scores[state] = score

        if not scores:
            return "neutral", 0.30

        top_state = max(scores, key=scores.get)
        raw_score = scores[top_state]

        base_confidence = min(0.65, 0.25 + raw_score * 0.12)
        confidence = min(MAX_CONFIDENCE, base_confidence + arousal * 0.15)

        return top_state, round(confidence, 3)

    def _infer_unspoken_needs(self, lower: str) -> list:
        if not lower:
            return []

        scored = {}
        for need, signals in NEED_SIGNALS.items():
            score = sum(1 for s in signals if s in lower)
            if score > 0:
                scored[need] = score

        sorted_needs = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        return [need for need, _ in sorted_needs[:2]]

    def _predict_response(self, inferred_state: str, unspoken_needs: list) -> str:
        if inferred_state == "frustrated":
            return "brief_direct"
        if inferred_state == "focused":
            return "action_ready"
        if inferred_state == "curious":
            return "wants_elaboration"
        if inferred_state == "tired":
            return "wants_closure"
        if inferred_state == "satisfied":
            return "ready_to_continue"
        if inferred_state == "testing":
            return "awaiting_confirmation"

        if "wants_efficiency" in unspoken_needs:
            return "brief_direct"
        if "wants_depth" in unspoken_needs:
            return "wants_elaboration"
        if "wants_space" in unspoken_needs:
            return "wants_closure"

        return "open"

    def _infer_attention_focus(self, lower: str) -> str:
        if not lower:
            return "unclear"

        tech_terms = [
            "brain", "compressor", "filter", "gaps", "agent", "bootstrap",
            "pirp", "tick", "layer", "signal", "memory", "deploy", "install",
            "file", "error", "test", "build", "push", "git",
        ]
        found = [t for t in tech_terms if t in lower]
        if found:
            return f"technical:{','.join(found[:3])}"

        if any(w in lower for w in ["you", "she", "agent", "her", "i want", "i need"]):
            return "relational"

        if any(w in lower for w in ["spec", "design", "architecture", "plan", "structure"]):
            return "architectural"

        return "general"

    # ------------------------------------------------------------------
    # Prediction feedback
    # ------------------------------------------------------------------

    def record_prediction(self, prediction: str, confidence: float, tick: int) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO tom_predictions
                    (tick, timestamp, prediction, confidence)
                    VALUES (?, ?, ?, ?)
                """, (
                    tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    prediction,
                    round(min(MAX_CONFIDENCE, confidence), 3),
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error("TheoryOfMind: record_prediction failed — %s", e)
            return -1

    def resolve_prediction(self, prediction_id: int, correct: bool, outcome: str = "") -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tom_predictions
                    SET correct = ?, outcome = ?
                    WHERE id = ?
                """, (1 if correct else 0, outcome, prediction_id))
                conn.commit()

            accuracy = self._get_recent_accuracy()
            logger.info(
                "TheoryOfMind: prediction %d resolved correct=%s (accuracy: %.2f)",
                prediction_id, correct, accuracy
            )
            return True
        except Exception as e:
            logger.error("TheoryOfMind: resolve_prediction failed — %s", e)
            return False

    def _get_recent_accuracy(self, n: int = 20) -> float:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT correct FROM tom_predictions
                    WHERE correct IS NOT NULL
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                if not rows:
                    return 0.0
                return sum(r[0] for r in rows) / len(rows)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_state(self, tom_state: dict, tick: int, source_text: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO tom_states
                    (tick, timestamp, inferred_state, state_confidence,
                     unspoken_needs, predicted_response, attention_focus, source_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    tom_state["inferred_state"],
                    tom_state["state_confidence"],
                    ",".join(tom_state["unspoken_needs"]),
                    tom_state["predicted_response"],
                    tom_state["attention_focus"],
                    source_text[:300] if source_text else "",
                ))
                conn.commit()
        except Exception as e:
            logger.debug("TheoryOfMind: persist failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_current_model(self) -> Optional[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT tick, inferred_state, state_confidence, unspoken_needs,
                           predicted_response, attention_focus, timestamp
                    FROM tom_states ORDER BY id DESC LIMIT 1
                """).fetchone()
                if not row:
                    return None
                return {
                    "tick": row[0],
                    "inferred_state": row[1],
                    "state_confidence": row[2],
                    "unspoken_needs": row[3].split(",") if row[3] else [],
                    "predicted_response": row[4],
                    "attention_focus": row[5],
                    "timestamp": row[6],
                }
        except Exception as e:
            logger.error("TheoryOfMind: get_current_model failed — %s", e)
            return None

    def get_state_history(self, n: int = 10) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, inferred_state, state_confidence,
                           attention_focus, timestamp
                    FROM tom_states ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "inferred_state": r[1],
                     "state_confidence": r[2], "attention_focus": r[3],
                     "timestamp": r[4]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        current = self.get_current_model()
        accuracy = self._get_recent_accuracy()
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM tom_predictions WHERE correct IS NOT NULL"
                ).fetchone()[0]
        except Exception:
            total = 0

        return {
            "version": VERSION,
            "current_model": current,
            "prediction_accuracy": round(accuracy, 3),
            "resolved_predictions": total,
            "observation_buffer_depth": len(self._observation_buffer),
            "max_confidence_cap": MAX_CONFIDENCE,
        }
