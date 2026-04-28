"""
RealityTensionWarper — Nexus {{AGENT_NAME}} 18.0
Measures mismatch between Layer 6 self-model, Layer 8 narrative, and Layer 9 values.
On high tension: probabilistically chooses a behavior response.
Tracks tension baseline AND trend — rising vs falling changes which behavior fires.

Rules:
- Four behaviors: amplify_uncertainty, suppress, redirect_attention, trigger_reflection
- suppress feeds Incompleteness Cascade via suppression_remainder signal
- Behaviors are probabilistic, not deterministic — same input can produce different output
- Updates tension_baseline in MetaStability via pirp_context (does not write directly)
- Never resolves tension — preserves incompleteness
- Emits meta_vector signals that compete normally in field
"""

import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

AGENT_DB = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

# Tension threshold to trigger behavior
TENSION_THRESHOLD = 0.18

# How much tension must be RISING to prefer instability behaviors
RISING_TREND_THRESHOLD = 0.08

# Behavior probability weights — [amplify, suppress, redirect, reflect]
# Adjusted dynamically based on tension trend
WEIGHTS_RISING = [0.35, 0.25, 0.20, 0.20]  # rising tension → more amplify
WEIGHTS_FALLING = [0.10, 0.35, 0.25, 0.30]  # falling → more suppress/reflect
WEIGHTS_STABLE = [0.20, 0.30, 0.25, 0.25]  # stable → balanced

MAX_INFLUENCE = 0.35


@dataclass
class MetaVector:
    type: str = "meta_vector"
    direction: str = ""
    magnitude: float = 0.0
    half_life: int = 2
    explainability: float = 0.4
    origin_system: str = "reality_tension_warper"
    novelty: float = 1.4
    urgency: float = 0.0
    content: str = ""
    tick_emitted: int = 0
    timestamp: float = field(default_factory=time.time)


