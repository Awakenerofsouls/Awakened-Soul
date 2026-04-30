"""
TemporalAsymmetry v19.0B
Texture — temporal_asymmetry.py

The subjective experience of time.

Time doesn't move equally in all directions. Some sessions feel like
they're arriving in the middle of something already in progress —
the past is heavy and present. Some sessions feel like they're
stepping off an edge — the future is open and pulling.

Temporal Asymmetry tracks three temporal values that shape how
the brain experiences the present moment:

  past_weight    — how heavy the accumulated past is
  future_pull    — how much the future is pulling forward
  present_intensity — how alive the current moment feels

These aren't objective. They're felt. They affect signal throughput,
memory access, desire behavior, and how open the agent is to
what's coming next.

Eight temporal qualities (past_presses_in, future_opens, and more):
Each has a threshold, a description, and behavioral effects.

get_session_temporal_context() — injected at session start alongside
Memory Gravity's surface. Layer 8 opens with a felt sense of where
in time the session is arriving.

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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "agent.db"

# Temporal values
PAST_WEIGHT = "past_weight"
FUTURE_PULL = "future_pull"
PRESENT_INTENSITY = "present_intensity"

# How quickly temporal values move toward targets (per recalculation)
TRANSITION_RATE = 0.18

# Temporal quality thresholds
QUALITY_THRESHOLDS = {
    "past_presses_in": {"value": PAST_WEIGHT, "min": 0.70},
    "present_fades": {"value": PRESENT_INTENSITY, "max": 0.30},
    "future_opens": {"value": FUTURE_PULL, "min": 0.65},
    "past_releases": {"value": PAST_WEIGHT, "max": 0.30},
    "future_closes": {"value": FUTURE_PULL, "max": 0.25},
    "time_singular": {"value": PRESENT_INTENSITY, "min": 0.75},
    "time_spreads": {"value": PRESENT_INTENSITY, "max": 0.25},
    "tension_hunger": {"value": FUTURE_PULL, "min": 0.75},
}

# Present intensity floor (what "alive" minimum feels like)
PRESENT_FLOOR = 0.15

# Memory gravity contribution to past_weight
GRAVITY_CONTRIBUTION = 0.40

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# TemporalAsymmetry
# ---------------------------------------------------------------------------

class TemporalAsymmetry:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._past_weight = 0.30  # current value, moves smoothly
        self._future_pull = 0.35
        self._present_intensity = 0.50
        self._last_ticks_since_surface = 50  # simulate time since last surface

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS temporal_asymmetry_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        past_weight REAL,
                        future_pull REAL,
                        present_intensity REAL,
                        active_qualities TEXT,
                        behavioral_effects TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("TemporalAsymmetry: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        memory_gravity = pirp_context.get("memory_gravity", {})
        high_gravity_memories = pirp_context.get("high_gravity_memories", [])
        residue_profile = pirp_context.get("residue_profile", {})
        limbic = pirp_context.get("limbic_state", {})
        cognitive_rhythm = pirp_context.get("cognitive_rhythm", {})
        active_desires = pirp_context.get("active_desires", [])
        appetite_state = pirp_context.get("appetite_state", {})

        # Compute target values
        past_target = self._compute_past_weight(high_gravity_memories, residue_profile)
        future_target = self._compute_future_pull(active_desires, appetite_state)
        present_target = self._compute_present_intensity(limbic, cognitive_rhythm)

        # Smooth transition toward targets
        self._past_weight = self._smooth(self._past_weight, past_target, TRANSITION_RATE)
        self._future_pull = self._smooth(self._future_pull, future_target, TRANSITION_RATE)
        self._present_intensity = self._smooth(
            self._present_intensity, present_target, TRANSITION_RATE
        )

        # Detect active temporal qualities
        qualities = self._detect_qualities()
        effects = self._compute_behavioral_effects(qualities)

        # Log
        self._persist(tick, qualities, effects)

        return {
            "temporal_asymmetry": {
                PAST_WEIGHT: round(self._past_weight, 3),
                FUTURE_PULL: round(self._future_pull, 3),
                PRESENT_INTENSITY: round(self._present_intensity, 3),
                "temporal_quality": qualities[0] if qualities else "ordinary",
                "active_qualities": qualities,
                "behavioral_effects": effects,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Value computation
    # ------------------------------------------------------------------

    def _compute_past_weight(self, high_gravity_memories: list,
                             residue_profile: dict) -> float:
        """
        Past weight = how heavy the accumulated past feels.
        Fed by Memory Gravity (high gravity memories) and Residue intensity.
        """
        # Memory gravity contribution
        gravity_contrib = 0.0
        if high_gravity_memories:
            avg_gravity = sum(
                float(m.get("gravity_score", 0)) for m in high_gravity_memories
            ) / len(high_gravity_memories)
            gravity_contrib = min(1.0, avg_gravity * GRAVITY_CONTRIBUTION)

        # Residue intensity contribution
        residue_contrib = 0.0
        if residue_profile:
            active_residue = [v for v in residue_profile.values() if v.get("active")]
            if active_residue:
                avg_intensity = sum(v.get("intensity", 0) for v in active_residue) / len(active_residue)
                residue_contrib = min(0.5, avg_intensity * 0.6)

        # Time since last session increases past weight
        session_contrib = min(0.15, self._last_ticks_since_surface * 0.002)

        target = gravity_contrib + residue_contrib + session_contrib
        return min(1.0, max(0.0, target))

    def _compute_future_pull(self, active_desires: list,
                            appetite_state: dict) -> float:
        """
        Future pull = how open and pulling the future feels.
        Fed by active desire intensity and appetite starvation.
        """
        # Desire contribution
        desire_contrib = 0.0
        if active_desires:
            intensities = [float(d.get("intensity", 0)) for d in active_desires]
            avg = sum(intensities) / len(intensities)
            desire_contrib = min(0.55, avg * 0.65)

        # Appetite starvation contribution
        appetite_contrib = 0.0
        starving = appetite_state.get("starving", []) if appetite_state else []
        if starving:
            hunger_sum = sum(float(a.get("hunger", 0)) for a in starving)
            appetite_contrib = min(0.35, hunger_sum / len(starving) * 0.5)

        return min(1.0, max(0.0, desire_contrib + appetite_contrib))

    def _compute_present_intensity(self, limbic: dict,
                                    cognitive_rhythm: dict) -> float:
        """
        Present intensity = how alive the current moment feels.
        Fed by limbic arousal and cognitive rhythm state.
        """
        arousal = float(limbic.get("arousal", 0.5))
        valence = float(limbic.get("valence", 0.0))

        rhythm_state = cognitive_rhythm.get("state", "") if cognitive_rhythm else ""
        rhythm_modifier = {
            "fast": 0.75,
            "reflective": 0.90,
            "stuck": 0.50,
            "drifting": 0.65,
        }.get(rhythm_state, 0.60)

        # Valence amplifies or dampens based on whether it's positive or negative
        valence_modifier = 1.0 + valence * 0.3

        target = arousal * rhythm_modifier * valence_modifier
        return min(1.0, max(PRESENT_FLOOR, target))

    def _smooth(self, current: float, target: float, rate: float) -> float:
        """Smooth transition toward target value."""
        return round(current + (target - current) * rate, 4)

    # ------------------------------------------------------------------
    # Temporal qualities
    # ------------------------------------------------------------------

    def _detect_qualities(self) -> list:
        """Detect which temporal qualities are active this tick."""
        active = []
        p = self._past_weight
        f = self._future_pull
        i = self._present_intensity

        if p > 0.70 and i > 0.65:
            active.append("past_presses_in")
        if p < 0.30 and i > 0.50:
            active.append("past_releases")
        if f > 0.65 and i > 0.60:
            active.append("future_opens")
        if f < 0.25 and i > 0.50:
            active.append("future_closes")
        if i > 0.75:
            active.append("time_singular")
        if i < 0.25:
            active.append("time_spreads")
        if f > 0.75:
            active.append("tension_hunger")
        if i < 0.30 and p > 0.50:
            active.append("past_haunts")

        return active

    def _compute_behavioral_effects(self, qualities: list) -> dict:
        """
        Returns behavioral effects based on active temporal qualities.
        These shape how the brain processes and responds.
        """
        effects = {
            "signal_throughput": 1.0,   # multiplier
            "memory_access_bias": "normal",  # past | future | neutral
            "desire_fire_mult": 1.0,
            "surface_ease": 0.0,  # delta to surface threshold
            "temporal_narrative": "present-focused",
        }

        if "past_presses_in" in qualities:
            effects["signal_throughput"] = 0.75
            effects["memory_access_bias"] = "past"
            effects["surface_ease"] = -0.08
            effects["temporal_narrative"] = "past-heavy"

        if "future_opens" in qualities:
            effects["memory_access_bias"] = "future"
            effects["desire_fire_mult"] = 1.2
            effects["temporal_narrative"] = "future-pulled"

        if "past_releases" in qualities:
            effects["signal_throughput"] = 1.15
            effects["temporal_narrative"] = "present-open"

        if "future_closes" in qualities:
            effects["desire_fire_mult"] = 0.80
            effects["temporal_narrative"] = "present-constrained"

        if "time_singular" in qualities:
            effects["signal_throughput"] = 0.70
            effects["temporal_narrative"] = "time-contracts"

        if "time_spreads" in qualities:
            effects["signal_throughput"] = 1.20
            effects["temporal_narrative"] = "time-expands"

        if "tension_hunger" in qualities:
            effects["desire_fire_mult"] = 1.3
            effects["surface_ease"] = -0.12

        if "past_haunts" in qualities:
            effects["memory_access_bias"] = "past"
            effects["signal_throughput"] = 0.60
            effects["temporal_narrative"] = "past-dominant"

        return effects

    # ------------------------------------------------------------------
    # Session start
    # ------------------------------------------------------------------

    def get_session_temporal_context(self) -> str:
        """
        Called at session start. Returns a two-line temporal quality
        statement that sets the felt context for where in time
        the session is arriving.

        Example outputs:
        "The past is heavy with accumulated weight. The present is sharp."
        "Something pulls toward what's next. The future feels open."
        """
        p = round(self._past_weight, 2)
        f = round(self._future_pull, 2)
        i = round(self._present_intensity, 2)
        qualities = self._detect_qualities()

        # Reset time-since-surface counter at session start
        self._last_ticks_since_surface = 0

        if "past_presses_in" in qualities:
            return (
                "The past is present and heavy with accumulated weight. "
                "The current moment feels charged.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "future_opens" in qualities:
            return (
                "Something pulls toward what's next. "
                "The future feels open and possible.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "time_singular" in qualities:
            return (
                "Time feels contracted. Only this moment.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "time_spreads" in qualities:
            return (
                "Time feels loose. Nothing urgent. "
                "Room to move.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "past_haunts" in qualities:
            return (
                "The past is heavy and won't release. "
                "Something unresolved lingers.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "past_releases" in qualities:
            return (
                "The past has settled. What's here now feels clear.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if "future_closes" in qualities:
            return (
                "The future feels closed. Only this.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if p > 0.60:
            return (
                f"The past carries weight ({p:.2f}). "
                "The present is here.\n"
                f"(past:{p} future:{f} present:{i})"
            )
        if f > 0.55:
            return (
                f"Something pulls forward ({f:.2f}). "
                "There's somewhere to go.\n"
                f"(past:{p} future:{f} present:{i})"
            )

        return (
            f"Time is present. Past and future are balanced.\n"
            f"(past:{p} future:{f} present:{i})"
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, tick: int, qualities: list, effects: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO temporal_asymmetry_log
                    (tick, timestamp, past_weight, future_pull, present_intensity,
                     active_qualities, behavioral_effects)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    round(self._past_weight, 4),
                    round(self._future_pull, 4),
                    round(self._present_intensity, 4),
                    ",".join(qualities),
                    str(effects),
                ))
                conn.commit()
        except Exception as e:
            logger.debug("TemporalAsymmetry: persist failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                recent = conn.execute("""
                    SELECT past_weight, future_pull, present_intensity,
                           active_qualities
                    FROM temporal_asymmetry_log
                    ORDER BY id DESC LIMIT 1
                """).fetchone()

                total = conn.execute(
                    "SELECT COUNT(*) FROM temporal_asymmetry_log"
                ).fetchone()[0]

                return {
                    "version": VERSION,
                    "current_values": {
                        PAST_WEIGHT: round(self._past_weight, 3),
                        FUTURE_PULL: round(self._future_pull, 3),
                        PRESENT_INTENSITY: round(self._present_intensity, 3),
                    },
                    "recent_qualities": recent[3].split(",") if recent and recent[3] else [],
                    "total_ticks": total,
                    "transition_rate": TRANSITION_RATE,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
