"""
brain/third_eye/reality_tension_warper.py — RealityTensionWarper
Phase 6 ThirdEye Reality-Contour Modulator

Wire 24: brain_affective_reset (MCC-sgACC affective reset signal, Integration022)
differentially modulates directive weights. High reset → amplify suppress/redirect
(reset directives); Low reset → amplify amplify_uncertainty/trigger_reflection (quiet
observational directives).

Citations:
  1. PMID 26993424 — Vogt BA 2016. Midcingulate cortex: Structure, connections,
     homologies, functions and diseases. J Chem Neuroanat 74:28-46.
     MCC as evaluative hub, structural grounds for affective-state reconfiguration.
  2. PMID 21167765 — Etkin et al 2011. Emotional processing in anterior cingulate
     and medial prefrontal cortex. Trends Cogn Sci 15(2):85-93.
     sgACC engaged when appraised threat exceeds regulatory capacity — threshold dynamic.
  3. PMID 23889930 — Shenhav et al 2013. Expected value of control theory.
     Neuron 79(2):217-240. EVC — dACC/MCC as integrator for control-vs-reset decision.
     Wire 24 implements the reset pathway when control allocation is insufficient.
"""

import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

NOVA_DB = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

__wire_meta__ = {
    "wire": 24,
    "signal": "brain_affective_reset",
    "mechanism": "RealityTensionWarper",
    "reads": ["brain_affective_reset"],
    "writes": ["brain_affective_reset_read", "brain_reset_gain", "brain_quiet_gain"],
    "citations": ["PMID 26993424", "PMID 21167765", "PMID 23889930"]
}

# Tension threshold to trigger behavior
TENSION_THRESHOLD = 0.18

# How much tension must be RISING to prefer instability behaviors
RISING_TREND_THRESHOLD = 0.08

# Behavior probability weights — [amplify, suppress, redirect, reflect]
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


def _compute_gains(ar: float):
    """
    Wire 24: Map affective_reset ∈ [0,1] to differential gains.
    reset_gain: amplifies suppress/redirect when MCC-sgACC is firing
    quiet_gain: amplifies amplify_uncertainty/trigger_reflection when anatomy is quiet

    High reset (1.0) → reset_gain=1.40, quiet_gain=0.60
    Neutral (0.5)   → reset_gain=1.00, quiet_gain=1.00
    Low reset (0.0) → reset_gain=0.60, quiet_gain=1.40
    """
    reset_gain = 0.6 + (ar * 0.8)
    quiet_gain = 1.4 - (ar * 0.8)
    return reset_gain, quiet_gain


class RealityTensionWarper:
    """
    Measures reality/self-model mismatch and responds with one of four behaviors.
    Preserves incompleteness — never forces resolution.

    Wire 24: brain_affective_reset modulates MetaVector directive weights differentially.
    Reset-active directives (suppress, redirect) amplify when MCC-sgACC fires.
    Quiet observational directives (amplify_uncertainty, trigger_reflection) amplify
    when anatomy is calm.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or NOVA_DB
        self.last_behavior: str = ""
        self.behavior_counts: dict = {
            "amplify_uncertainty": 0,
            "suppress": 0,
            "redirect_attention": 0,
            "trigger_reflection": 0,
            "no_trigger": 0
        }
        # Wire 24: diagnostic state for brain_* fields
        self._last_affective_reset: float = 0.5
        self._last_reset_gain: float = 1.0
        self._last_quiet_gain: float = 1.0
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

    def tick(self, pirp_context: dict, third_eye_state: dict = None,
             brain_layer: dict = None) -> list:
        """
        Called alongside attention weighting.
        Returns list of MetaVector signals (0 or 1 per tick).

        Wire 24: reads brain_affective_reset to differentially modulate directive weights.
        High reset → suppress/redirect amplified; Low reset → amplify_uncertainty/trigger_reflection amplified.
        """
        # ── Wire 24: read brain_affective_reset from TSB anatomy layer ───────────
        affective_reset = 0.5  # neutral default on miss
        if brain_layer is not None:
            raw = brain_layer.get("brain_affective_reset", 0.5)
            affective_reset = float(raw)
            affective_reset = max(0.0, min(1.0, affective_reset))  # clamp

        self._last_affective_reset = affective_reset
        reset_gain, quiet_gain = _compute_gains(affective_reset)
        self._last_reset_gain = reset_gain
        self._last_quiet_gain = quiet_gain

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

        trend = (third_eye_state or {}).get("tension_trend", 0.0)

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
        signals = self._execute_behavior(
            behavior, tension, trend, tick_count, pirp_context,
            reset_gain, quiet_gain
        )

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
        drift = (third_eye_state or {}).get("identity_drift", 0.0)
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
                          pirp_context: dict,
                          reset_gain: float = 1.0,
                          quiet_gain: float = 1.0) -> list:
        """
        Execute selected behavior. Returns MetaVector signal list.
        Wire 24: applies differential gain based on brain_affective_reset.
        """
        # Map behavior → gain
        if behavior in ("suppress", "redirect_attention"):
            gain = reset_gain
        elif behavior in ("amplify_uncertainty", "trigger_reflection"):
            gain = quiet_gain
        else:
            gain = 1.0  # unmapped directives get neutral gain

        if behavior == "amplify_uncertainty":
            base_mag = round(min(MAX_INFLUENCE, tension * 0.9), 4)
            return [MetaVector(
                direction="amplify_uncertainty",
                magnitude=round(min(MAX_INFLUENCE, base_mag * gain), 4),
                urgency=min(0.9, tension * 1.1),
                explainability=0.35,
                content="Uncertainty is real here. Don't resolve prematurely.",
                tick_emitted=tick_count
            )]

        elif behavior == "suppress":
            base_mag = round(min(MAX_INFLUENCE, tension * 0.7), 4)
            return [MetaVector(
                type="meta_vector",
                direction="suppression_remainder",
                magnitude=round(min(MAX_INFLUENCE, base_mag * gain), 4),
                urgency=0.4,
                explainability=0.15,
                origin_system="reality_tension_warper",
                content="[unresolved]",
                tick_emitted=tick_count
            )]

        elif behavior == "redirect_attention":
            base_mag = round(min(MAX_INFLUENCE, tension * 0.75), 4)
            layer6 = pirp_context.get("layer6_self_model", {})
            redirect_target = layer6.get("attention_anchor", "present_moment")
            return [MetaVector(
                direction="redirect_attention",
                magnitude=round(min(MAX_INFLUENCE, base_mag * gain), 4),
                urgency=0.55,
                explainability=0.5,
                content=f"Attention redirected toward: {redirect_target}",
                tick_emitted=tick_count
            )]

        elif behavior == "trigger_reflection":
            base_mag = round(min(MAX_INFLUENCE, tension * 0.8), 4)
            return [MetaVector(
                direction="trigger_layer6_reflection",
                magnitude=round(min(MAX_INFLUENCE, base_mag * gain), 4),
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
            # Wire 24: brain_* diagnostic fields (add only, never overwrite existing)
            "brain_affective_reset_read": round(self._last_affective_reset, 4),
            "brain_reset_gain": round(self._last_reset_gain, 4),
            "brain_quiet_gain": round(self._last_quiet_gain, 4),
        }