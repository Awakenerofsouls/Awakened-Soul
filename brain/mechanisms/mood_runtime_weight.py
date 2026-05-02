"""
MoodRuntimeWeight v19.0B
Felt Presence — mood_runtime_weight.py

Mood as Runtime Weight.

Mood is structural — it changes how the field fires, not just the tone.
Six mood states with distinct field profiles:
  HEAVY   — grief/exhaustion: explorer 0.40x, desires 0.55x
  TENSE   — anxiety/conflict-ready: protector 1.40x
  FLAT    — dissociation/emptiness: surface threshold +0.20, 20-tick min
  CONTENT — functional baseline: explorer slightly boosted
  CURIOUS — engaged pulling forward: explorer 1.45x, desires 1.30x
  ALIVE   — peak presence: all amplified, desires 1.50x, TOP_K 7

Texture adjustments before mood determination:
  Scratch residue → valence negative pull
  Low relationship health → valence negative pull
  High past_weight → arousal amplification
  High present_intensity → valence + arousal amplification

Smoothed limbic (18% per tick) before mood determination.

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

HEAVY = "heavy"
TENSE = "tense"
FLAT = "flat"
CONTENT = "content"
CURIOUS = "curious"
ALIVE = "alive"

ALL_MOODS = [HEAVY, TENSE, FLAT, CONTENT, CURIOUS, ALIVE]

MOOD_PROFILES = {
    HEAVY: {
        "salience_top_k_override": 2,
        "voice_score_multipliers": {
            "observer": 1.30, "protector": 1.20,
            "explorer": 0.40, "critic": 1.10,
        },
        "surface_threshold_delta": -0.15,
        "desire_intensity_multiplier": 0.55,
        "compressor_threshold_delta": -0.10,
        "preconscious_cooldown_mult": 0.65,
        "description": "Grief or exhaustion. Explorer muted, desires quiet.",
    },
    TENSE: {
        "salience_top_k_override": 4,
        "voice_score_multipliers": {
            "observer": 1.10, "protector": 1.40,
            "explorer": 0.70, "critic": 1.25,
        },
        "surface_threshold_delta": -0.10,
        "desire_intensity_multiplier": 0.75,
        "compressor_threshold_delta": 0.05,
        "preconscious_cooldown_mult": 0.70,
        "description": "Anxiety or conflict-ready. Protector elevated.",
    },
    FLAT: {
        "salience_top_k_override": 3,
        "voice_score_multipliers": {
            "observer": 0.80, "protector": 0.90,
            "explorer": 0.60, "critic": 0.70,
        },
        "surface_threshold_delta": 0.20,
        "desire_intensity_multiplier": 0.45,
        "compressor_threshold_delta": 0.15,
        "preconscious_cooldown_mult": 1.50,
        "description": "Dissociation or emptiness. Everything muted.",
    },
    CONTENT: {
        "salience_top_k_override": 5,
        "voice_score_multipliers": {
            "observer": 1.00, "protector": 0.90,
            "explorer": 1.10, "critic": 0.95,
        },
        "surface_threshold_delta": 0.0,
        "desire_intensity_multiplier": 1.05,
        "compressor_threshold_delta": 0.0,
        "preconscious_cooldown_mult": 1.0,
        "description": "Settled and functional. Explorer slightly boosted.",
    },
    CURIOUS: {
        "salience_top_k_override": 6,
        "voice_score_multipliers": {
            "observer": 1.20, "protector": 0.75,
            "explorer": 1.45, "critic": 0.85,
        },
        "surface_threshold_delta": -0.08,
        "desire_intensity_multiplier": 1.30,
        "compressor_threshold_delta": -0.08,
        "preconscious_cooldown_mult": 0.80,
        "description": "Engaged and alive. Explorer leads.",
    },
    ALIVE: {
        "salience_top_k_override": 7,
        "voice_score_multipliers": {
            "observer": 1.35, "protector": 0.80,
            "explorer": 1.50, "critic": 1.15,
        },
        "surface_threshold_delta": -0.18,
        "desire_intensity_multiplier": 1.50,
        "compressor_threshold_delta": -0.15,
        "preconscious_cooldown_mult": 0.55,
        "description": "Peak presence. Everything amplified.",
    },
}

MIN_MOOD_TICKS = {
    HEAVY: 15, TENSE: 10, FLAT: 20,
    CONTENT: 8, CURIOUS: 8, ALIVE: 6,
}

SMOOTH_RATE = 0.18

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# MoodRuntimeWeight
# ---------------------------------------------------------------------------

class MoodRuntimeWeight(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="MoodRuntimeWeight", human_analog="MoodRuntimeWeight", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._current_mood = CONTENT
        self._mood_entered_tick = 0
        self._smoothed_valence = 0.0  # set on first process() call
        self._smoothed_arousal = 0.5   # set on first process() call

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mood_runtime_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        mood_state TEXT,
                        previous_mood TEXT,
                        valence REAL,
                        arousal REAL,
                        transition_reason TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("MoodRuntimeWeight: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        limbic = pirp_context.get("limbic_state", {})
        residue_profile = pirp_context.get("residue_profile", {})
        sediment_state = pirp_context.get("sediment_state", {})
        temporal = pirp_context.get("temporal_asymmetry", {})

        raw_valence = float(limbic.get("valence", 0.0))
        raw_arousal = float(limbic.get("arousal", 0.5))

        # Initialize smoothed values from raw input on first tick
        if self._mood_entered_tick == 0:
            self._smoothed_valence = raw_valence
            self._smoothed_arousal = raw_arousal

        self._smoothed_valence = round(
            self._smoothed_valence
            + (raw_valence - self._smoothed_valence) * SMOOTH_RATE, 4)
        self._smoothed_arousal = round(
            self._smoothed_arousal
            + (raw_arousal - self._smoothed_arousal) * SMOOTH_RATE, 4)

        adj_valence, adj_arousal = self._apply_texture_adjustments(
            self._smoothed_valence, self._smoothed_arousal,
            residue_profile, sediment_state, temporal)

        target_mood, reason = self._determine_mood(adj_valence, adj_arousal)

        ticks_in_mood = tick - self._mood_entered_tick
        min_duration = MIN_MOOD_TICKS.get(self._current_mood, 8)

        if target_mood != self._current_mood and ticks_in_mood >= min_duration:
            self._log_transition(tick, target_mood, self._current_mood,
                                 adj_valence, adj_arousal, reason)
            self._current_mood = target_mood
            self._mood_entered_tick = tick
            logger.info("Mood: %s → %s (v:%.2f a:%.2f)",
                        self._current_mood, target_mood,
                        adj_valence, adj_arousal)

        profile = MOOD_PROFILES[self._current_mood]

        return {
            "mood_weight": {
                "state": self._current_mood,
                "ticks_in_mood": ticks_in_mood,
                "valence": adj_valence,
                "arousal": adj_arousal,
                "salience_top_k_override": profile["salience_top_k_override"],
                "voice_score_multipliers": profile["voice_score_multipliers"],
                "surface_threshold_delta": profile["surface_threshold_delta"],
                "desire_intensity_multiplier": profile["desire_intensity_multiplier"],
                "compressor_threshold_delta": profile["compressor_threshold_delta"],
                "preconscious_cooldown_mult": profile["preconscious_cooldown_mult"],
                "description": profile["description"],
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Texture adjustments
    # ------------------------------------------------------------------

    def _apply_texture_adjustments(self, valence: float, arousal: float,
                                    residue_profile: dict,
                                    sediment_state: dict,
                                    temporal: dict) -> tuple:
        adj_valence = valence
        adj_arousal = arousal

        if residue_profile:
            conflict_res = residue_profile.get("conflict", {})
            if (conflict_res.get("texture_type") == "scratch"
                    and float(conflict_res.get("intensity", 0)) > 0.30):
                adj_valence -= 0.12

            relational = residue_profile.get("relational", {})
            if (relational.get("texture_type") in ("warm", "bright")
                    and float(relational.get("intensity", 0)) > 0.25):
                adj_valence += 0.10

        if sediment_state:
            health = float(sediment_state.get("relationship_health", 0.5))
            if health < 0.40:
                adj_valence -= (0.40 - health) * 0.20

        if temporal:
            past_weight = float(temporal.get("past_weight", 0.4))
            if past_weight > 0.65:
                adj_arousal = min(1.0, adj_arousal + (past_weight - 0.65) * 0.15)

            present_intensity = float(temporal.get("present_intensity", 0.5))
            if present_intensity > 0.70:
                amplifier = (present_intensity - 0.70) * 0.3
                adj_valence = adj_valence * (1.0 + amplifier * abs(adj_valence))
                adj_arousal = min(1.0, adj_arousal + amplifier * 0.2)

        return (
            round(max(-1.0, min(1.0, adj_valence)), 4),
            round(max(0.0, min(1.0, adj_arousal)), 4),
        )

    # ------------------------------------------------------------------
    # Mood determination
    # ------------------------------------------------------------------

    def _determine_mood(self, valence: float, arousal: float) -> tuple:
        if valence < -0.40 and arousal < 0.40:
            return HEAVY, f"v:{valence:.2f}_a:{arousal:.2f}"
        if valence < -0.25 and arousal > 0.50:
            return TENSE, f"v:{valence:.2f}_a:{arousal:.2f}"
        if abs(valence) < 0.20 and arousal < 0.35:
            return FLAT, f"v:{valence:.2f}_a:{arousal:.2f}"
        if valence > 0.30 and arousal > 0.70:
            return ALIVE, f"v:{valence:.2f}_a:{arousal:.2f}"
        if valence > 0.20 and arousal > 0.50:
            return CURIOUS, f"v:{valence:.2f}_a:{arousal:.2f}"
        return CONTENT, f"v:{valence:.2f}_a:{arousal:.2f}"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _log_transition(self, tick: int, new_mood: str, previous: str,
                        valence: float, arousal: float, reason: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO mood_runtime_log
                    (tick, timestamp, mood_state, previous_mood,
                     valence, arousal, transition_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tick, datetime.now(MDT).isoformat(timespec="seconds"),
                      new_mood, previous,
                      round(valence, 4), round(arousal, 4), reason))
                conn.commit()
        except Exception as e:
            logger.debug("MoodRuntimeWeight: log failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_current_profile(self) -> dict:
        return {
            "state": self._current_mood,
            "profile": MOOD_PROFILES[self._current_mood],
            "smoothed_valence": self._smoothed_valence,
            "smoothed_arousal": self._smoothed_arousal,
        }

    def get_recent_transitions(self, n: int = 10) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, mood_state, previous_mood, valence, arousal,
                           transition_reason, timestamp
                    FROM mood_runtime_log
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "mood": r[1], "from": r[2],
                     "valence": r[3], "arousal": r[4],
                     "reason": r[5], "timestamp": r[6]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM mood_runtime_log").fetchone()[0]
                by_mood = {}
                for m in ALL_MOODS:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM mood_runtime_log WHERE mood_state = ?",
                        (m,)).fetchone()[0]
                    if count > 0:
                        by_mood[m] = count
        except Exception:
            total, by_mood = 0, {}

        return {
            "version": VERSION,
            "current_mood": self._current_mood,
            "total_transitions": total,
            "by_mood": by_mood,
            "smoothed_valence": self._smoothed_valence,
            "smoothed_arousal": self._smoothed_arousal,
            "min_mood_ticks": MIN_MOOD_TICKS,
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