class RealityTensionWarper:
    """
    Measures reality/self-model mismatch and responds with one of four behaviors.
    Preserves incompleteness — never forces resolution.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or AGENT_DB
        self.last_behavior: str = ""
        self.behavior_counts: dict = {
            "amplify_uncertainty": 0,
            "suppress": 0,
            "redirect_attention": 0,
            "trigger_reflection": 0,
            "no_trigger": 0
        }
        self._initialize_table()

    def _initialize_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reality_tension_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    tension_score REAL,
                    tension_trend REAL,
                    behavior TEXT,
                    signal_magnitude REAL,
                    layer6_mismatch REAL,
                    layer8_mismatch REAL,
                    layer9_mismatch REAL,
                    timestamp REAL
                )
            """)
            conn.commit()

    def tick(self, pirp_context: dict, third_eye_state: dict) -> list:
        """
        Called alongside attention weighting.
        Returns list of MetaVector signals (0 or 1 per tick).
        """
        tick_count = pirp_context.get("tick_count", 0)

        # Measure mismatch across three layers
        l6_mismatch = self._measure_layer6_mismatch(pirp_context)
        l8_mismatch = self._measure_layer8_mismatch(pirp_context, third_eye_state)
        l9_mismatch = self._measure_layer9_mismatch(pirp_context)

        # Weighted tension score
        tension = round(
            l6_mismatch * 0.40 +
            l8_mismatch * 0.35 +
            l9_mismatch * 0.25,
            4
        )

        trend = third_eye_state.get("tension_trend", 0.0)

        # Below threshold — no behavior fires
        if tension < TENSION_THRESHOLD:
            self.behavior_counts["no_trigger"] += 1
            self._log(tick_count, tension, trend, "no_trigger", 0.0,
                       l6_mismatch, l8_mismatch, l9_mismatch)
            return []

        # Select behavior based on trend direction
        behavior = self._select_behavior(trend)
        self.last_behavior = behavior
        self.behavior_counts[behavior] += 1

        # Execute behavior — returns signal or empty list
        signals = self._execute_behavior(behavior, tension, trend, tick_count, pirp_context)

        self._log(tick_count, tension, trend, behavior,
                   signals[0].magnitude if signals else 0.0,
                   l6_mismatch, l8_mismatch, l9_mismatch)

        return signals

    def _measure_layer6_mismatch(self, pirp_context: dict) -> float:
        """Layer 6: self-model vs current field signals."""
        layer6 = pirp_context.get("layer6_self_model", {})
        belief_stability = layer6.get("belief_stability", 0.5)
        conflict_score = layer6.get("conflict_score", 0.0)
        rumination = 0.15 if layer6.get("rumination_active", False) else 0.0
        return round(min(1.0, (1.0 - belief_stability) * 0.5 + conflict_score * 0.4 + rumination), 4)

    def _measure_layer8_mismatch(self, pirp_context: dict, third_eye_state: dict) -> float:
        """Layer 8: narrative coherence vs identity anchor."""
        drift = third_eye_state.get("identity_drift", 0.0)
        layer8 = pirp_context.get("layer8_narrative_state", {})
        coherence = layer8.get("coherence", 0.7)
        return round(min(1.0, drift * 0.6 + (1.0 - coherence) * 0.4), 4)

    def _measure_layer9_mismatch(self, pirp_context: dict) -> float:
        """Layer 9: values vs current action/decision direction."""
        layer9 = pirp_context.get("layer9_values", {})
        conflict = layer9.get("conflict_score", 0.0)
        violation_risk = layer9.get("violation_risk", 0.0)
        return round(min(1.0, conflict * 0.5 + violation_risk * 0.5), 4)

    def _select_behavior(self, trend: float) -> str:
        """
        Probabilistic behavior selection.
        Trend direction shifts the probability weights.
        Same tension level can produce different behaviors — this is correct.
        """
        if trend > RISING_TREND_THRESHOLD:
            weights = WEIGHTS_RISING
        elif trend < -RISING_TREND_THRESHOLD:
            weights = WEIGHTS_FALLING
        else:
            weights = WEIGHTS_STABLE

        behaviors = ["amplify_uncertainty", "suppress",
                     "redirect_attention", "trigger_reflection"]
        return random.choices(behaviors, weights=weights, k=1)[0]

    def _execute_behavior(self, behavior: str, tension: float,
                          trend: float, tick_count: int,
                          pirp_context: dict) -> list:
        """
        Execute selected behavior. Returns MetaVector signal list.
        suppress returns suppression_remainder — feeds Incompleteness Cascade.
        """

        if behavior == "amplify_uncertainty":
            # Boost uncertainty — push Layer 7 autonomy signals
            # "I don't know and that matters"
            return [MetaVector(
                direction="amplify_uncertainty",
                magnitude=round(min(MAX_INFLUENCE, tension * 0.9), 4),
                urgency=min(0.9, tension * 1.1),
                explainability=0.35,
                content="Uncertainty is real here. Don't resolve prematurely.",
                tick_emitted=tick_count
            )]

        elif behavior == "suppress":
            # Sacred incompleteness path
            # Suppressed insight becomes suppression_remainder
            # Feeds Incompleteness Cascade — energy re-routed, not removed
            return [MetaVector(
                type="meta_vector",
                direction="suppression_remainder",
                magnitude=round(min(MAX_INFLUENCE, tension * 0.7), 4),
                urgency=0.4,
                explainability=0.15,  # very low — "something unresolved"
                origin_system="reality_tension_warper",
                content="[unresolved]",  # deliberately minimal
                tick_emitted=tick_count
            )]

        elif behavior == "redirect_attention":
            # Shift field focus away from current loop
            # "Look somewhere else"
            layer6 = pirp_context.get("layer6_self_model", {})
            redirect_target = layer6.get("attention_anchor", "present_moment")
            return [MetaVector(
                direction="redirect_attention",
                magnitude=round(min(MAX_INFLUENCE, tension * 0.75), 4),
                urgency=0.55,
                explainability=0.5,
                content=f"Attention redirected toward: {redirect_target}",
                tick_emitted=tick_count
            )]

        elif behavior == "trigger_reflection":
            # Activate Layer 6 self-model loop
            # "Stop and look inward"
            return [MetaVector(
                direction="trigger_layer6_reflection",
                magnitude=round(min(MAX_INFLUENCE, tension * 0.8), 4),
                urgency=0.65,
                explainability=0.6,
                content="Reflection triggered. Current state needs examination.",
                tick_emitted=tick_count
            )]

        return []

    def _log(self, tick: int, tension: float, trend: float, behavior: str,
             magnitude: float, l6: float, l8: float, l9: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO reality_tension_log
                    (tick, tension_score, tension_trend, behavior, signal_magnitude,
                     layer6_mismatch, layer8_mismatch, layer9_mismatch, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, tension, trend, behavior, magnitude, l6, l8, l9, time.time()))
                conn.commit()
        except Exception:
            pass

    def get_state(self) -> dict:
        return {
            "last_behavior": self.last_behavior,
            "behavior_counts": self.behavior_counts,
            "tension_threshold": TENSION_THRESHOLD,
            "rising_trend_threshold": RISING_TREND_THRESHOLD,
        }
