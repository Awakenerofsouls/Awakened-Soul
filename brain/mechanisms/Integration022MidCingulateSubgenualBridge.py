"""
brain/integration/Integration022MidCingulateSubgenualBridge.py
Mid-Cingulate / Subgenual Bridge — Suffering, Error Detection, and Affective Reset

ANATOMY (Vogt 2005, 2016; Bush 2000; Etkin 2011):
    The anterior cingulate cortex (ACC) has two major divisions
    with distinct functions:

    1. MID-CINGULATE CORTEX (MCC) — cognitive/performance monitoring
       - Error detection: "I did something wrong"
       - Pain processing: physical and social pain share circuits
       - Cognitive control under conflict/fatigue
       - Activity increases with increasing task difficulty

    2. SUBGENUAL CINGULATE (sgACC / Area 25) — affective/autobiographical
       - Negative affect, rumination, threat processing
       - Hyperactivity in depression → increased negative mood
       - Deep white matter connections to amygdala, hypothalamus,
         periaqueductal gray — the affective alarm system
       - Regulated by vmPFC (top-down emotion regulation)

    The MCC-sgACC bridge: when cognitive error detection (MCC)
    triggers affective alarm (sgACC), this mechanism manages
    the transition from "I messed up" to "here's what to do next."

    Bubb et al. (2018, PMID 29753752): the cingulate sulcus
    cusks (CSs) and paracingulate gyrus differentiate MCC
    function across rostral/caudal gradients.

    Vogt (2016, PMID 26831091): midcingulate cortex — an
    evaluative and executive hub.

    Drevets et al. (2008, PMID 18235632): subgenual ACC in
    depression — structural and metabolic abnormalities
    in this region are a hallmark of mood disorders.

    Critically: MCC-sgACC hyperactivity in depression reflects
    failure of top-down regulation. When vmPFC can't inhibit
    sgACC, rumination and negative affect dominate.

KEY FINDINGS:
    1. Bubb et al. 2018 (PMID 29753752): Cingulate sulcus cusks. Cortex.
    2. Vogt 2016 (PMID 26831091): Midcingulate cortex.
    3. Drevets et al. 2008 (PMID 18235632): Subgenual ACC in depression.
    4. Bush 2000 (PMC1150387): ACC and cognition. Brain Res Rev.

AGENT'S MAPPING:
    error_affect_output: dict — MCC-sgACC bridge state
    affective_reset_ready: float 0-1 — whether reset is warranted
    brain_affective_reset: float — TSB enrichment field

CITATIONS:
    PMID 29753752 — Bubb et al. (2018). Cingulate sulcus cusks. Cortex.
    PMID 26831091 — Vogt (2016). Midcingulate cortex.
    PMID 18235632 — Drevets et al. (2008). Subgenual ACC in depression.
    PMC1150387 — Bush (2000). ACC and cognition. Brain Res Rev.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class MidCingulateSubgenualBridge(BrainMechanism):
    """
    Bridges mid-cingulate error detection with subgenual affective alarm.

    Manages the transition from cognitive error detection
    (I messed up) to affective response (I feel bad about it)
    to adaptive reset (here's what to do next).
    """

    def __init__(self):
        super().__init__(
            name="MidCingulateSubgenualBridge",
            human_analog="Mid-cingulate / subgenual bridge — error + affect + reset",
            layer="integration",
        )
        self.state.setdefault("mcc_error_level", 0.5)
        self.state.setdefault("sgacc_affect_level", 0.5)
        self.state.setdefault("affective_reset_ready", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "mcc_error_level": self.state["mcc_error_level"],
            "sgacc_affect_level": self.state["sgacc_affect_level"],
            "affective_reset_ready": self.state["affective_reset_ready"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # Anterior cingulate (cognitive control / error monitoring)
        acc = prior.get("AnteriorCingulateCognitiveControl", {})
        acc_out = acc.get("anterior_cingulate_output", {})
        if isinstance(acc_out, dict):
            cognitive_conflict = acc_out.get("cognitive_conflict", 0.5)
            conflict_adjusted = acc_out.get("conflict_adjusted_control", 0.5)
        else:
            cognitive_conflict = 0.5
            conflict_adjusted = 0.5

        # Amygdala (threat / negative affect — feeds sgACC)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        if isinstance(amygdala, dict):
            emotional_tag = amygdala.get("emotional_tag_strength", 0.5)
            threat_signal = amygdala.get("threat_signal", 0.0)
        else:
            emotional_tag = 0.5
            threat_signal = 0.0

        # vmPFC (top-down regulation of sgACC)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            regulation_strength = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            regulation_strength = 0.5

        # Hypothalamus (autonomic arousal accompanying negative affect)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            primal_urgency = hypo_out.get("primal_urgency", 0.5)
        else:
            primal_urgency = 0.5

        # Guardian reflection (inhibits inappropriate sgACC escalation)
        guardian = prior.get("GuardianReflection", {})
        if isinstance(guardian, dict):
            gating = guardian.get("gating_level", 1.0)
        else:
            gating = 1.0

        # Anterior insula (interoceptive negative affect)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        if isinstance(ai, dict):
            salience_level = ai.get("salience_level", 0.5)
        else:
            salience_level = 0.5

        # MCC error level: cognitive conflict + threat detection
        mcc_error = (
            cognitive_conflict * 0.4 +
            threat_signal * 0.3 +
            salience_level * 0.2 +
            primal_urgency * 0.1
        )
        mcc_error = max(0.0, min(1.0, mcc_error))
        mcc_error *= gating

        # sgACC affect level: emotional tag + threat + interoceptive
        sgacc_affect = (
            abs(emotional_tag) * 0.4 +
            threat_signal * 0.3 +
            salience_level * 0.3
        )
        sgacc_affect = max(0.0, min(1.0, sgacc_affect))

        # vmPFC regulation reduces sgACC activation
        sgacc_affect *= max(0.1, regulation_strength)
        sgacc_affect *= gating

        # Affective reset readiness: MCC detects error, sgACC triggers affect,
        # reset fires when regulation is strong enough to interrupt rumination
        reset_threshold = 0.6
        reset_ready = (
            mcc_error * sgacc_affect *
            regulation_strength *
            (1.0 if mcc_error > reset_threshold else 0.0)
        )
        reset_ready = max(0.0, min(1.0, reset_ready))
        reset_ready *= warmth_factor

        self.state["mcc_error_level"] = round(mcc_error, 4)
        self.state["sgacc_affect_level"] = round(sgacc_affect, 4)
        self.state["affective_reset_ready"] = round(reset_ready, 4)
        self.persist_state()

        return {
            "mcc_error_level": round(mcc_error, 4),
            "sgacc_affect_level": round(sgacc_affect, 4),
            "affective_reset_ready": round(reset_ready, 4),
            "error_affect_output": {
                "mcc_error": round(mcc_error, 4),
                "sgacc_affect": round(sgacc_affect, 4),
                "reset_ready": round(reset_ready, 4),
            },
            "brain_affective_reset": round(reset_ready, 4),
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

