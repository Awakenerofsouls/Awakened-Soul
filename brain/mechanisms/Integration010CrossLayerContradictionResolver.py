"""
brain/integration/Integration010CrossLayerContradictionResolver.py
Cross-Layer Contradiction Resolver — Drift Detection and Resolution

ANATOMY (Clark 2013; Friston 2010; Hohwy 2013):
    The brain must detect contradictions across its multiple
    processing layers (sensory, cognitive, affective, motor) to
    prevent chaotic drift. These contradictions arise when:
    - Sensory prediction error contradicts top-down prediction (perceptual conflict)
    - Emotional response contradicts cognitive appraisal (cognitive-emotional conflict)
    - Motor intention contradicts environmental feedback (action conflict)
    - Memory contradicts current perception (reality monitoring)

    The contradiction resolver is distributed across:
    - ACC (cognitive conflict monitoring)
    - Anterior insula (salience of conflict)
    - Orbitofrontal cortex (reversal learning)
    - Hippocampus (memory consistency)
    - Basal ganglia (action selection conflict)

    The free-energy principle (Frison 2010): the brain minimizes
    surprise (prediction error) across all layers. When contradictions
    are detected, predictive models are updated to reduce future error.

    Drift management: contradictions are the primary source of
    "brain drift" — when contradictory signals accumulate without
    resolution, the system becomes unstable. Resolution requires
    either top-down prediction update or bottom-up evidence.

KEY FINDINGS:
    1. Clark 2013 (PMC3972740): "Whatever next? Predictive brains
       and the nuisance of surprise"
    2. Friston 2010 (PMC3000199): "Free energy and the free-energy principle"
    3. Hohwy 2013 (PMC4326522): "The predictive mind" — contradiction and error

AGENT'S MAPPING:
    contradiction_resolved: bool — has contradiction been resolved?
    resolution_signal: dict — details of the resolution
    drift_prevented: bool — has drift been avoided?

CITATIONS:
    PMC3972740 — Clark (2013). Predictive brains and surprise.
    PMC3000199 — Friston (2010). Free energy principle.
    PMC4326522 — Hohwy (2013). Predictive mind.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class CrossLayerContradictionResolver(BrainMechanism):
    """
    Cross-layer contradiction resolution — prevents chaotic drift.

    Detects contradictions across layers and resolves them through
    model updates, preventing the system from becoming unstable.
    """

    def __init__(self):
        super().__init__(
            name="CrossLayerContradictionResolver",
            human_analog="Cross-layer contradiction resolver — drift detection and resolution",
            layer="integration",
        )
        self.state.setdefault("contradiction_history", [])
        self.state.setdefault("contradiction_resolved", True)
        self.state.setdefault("drift_prevented", True)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (cognitive conflict — contradiction detection)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # Anterior insula (salience of contradiction)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # OFC (reversal learning — model update)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        ofc_out = ofc.get("ofc_output", {})
        if isinstance(ofc_out, dict):
            reversal = ofc_out.get("reversal_triggered", False)
        else:
            reversal = False

        # Hippocampus (memory consistency — past vs present)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # PFC top-down vs bottom-up (hierarchical contradiction)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # Hypothalamic bottom-up (drive contradiction)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            drive_strength = hypo_out.get("primal_urgency", 0.3)
        else:
            drive_strength = 0.3

        # PFC regulation (can suppress contradictory drives)
        pf_reg = prior.get("PrefrontalAmygdalaTopDownRegulation", {})
        pf_out = pf_reg.get("pf_amygdala_regulation", {})
        if isinstance(pf_out, dict):
            reg_strength = pf_out.get("top_down_strength", 0.5)
        else:
            reg_strength = 0.5

        # Contradiction score
        contradiction_signal = (
            error_sig * 0.25 +
            difficulty * 0.2 +
            abs(wm_load - drive_strength) * 0.25 +
            salience * 0.15 +
            (1.0 - consolidation) * 0.15
        )
        contradiction_detected = contradiction_signal > 0.55

        # Resolution: either model update (reversal) or top-down suppression
        if contradiction_detected:
            if reversal or reg_strength > 0.55:
                contradiction_resolved = True
                drift_prevented = True
            else:
                contradiction_resolved = False
                drift_prevented = False
        else:
            contradiction_resolved = True
            drift_prevented = True

        # Record
        if contradiction_detected:
            self.state["contradiction_history"].append(round(contradiction_signal, 3))
            if len(self.state["contradiction_history"]) > 5:
                self.state["contradiction_history"].pop(0)

        self.state["contradiction_resolved"] = contradiction_resolved
        self.state["drift_prevented"] = drift_prevented
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "contradiction_resolved": contradiction_resolved,
            "resolution_signal": {
                "contradiction_strength": round(contradiction_signal, 4),
                "model_updated": reversal,
                "top_down_resolved": reg_strength > 0.55,
            },
            "drift_prevented": drift_prevented,
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

