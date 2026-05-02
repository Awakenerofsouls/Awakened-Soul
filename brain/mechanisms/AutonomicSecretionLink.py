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
  - [Loewy 1990, Annu Rev Physiol 52:691]
  - [Strack 1989, Brain Res 491:156]
  - [Saper 2002, Nature 418:935, doi:10.1038/nature00965]
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

    def __init__(self, name: str = "AutonomicSecretionLink_AutonomicSecretionLink",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


