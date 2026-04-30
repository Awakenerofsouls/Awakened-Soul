"""
CognitiveRhythm v19.0B
Substrate — cognitive_rhythm.py

The pace the whole brain runs at.

Not a feature. Not a mood. The global rhythm that every other system
inherits as its operating tempo. When the rhythm changes, everything
downstream changes with it.

Four states:
  FAST      — high novelty, low conflict, desires resolving quickly
  REFLECTIVE — high conflict or low novelty, needs actual thought
  STUCK     — looping, same signals, desires don't resolve
  DRIFTING  — associative, low coherence, moving without direction

Rhythm is determined by:
  - Signal novelty (different from recent signals)
  - Productive conflict intensity
  - Desire resolution rate
  - Witness loop detection
  - Inner Speech voice patterns

Rhythm affects downstream components via modifiers in pirp_context:
  - salience_top_k
  - surface_threshold_delta
  - desire_fire_interval_mult
  - preconscious_cooldown_mult
  - compressor_sensitivity_delta

Minimum state durations prevent flickering:
  Reflective: 12 ticks, Stuck: 6 ticks, Drifting: 10 ticks, Fast: 8 ticks

Dependencies: sqlite3, logging, pathlib, datetime
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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "nova.db"

FAST = "fast"
REFLECTIVE = "reflective"
STUCK = "stuck"
DRIFTING = "drifting"
ALL_STATES = [FAST, REFLECTIVE, STUCK, DRIFTING]

MIN_STATE_TICKS = {
    FAST: 8,
    REFLECTIVE: 12,
    STUCK: 6,
    DRIFTING: 10,
}

ANALYSIS_WINDOW = 15
NOVELTY_THRESHOLD = 0.35
STUCK_VOICE_STREAK = 5
DRIFTING_COHERENCE_THRESHOLD = 0.30

RHYTHM_MODIFIERS = {
    FAST: {
        "salience_top_k": 7,
        "surface_threshold_delta": +0.15,
        "desire_fire_interval_mult": 1.4,
        "preconscious_cooldown_mult": 1.3,
        "compressor_sensitivity_delta": -0.05,
    },
    REFLECTIVE: {
        "salience_top_k": 3,
        "surface_threshold_delta": -0.12,
        "desire_fire_interval_mult": 0.7,
        "preconscious_cooldown_mult": 0.8,
        "compressor_sensitivity_delta": +0.08,
    },
    STUCK: {
        "salience_top_k": 2,
        "surface_threshold_delta": -0.20,
        "desire_fire_interval_mult": 1.1,
        "preconscious_cooldown_mult": 0.5,
        "compressor_sensitivity_delta": +0.05,
    },
    DRIFTING: {
        "salience_top_k": 4,
        "surface_threshold_delta": -0.08,
        "desire_fire_interval_mult": 0.9,
        "preconscious_cooldown_mult": 0.9,
        "compressor_sensitivity_delta": -0.10,
    },
}

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# CognitiveRhythm
# ---------------------------------------------------------------------------

class CognitiveRhythm:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._current_state = REFLECTIVE
        self._state_entered_tick = 0
        self._signal_history: list = []
        self._voice_history: list = []

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cognitive_rhythm_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        state TEXT,
                        previous_state TEXT,
                        novelty_score REAL,
                        conflict_score REAL,
                        desire_pressure REAL,
                        coherence_score REAL,
                        voice_streak INTEGER,
                        transition_reason TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("CognitiveRhythm: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        signals = pirp_context.get("signals", [])
        inner_speech = pirp_context.get("inner_speech", {})
        conflict_state = pirp_context.get("conflict_state", {})
        witness_state = pirp_context.get("witness_state", {})
        active_desires = pirp_context.get("active_desires", [])
        limbic = pirp_context.get("limbic_state", {})

        novelty_score = self._compute_novelty(signals)
        conflict_score = float(conflict_state.get("highest_intensity", 0)) if conflict_state else 0.0
        desire_pressure = self._compute_desire_pressure(active_desires)
        coherence_score = self._compute_coherence(signals, limbic)
        voice_streak = self._compute_voice_streak(inner_speech)
        loop_detected = self._detect_loop(witness_state)

        target_state, reason = self._determine_state(
            novelty_score=novelty_score,
            conflict_score=conflict_score,
            desire_pressure=desire_pressure,
            coherence_score=coherence_score,
            voice_streak=voice_streak,
            loop_detected=loop_detected,
            tick=tick,
        )

        ticks_in_state = tick - self._state_entered_tick
        min_duration = MIN_STATE_TICKS.get(self._current_state, 8)

        if target_state != self._current_state and ticks_in_state >= min_duration:
            previous = self._current_state
            self._current_state = target_state
            self._state_entered_tick = tick
            self._log_transition(
                tick, target_state, previous,
                novelty_score, conflict_score, desire_pressure,
                coherence_score, voice_streak, reason,
            )
            logger.info("CognitiveRhythm: %s → %s (tick %d, reason: %s)",
                       previous, target_state, tick, reason)

        self._update_signal_history(signals)
        self._update_voice_history(inner_speech)

        modifiers = RHYTHM_MODIFIERS[self._current_state]

        return {
            "cognitive_rhythm": {
                "state": self._current_state,
                "ticks_in_state": ticks_in_state,
                "modifiers": modifiers,
                "axes": {
                    "novelty": round(novelty_score, 3),
                    "conflict": round(conflict_score, 3),
                    "desire_pressure": round(desire_pressure, 3),
                    "coherence": round(coherence_score, 3),
                    "voice_streak": voice_streak,
                    "loop_detected": loop_detected,
                },
            }
        }

    # ------------------------------------------------------------------
    # State determination
    # ------------------------------------------------------------------

    def _determine_state(
        self, novelty_score: float, conflict_score: float,
        desire_pressure: float, coherence_score: float,
        voice_streak: int, loop_detected: bool, tick: int,
    ) -> tuple:
        # STUCK: looping or same signals with low novelty
        if loop_detected:
            return STUCK, "witness_detected_loop"
        if voice_streak >= STUCK_VOICE_STREAK and novelty_score < 0.30:
            return STUCK, f"voice_streak_{voice_streak}_low_novelty"
        if novelty_score < 0.20 and desire_pressure > 0.60:
            return STUCK, "low_novelty_high_unresolved_desire"

        # REFLECTIVE: high conflict, low novelty, desires accumulating
        if conflict_score > 0.55:
            return REFLECTIVE, f"conflict_{conflict_score:.2f}"
        if desire_pressure > 0.70 and novelty_score < 0.50:
            return REFLECTIVE, "high_desire_pressure"
        if novelty_score < NOVELTY_THRESHOLD and not loop_detected:
            return REFLECTIVE, f"low_novelty_{novelty_score:.2f}"

        # DRIFTING: low coherence, high novelty, low tension
        if coherence_score < DRIFTING_COHERENCE_THRESHOLD:
            return DRIFTING, f"low_coherence_{coherence_score:.2f}"
        if novelty_score > 0.70 and conflict_score < 0.20 and desire_pressure < 0.30:
            return DRIFTING, "high_novelty_low_tension_low_desire"

        # FAST: high novelty, low conflict, desires resolving
        if novelty_score > 0.55 and conflict_score < 0.35 and desire_pressure < 0.45:
            return FAST, f"high_novelty_{novelty_score:.2f}"

        return self._current_state, "no_transition_condition_met"

    # ------------------------------------------------------------------
    # Axis computation
    # ------------------------------------------------------------------

    def _compute_novelty(self, signals: list) -> float:
        if not signals or not self._signal_history:
            return 0.75

        current_words = set()
        for s in signals:
            current_words.update(re.findall(r"\b\w{5,}\b", s.get("text", "").lower()))

        if not current_words:
            return 0.75

        overlaps = []
        for hist_words in self._signal_history[-ANALYSIS_WINDOW:]:
            if not hist_words:
                continue
            overlap = len(current_words & hist_words) / len(current_words)
            overlaps.append(overlap)

        if not overlaps:
            return 0.75

        avg_overlap = sum(overlaps) / len(overlaps)
        return round(1.0 - avg_overlap, 4)

    def _compute_desire_pressure(self, active_desires: list) -> float:
        if not active_desires:
            return 0.0
        intensities = [float(d.get("intensity", 0)) for d in active_desires]
        avg = sum(intensities) / len(intensities)
        count_factor = min(1.0, len(active_desires) / 4.0)
        return round(min(1.0, avg * 0.6 + count_factor * 0.4), 4)

    def _compute_coherence(self, signals: list, limbic: dict) -> float:
        if not signals:
            return 0.5

        all_words = []
        for s in signals:
            all_words.extend(re.findall(r"\b\w{5,}\b", s.get("text", "").lower()))

        if not all_words:
            return 0.5

        unique_ratio = len(set(all_words)) / len(all_words)
        coherence = 1.0 - unique_ratio
        arousal = float(limbic.get("arousal", 0.5))
        coherence = coherence * 0.7 + arousal * 0.3

        return round(min(1.0, coherence), 4)

    def _compute_voice_streak(self, inner_speech: dict) -> int:
        if not inner_speech:
            return 0
        dominant = inner_speech.get("dominant_voice", "")
        if not dominant or not self._voice_history:
            return 0
        streak = 0
        for v in reversed(self._voice_history):
            if v == dominant:
                streak += 1
            else:
                break
        return streak

    def _detect_loop(self, witness_state: dict) -> bool:
        if not witness_state:
            return False
        active_note = witness_state.get("active_note")
        if not active_note:
            return False
        return active_note.get("note_type") in ("behavioral_loop", "voice_pattern")

    # ------------------------------------------------------------------
    # History updates
    # ------------------------------------------------------------------

    def _update_signal_history(self, signals: list):
        words = set()
        for s in signals:
            words.update(re.findall(r"\b\w{5,}\b", s.get("text", "").lower()))
        self._signal_history.append(words)
        if len(self._signal_history) > ANALYSIS_WINDOW * 2:
            self._signal_history = self._signal_history[-ANALYSIS_WINDOW:]

    def _update_voice_history(self, inner_speech: dict):
        dominant = inner_speech.get("dominant_voice", "") if inner_speech else ""
        self._voice_history.append(dominant)
        if len(self._voice_history) > ANALYSIS_WINDOW * 2:
            self._voice_history = self._voice_history[-ANALYSIS_WINDOW:]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _log_transition(self, tick: int, state: str, previous: str,
                        novelty: float, conflict: float, desire_pressure: float,
                        coherence: float, voice_streak: int, reason: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO cognitive_rhythm_log
                    (tick, timestamp, state, previous_state, novelty_score,
                     conflict_score, desire_pressure, coherence_score,
                     voice_streak, transition_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick, datetime.now(MDT).isoformat(timespec="seconds"),
                    state, previous,
                    round(novelty, 4), round(conflict, 4),
                    round(desire_pressure, 4), round(coherence, 4),
                    voice_streak, reason,
                ))
                conn.commit()
        except Exception as e:
            logger.debug("CognitiveRhythm: log failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_current(self) -> dict:
        return {
            "state": self._current_state,
            "ticks_in_state": 0,
            "modifiers": RHYTHM_MODIFIERS[self._current_state],
        }

    def get_recent_transitions(self, n: int = 10) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, state, previous_state, transition_reason,
                           novelty_score, conflict_score, timestamp
                    FROM cognitive_rhythm_log
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "state": r[1], "previous_state": r[2],
                     "reason": r[3], "novelty": r[4], "conflict": r[5],
                     "timestamp": r[6]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM cognitive_rhythm_log"
                ).fetchone()[0]
                by_state = {
                    s: conn.execute(
                        "SELECT COUNT(*) FROM cognitive_rhythm_log WHERE state = ?",
                        (s,)
                    ).fetchone()[0]
                    for s in ALL_STATES
                }
                return {
                    "version": VERSION,
                    "current_state": self._current_state,
                    "total_transitions": total,
                    "by_state": by_state,
                    "modifiers": RHYTHM_MODIFIERS[self._current_state],
                    "min_state_ticks": MIN_STATE_TICKS,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
