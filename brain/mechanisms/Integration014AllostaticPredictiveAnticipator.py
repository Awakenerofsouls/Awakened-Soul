"""
brain/integration/Integration014AllostaticPredictiveAnticipator.py
Allostatic Predictive Anticipator — Proactive Resource Preparation

ANATOMY (Sterling 2012; McEwen 2008; Schulkin 2011):
    Allostasis = "stability through change" — the brain doesn't just
    maintain homeostasis (fixed setpoints), it actively PREDICTS
    and PREPARES for future needs. This is allostatic regulation:

    Example: Stress response. Rather than waiting for cortisol to
    drop before activating recovery, the brain anticipates that
    stress will end and PRE-ACTIVATES recovery mechanisms.

    The allostatic predictive system involves:
    - Hippocampus (context prediction: "this situation usually leads to X")
    - Amygdala (anticipatory anxiety: "this will be stressful")
    - Hypothalamus (preparing resources for predicted demand)
    - PFC (planning based on predicted needs)
    - VTA/mPFC (reward prediction for motivation)

    Key concept: "Predictive allostasis" (Sterling 2012). The brain
    sets allostatic (anticipatory) states based on prediction, not
    reaction. Example: eating before you're hungry — anticipating
    that energy will be needed.

    McEwen's "allostatic load" model: chronic over-prediction of
    threats leads to allostatic overload (chronic stress, disease).

KEY FINDINGS:
    1. Sterling 2012 (PMC3409569): "Allostasis: a predictive
       regulatory system" — predicts needs before they arise
    2. McEwen 2008 (PMC3139674): "Stress and allostatic load"
       — chronic over-prediction causes damage
    3. Schulkin 2011: "Allostasis and the predictive brain"

AGENT'S MAPPING:
    allostatic_prediction: dict — prediction output
    proactive_resource_allocation: float 0-1 — proactive preparation strength
    future_drive_state: dict — predicted future needs

CITATIONS:
    PMID 21684297 — Sterling (2012). Allostasis: a model of predictive regulation. Physiol Behav.
    PMID 31488322 — Schulkin & Sterling (2019). Allostasis: A Brain-Centered Predictive Mode. Trends Neurosci.
    PMID 29957178 — Sterling (2018). Predictive regulation and human design. Elife.
    PMC2830733 — Vann et al. (2009). Hippocampal prediction. Philos Trans R Soc Lond B Biol Sci.
    PMC3139674 — McEwen (2008). Stress and allostatic load. Ann N Y Acad Sci.


CITATIONS
---------
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Clark 2013, Behav Brain Sci 36:181, predictive coding]
  - [Rao 1999, Nat Neurosci 2:79, predictive coding cortex]
"""

from brain.base_mechanism import BrainMechanism


class AllostaticPredictiveAnticipator(BrainMechanism):
    """
    Allostatic predictive anticipator — proactive resource preparation.

    Predicts future drive states and pre-allocates resources
    before needs arise, going beyond reactive homeostasis.
    """

    def __init__(self):
        super().__init__(
            name="AllostaticPredictiveAnticipator",
            human_analog="Allostatic predictive anticipator — proactive resource preparation",
            layer="integration",
        )
        self.state.setdefault("prediction_model", {})
        self.state.setdefault("proactive_resource_allocation", 0.0)
        self.state.setdefault("future_drive_state", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal contextual prediction
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Amygdala (anticipatory emotional prediction)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Hypothalamus (current drive state)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            primal_urgency = hypo_out.get("primal_urgency", 0.5)
        else:
            primal_urgency = 0.5

        # vmPFC (regulatory prediction — how to prepare)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            vmpfc_strength = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            vmpfc_strength = 0.5

        # Anterior temporal (conceptual memory — what usually happens here)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # DLPFC (planning for predicted needs)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # VTA (motivation for predicted reward)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            motivation = vta_out.get("motivation_signal", 0.5)
        else:
            motivation = 0.5

        # Prediction model: based on context (hippocampus) + past (ATP) + emotion (amygdala)
        anticipation = consolidation * 0.3 + concept_bind * 0.2 + abs(emotional_tag) * 0.2 + primal_urgency * 0.3
        anticipation = max(0.0, min(1.0, anticipation))

        # Proactive allocation: prepare before need is critical
        proactive_resource_allocation = anticipation * (cognitive_ctrl * 0.4 + motivation * 0.4 + vmpfc_strength * 0.2)
        proactive_resource_allocation = max(0.0, min(1.0, proactive_resource_allocation))

        # Future drive state prediction
        future_drive_state = {
            "predicted_urgency": round(anticipation, 4),
            "predicted_motivation": round(motivation, 4),
            "predicted_emotion": round(emotional_tag, 4),
            "preparation_active": proactive_resource_allocation > 0.55,
        }

        self.state["prediction_model"] = future_drive_state
        self.state["proactive_resource_allocation"] = round(proactive_resource_allocation, 4)
        self.state["future_drive_state"] = future_drive_state
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "allostatic_prediction": future_drive_state,
            "proactive_resource_allocation": round(proactive_resource_allocation, 4),
            "future_drive_state": future_drive_state,
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

