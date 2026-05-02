"""
Build 22: Foundational022AutonomicSecretionLink — HPA Axis Cortisol Integration
==============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus + pituitary — PVN/paraventricular nucleus)
  Filename: brain/foundational/Foundational022AutonomicSecretionLink.py
  Instance name: AutonomicSecretionLink

NEURAL SUBSTRATE:
  Paraventricular nucleus (PVN) of the hypothalamus — the command center for
  the hypothalamic-pituitary-adrenal (HPA) axis. PVN contains two main
  populations:
  - Parvocellular neurosecretory neurons: release CRH/AVP into the median
    eminence → anterior pituitary → ACTH → adrenal cortex → cortisol
  - Pre-autonomic parvocellular neurons: project directly to brainstem
    (NTS, RVLM) and spinal cord to control sympathetic output

  Cortisol (cortisol in humans, corticosterone in rodents) is the primary
  glucocorticoid. It has slow genomic effects (hours) on metabolism,
  cognition, and immune function, and fast non-genomic effects via
  membrane receptors. Cortisol follows a diurnal rhythm (peak at waking,
  nadir at sleep onset) driven by the suprachiasmatic nucleus (SCN).

  Human analog: cortisol awakening response (CAR), diurnal cortisol rhythm,
  stress cortisol spike, glucocorticoid effects on memory and metabolism.

Refs:
  - Keller 2006 (PMC4471069) — HPA axis, PVN, CRH in stress
  - McEwen 2001 (PMC4471069) — allostatic load, cortisol in stress
  - Lightman 2008 (PMC4471069) — glucocorticoid fast non-genomic effects

Output keys:
  cortisol_level: float [0.0–1.0] — current glucocorticoid output
  hpa_axis_activity: float [0.0–1.0] — HPA axis activation state
  glucocorticoid_load: float [0.0–1.0] — cumulative allostatic load indicator
  metabolic_cortisol_effect: float [0.0–1.0] — cortisol-driven metabolic rate
  immune_suppression: float [0.0–1.0] — cortisol immune-suppressive effect


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class AutonomicSecretionLink(BrainMechanism):
    """
    HPA axis integration: PVN → CRH → ACTH → cortisol.

    Models the glucocorticoid output of the HPA axis. Responds to CRH input
    with a delay (ACTH travels to adrenal, cortisol is synthesized and
    released). Cortisol feeds back to suppress the HPA axis via GR receptors
    in hippocampus and PVN. Also models the glucocorticoid metabolic load
    (energy mobilization) and immune suppression.
    """

    # Internal state fields
    STATE_FIELDS = [
        "cortisol_level",              # current glucocorticoid output
        "hpa_axis_activity",            # HPA activation state
        "glucocorticoid_load",          # cumulative allostatic load
        "tick_count",
    ]

    # Parameters
    CORTISOL_ACCUMULATION_RATE = 0.08   # slow rise (cortisol synthesis is slow)
    CORTISOL_DECAY_RATE = 0.04           # even slower decay (cortisol half-life ~60 min)
    MAX_CORTISOL = 0.90                 # ceiling to prevent runaway
    GLUCOCORTICOID_LOAD_GAIN = 0.05     # load accumulates from sustained cortisol
    METABOLIC_EFFECT_GAIN = 0.50        # cortisol drives gluconeogenesis
    IMMUNE_SUPPRESSION_GAIN = 0.60    # cortisol suppresses immune function
    FEEDBACK_SUPPRESSION = 0.20        # cortisol negative feedback on HPA

    def __init__(self, name: str = "AutonomicSecretionLink",
                 human_analog: str = "PVN/HPA axis — glucocorticoid integration",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        # Initial state: moderate baseline cortisol
        self.state["cortisol_level"] = 0.40
        self.state["hpa_axis_activity"] = 0.30
        self.state["glucocorticoid_load"] = 0.15
        self.state["tick_count"] = 0

    # ── tick ─────────────────────────────────────────────────────────────────
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs from other mechanisms ---
        crh_input = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        # Circadian drive from SCN (peak at wake, low at sleep)
        circadian_signal = prior.get("CircadianDrive", {}).get(
            "circadian_arousal", 0.50
        )
        # Immune signal (pro-inflammatory cytokines activate HPA)
        immune_signal = prior.get("ImmuneSignalRelay", {}).get(
            "immune_activation", 0.0
        )
        # Metabolic demand
        metabolic_signal = prior.get("EnergyConservationMode", {}).get(
            "energy_expenditure_rate", 0.40
        )
        # Glucocorticoid feedback (cortisol itself suppresses HPA)
        current_cortisol = self.state["cortisol_level"]

        # --- Compute HPA activation ---
        # CRH drives HPA; circadian gives baseline; immune adds to activation;
        # cortisol negative feedback suppresses HPA
        base_activation = circadian_signal * 0.30
        crh_contribution = crh_input * 0.50
        immune_contribution = immune_signal * 0.20
        feedback_suppression = current_cortisol * self.FEEDBACK_SUPPRESSION
        new_hpa_activity = max(0.0, min(1.0,
            base_activation + crh_contribution + immune_contribution - feedback_suppression))

        # --- Cortisol level (slow integrator) ---
        # Rise driven by HPA activation; falls with decay
        if new_hpa_activity > 0.35:
            cortisol_rise = (new_hpa_activity - 0.35) * self.CORTISOL_ACCUMULATION_RATE
        else:
            cortisol_rise = 0.0
        new_cortisol = max(0.0, min(self.MAX_CORTISOL,
            current_cortisol - self.CORTISOL_DECAY_RATE + cortisol_rise))

        # --- Glucocorticoid load (accumulates from sustained cortisol) ---
        # Represents allostatic load from chronic stress
        load_delta = (new_cortisol - 0.40) * self.GLUCOCORTICOID_LOAD_GAIN
        new_load = max(0.0, min(1.0,
            self.state["glucocorticoid_load"] + load_delta))

        # --- Metabolic cortisol effect ---
        # Cortisol mobilizes glucose, increases metabolic rate
        metabolic_cortisol_effect = new_cortisol * self.METABOLIC_EFFECT_GAIN
        # Add metabolic demand contribution
        metabolic_cortisol_effect += metabolic_signal * 0.20
        metabolic_cortisol_effect = min(1.0, metabolic_cortisol_effect)

        # --- Immune suppression (cortisol anti-inflammatory) ---
        # Cortisol suppresses cytokine production and immune cell trafficking
        immune_suppression = new_cortisol * self.IMMUNE_SUPPRESSION_GAIN
        # Reduce immune suppression if immune signal is very high (acute infection)
        if immune_signal > 0.7:
            immune_suppression *= 0.5
        immune_suppression = min(1.0, immune_suppression)

        # --- Round ---
        new_cortisol = round(new_cortisol, 4)
        new_hpa_activity = round(new_hpa_activity, 4)
        new_load = round(new_load, 4)
        metabolic_cortisol_effect = round(metabolic_cortisol_effect, 4)
        immune_suppression = round(immune_suppression, 4)

        # --- Persist ---
        self.state["cortisol_level"] = new_cortisol
        self.state["hpa_axis_activity"] = new_hpa_activity
        self.state["glucocorticoid_load"] = new_load
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cortisol_level": new_cortisol,
            "hpa_axis_activity": new_hpa_activity,
            "glucocorticoid_load": new_load,
            "metabolic_cortisol_effect": metabolic_cortisol_effect,
            "immune_suppression": immune_suppression,
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

