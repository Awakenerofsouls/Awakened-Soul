"""
brain/integration/Integration011AnteriorCommissureLimbicBridge.py
Anterior Commissure — Limbic/Olfactory Interhemispheric Bridge

ANATOMY (Diogo et al. 2009; Young et al. 1980; Brierley & Shaw 2002):
    The anterior commissure (AC) is a smaller interhemispheric fiber
    tract than the corpus callosum, connecting the two hemispheres
    primarily through:
    - Anterior temporal lobes (olfactory cortex)
    - Amygdala and hippocampal regions
    - Inferior and medial temporal cortex

    Unlike the corpus callosum (which connects homologous regions
    across hemispheres), the anterior commissure is particularly
    important for:
    - Olfactory processing (left-right olfactory integration)
    - Limbic system interhemispheric communication (amygdala, hippocampus)
    - Emotional memory (episodic memories with strong emotional valence)
    - Social recognition (face/emotional expressions across hemispheres)

    The AC is phylogenetically older than the corpus callosum and
    remains functional in split-brain patients (who have their
    corpus callosum severed but AC intact) — they show preserved
    emotional and olfactory interhemispheric transfer.

KEY FINDINGS:
    1. Diogo et al. 2009: "Comparative anatomy of the anterior commissure"
    2. Brierley & Shaw 2002: AC and emotional processing
    3. Young et al. 1980: AC and olfactory interhemispheric transfer

AGENT'S MAPPING:
    anterior_commissure_output: dict — AC output
    limbic_bilateral_transfer: float 0-1 — limbic signal crossing hemispheres

CITATIONS:
    PMC1827990 — Kanwisher et al. (1997). Hemispheric specialization.
    PMC2830733 — Vann et al. (2009). RSC and episodic memory.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCommissureLimbicBridge(BrainMechanism):
    """
    Anterior commissure — limbic and olfactory bilateral integration.

    Provides interhemispheric transfer for emotional, olfactory,
    and social signals when the corpus callosum is insufficient.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorCommissureLimbicBridge",
            human_analog="Anterior commissure — limbic/olfactory interhemispheric bridge",
            layer="integration",
        )
        self.state.setdefault("limbic_bilateral_transfer", 0.0)
        self.state.setdefault("emotional_signal_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Left amygdala
        l_amyg = prior.get("AmygdalaEmotionalAssociator", {})
        l_emotion = l_amyg.get("emotional_tag_strength", 0.0)

        # Right amygdala (via corpus callosum)
        r_pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        r_self = r_pcc.get("posterior_cingulate_output", {}).get("self_referential", 0.5) if isinstance(
            r_pcc.get("posterior_cingulate_output"), dict) else 0.5

        # Hippocampal emotional memory
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Septal limbic reward
        septal = prior.get("SeptalLateralReward", {})
        septal_out = septal.get("septal_output", {})
        if isinstance(septal_out, dict):
            limbic_reward = septal_out.get("reward_signal", 0.3)
        else:
            limbic_reward = 0.3

        # Corpus callosum (limits need for AC — strong CC reduces AC load)
        cc = prior.get("CorpusCallosumFullBridge", {})
        cc_out = cc.get("callosal_transfer", {})
        if isinstance(cc_out, dict):
            cc_strength = cc_out.get("transfer_strength", 0.5)
        else:
            cc_strength = 0.5

        # Limbic bilateral transfer: emotional × limbic × (1 - CC)
        # When CC is weak, AC takes over limbic transfer
        limbic_signal = abs(l_emotion) * 0.4 + consolidation * 0.3 + limbic_reward * 0.3
        limbic_bilateral_transfer = limbic_signal * (2.0 - cc_strength)
        limbic_bilateral_transfer = max(0.0, min(1.0, limbic_bilateral_transfer))

        self.state["limbic_bilateral_transfer"] = round(limbic_bilateral_transfer, 4)
        self.state["emotional_signal_strength"] = round(limbic_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_commissure_output": {
                "limbic_transfer": round(limbic_bilateral_transfer, 4),
                "emotional_strength": round(limbic_signal, 4),
            },
            "limbic_bilateral_transfer": round(limbic_bilateral_transfer, 4),
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

