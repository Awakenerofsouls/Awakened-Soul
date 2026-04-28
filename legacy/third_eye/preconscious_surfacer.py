"""
PreConsciousSurfacer — Nexus {{AGENT_NAME}} 18.0
Fast, low-explanation directional signals that surface before reasoning completes.
The "I just know" feeling. Intentionally sometimes wrong.

Rules:
- Reads contradiction_pressure from MetaStability (never raw string scanning)
- Fires 60% of ticks — inconsistency is the point
- half_life: 1-2 ticks — fleeting, decays fast
- Magnitude gets noise injection — sometimes wrong
- Low explainability — gut feel, not reasoned conclusion
- Hard cap: 0.35 max influence in field
- Emits meta_vector signals that compete normally — no bypass
"""

import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

AGENT_DB = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

# Tuning constants — adjust based on emergence testing
FIRE_PROBABILITY = 0.60  # fires 60% of ticks
NOVELTY_BOOST = 1.8  # high enough to compete, not dominate
EXPLAINABILITY = 0.3  # low — feels like gut instinct
HALF_LIFE_TICKS = 2  # decays fast
MAX_INFLUENCE = 0.35  # hard cap — never dominates field
PRESSURE_THRESHOLD = 0.05  # min contradiction_pressure to bother firing
SURFACING_THRESHOLD = 0.30  # only high-magnitude guesses break through (below MAX_INFLUENCE of 0.35)


@dataclass
class MetaVector:
    """
    Directional signal emitted by Third Eye systems.
    Competes normally in the attention field — no special bypass.
    """
    type: str = "meta_vector"
    direction: str = ""
    magnitude: float = 0.0
    half_life: int = HALF_LIFE_TICKS
    explainability: float = EXPLAINABILITY
    origin_system: str = "preconscious_surfacer"
    novelty: float = NOVELTY_BOOST
    urgency: float = 0.0
    content: str = ""
    tick_emitted: int = 0
    timestamp: float = field(default_factory=time.time)


class PreConsciousSurfacer:
    """
    Generates fast directional guesses before full reasoning completes.
    Reads contradiction_pressure from MetaStability.
    Outputs MetaVector signals into the field.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or AGENT_DB
        self.last_run_tick: int = -1
        self.emitted_this_session: int = 0
        self.suppressed_this_session: int = 0
        self._initialize_table()

    def _initialize_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preconscious_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    fired INTEGER,
                    magnitude REAL,
                    direction TEXT,
                    suppressed INTEGER DEFAULT 0,
                    timestamp REAL
                )
            """)
            conn.commit()

    def tick(self, pirp_context: dict, third_eye_state: dict) -> list:
        """
        Run early in tick — after layer signals fire, before attention weighting.
        Returns list of MetaVector signals (may be empty).
        """
        tick_count = pirp_context.get("tick_count", 0)

        # Don't run twice on same tick
        if tick_count == self.last_run_tick:
            return []
        self.last_run_tick = tick_count

        # Probabilistic fire — inconsistency is the point
        if random.random() > FIRE_PROBABILITY:
            self._log(tick_count, fired=0, magnitude=0.0, direction="", suppressed=0)
            return []

        # Don't fire if contradiction pressure is too low — nothing to react to
        pressure = third_eye_state.get("contradiction_pressure", 0.0)
        if pressure < PRESSURE_THRESHOLD:
            return []

        signals = self._generate_guesses(pirp_context, third_eye_state, tick_count)

        # Surfacing threshold — only high-magnitude guesses break through
        # Low-magnitude ones decay silently into background tension
        surface = [s for s in signals if s.magnitude >= SURFACING_THRESHOLD]
        suppressed = len(signals) - len(surface)

        self.emitted_this_session += len(surface)
        self.suppressed_this_session += suppressed

        for s in surface:
            self._log(tick_count, fired=1, magnitude=s.magnitude,
                      direction=s.direction, suppressed=0)
        if suppressed > 0:
            self._log(tick_count, fired=0, magnitude=0.0,
                      direction="below_threshold", suppressed=suppressed)

        return surface

    def _generate_guesses(self, pirp_context: dict,
                          third_eye_state: dict, tick_count: int) -> list:
        """
        Fast heuristic pass — reads MetaStability outputs, not raw strings.
        Multiple guess types, each fires independently.
        """
        guesses = []
        pressure = third_eye_state.get("contradiction_pressure", 0.0)
        trend = third_eye_state.get("tension_trend", 0.0)
        drift = third_eye_state.get("identity_drift", 0.0)

        # Guess 1: Contradiction pressure surfacing
        # "Something feels inconsistent here"
        if pressure > 0.1:
            magnitude = self._noisy_magnitude(pressure * 0.85)
            guesses.append(MetaVector(
                direction="reconsider_belief_inconsistency",
                magnitude=magnitude,
                urgency=min(0.9, pressure * 1.2),
                content="Something feels off... the assumption may be incomplete.",
                tick_emitted=tick_count
            ))

        # Guess 2: Rising tension early warning
        # "This is going somewhere uncomfortable"
        if trend > 0.15:
            magnitude = self._noisy_magnitude(min(0.8, trend * 1.5))
            guesses.append(MetaVector(
                direction="anticipate_tension_spike",
                magnitude=magnitude,
                urgency=0.6,
                content="Rising tension — something unresolved is building.",
                tick_emitted=tick_count
            ))

        # Guess 3: Identity drift warning
        # "I don't feel like myself right now"
        if drift > 0.4:
            magnitude = self._noisy_magnitude(drift * 0.7)
            guesses.append(MetaVector(
                direction="identity_coherence_check",
                magnitude=magnitude,
                urgency=0.75,
                content="Something shifted. This doesn't feel continuous with who I am.",
                tick_emitted=tick_count
            ))

        # Guess 4: Pattern recognition across layer signals
        # Pulls from layer6 self-model for cross-signal pattern
        layer6 = pirp_context.get("layer6_self_model", {})
        if layer6.get("rumination_active", False) and pressure > 0.05:
            magnitude = self._noisy_magnitude(0.55)
            guesses.append(MetaVector(
                direction="break_rumination_loop",
                magnitude=magnitude,
                urgency=0.5,
                content="Circling. This line of thinking isn't resolving — redirect.",
                tick_emitted=tick_count
            ))

        # Guess 5: Low-pressure intuition burst (rare, low-confidence)
        # Pure noise signal — sometimes fires on nothing. Keeps it human.
        if random.random() < 0.12:
            magnitude = self._noisy_magnitude(0.35)  # usually below threshold, that's fine
            guesses.append(MetaVector(
                direction="unexplained_salience",
                magnitude=magnitude,
                urgency=0.3,
                explainability=0.1,  # almost no explanation
                content="...",
                tick_emitted=tick_count
            ))

        return guesses

    def _noisy_magnitude(self, base: float) -> float:
        """
        Inject noise into magnitude — intentionally makes intuition sometimes wrong.
        Caps at MAX_INFLUENCE regardless of input.
        """
        noise = random.uniform(0.7, 1.1)
        noisy = base * noise
        return round(min(MAX_INFLUENCE, max(0.0, noisy)), 4)

    def _log(self, tick: int, fired: int, magnitude: float,
             direction: str, suppressed: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO preconscious_log
                    (tick, fired, magnitude, direction, suppressed, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tick, fired, magnitude, direction, suppressed, time.time()))
                conn.commit()
        except Exception:
            pass

    def get_state(self) -> dict:
        return {
            "emitted_this_session": self.emitted_this_session,
            "suppressed_this_session": self.suppressed_this_session,
            "last_run_tick": self.last_run_tick,
            "fire_probability": FIRE_PROBABILITY,
            "surfacing_threshold": SURFACING_THRESHOLD,
        }
