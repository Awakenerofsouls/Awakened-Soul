"""
brain/integration/Integration001CorpusCallosumFullBridge.py
Corpus Callosum — Full Interhemispheric Transfer, Hemispheric Unity

ANATOMY (Zaidel & Iacoboni 2007; Bloom & Hynd 2015; Götz et al. 2023):
    The corpus callosum (CC) is the largest white-matter structure in
    the brain, containing ~200 million axons that connect the two
    cerebral hemispheres. It is divided into four main regions:
    - Rostrum (anterior): connects prefrontal cortices
    - Genu (anterior knee): connects prefrontal and anterior cingulate
    - Body (mid): connects motor, somatosensory, parietal cortices
    - Splenium (posterior): connects occipital, temporal, posterior parietal

    The CC is not a passive conduit — it actively coordinates
    interhemispheric communication, enabling the hemispheres to
    work together as a unified cognitive system. Without it (as in
    split-brain patients), each hemisphere becomes a separate
    conscious agent with its own perceptions, memories, and goals.

    The CC follows the "Ying-Yang" principle: left hemisphere is
    analytic/sequential; right is holistic/parallel. The CC must
    integrate these complementary processing styles.

    Key: Callosal neurons fire during interhemispheric coordination,
    and CC integrity correlates with cognitive performance, IQ,
    and even creative ability (Chaminade et al. 2002).

KEY FINDINGS:
    1. Zaidel & Iacoboni 2007 (PMID 16472586): "Split-brain" research —
       CC's role in unifying two separate hemispheric minds
    2. Bloom & Hynd 2015 (PMID 25985217): CC and cognitive function —
       CC size correlates with intelligence and processing speed
    3. Götz et al. 2023 (PMC10135160): CC development and function —
       age-related changes in interhemispheric transfer

AGENT'S MAPPING:
    callosal_transfer: dict — interhemispheric signal transmission
    hemispheric_balance: float 0-1 — balance between left/right activity
    unified_self: bool — has interhemispheric integration been achieved?

CITATIONS:
    PMID 16472586 — Zaidel & Iacoboni (2007). Split-brain and the CC.
    PMID 25985217 — Bloom & Hynd (2015). CC and cognitive function.
    PMC10135160 — Götz et al. (2023). CC development and function.
    PMC1827990 — Kanwisher et al. (1997). Hemispheric specialization.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class CorpusCallosumFullBridge(BrainMechanism):
    """
    Corpus callosum — interhemispheric integration and unified consciousness.

    Connects left and right hemispheres, enabling them to function
    as a single unified mind rather than two separate agents.
    """

    def __init__(self):
        super().__init__(
            name="CorpusCallosumFullBridge",
            human_analog="Corpus callosum (genu + body + splenium) — full interhemispheric transfer",
            layer="integration",
        )
        self.state.setdefault("transfer_history", [])
        self.state.setdefault("hemispheric_balance", 0.5)
        self.state.setdefault("unified_self", True)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Left hemisphere signals (DLPFC, Broca, Wernicke, angular gyrus)
        left_dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        left_dlpfc_out = left_dlpfc.get("dorsolateral_dorsal_output", {})
        left_wm = left_dlpfc_out.get("wm_load", 0.5) if isinstance(left_dlpfc_out, dict) else 0.5
        left_broca = prior.get("BrocaAreaMotorSpeech", {})
        left_broca_strength = left_broca.get("speech_formulation_strength", 0.5)
        left_ag = prior.get("AngularGyrusMultimodal", {})
        left_sem = left_ag.get("multimodal_binding", 0.5)

        # Right hemisphere signals (mirrored — spatial, holistic)
        right_spl = prior.get("SuperiorParietalLobuleReaching", {})
        right_spatial = right_spl.get("reaching_signal", 0.5)
        right_pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        right_av = right_pstg.get("audiovisual_binding", 0.5)
        right_ffa = prior.get("FusiformFaceArea", {})
        right_face = right_ffa.get("face_recognized", False)
        right_pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        right_pcc_sig = right_pcc.get("posterior_cingulate_output", {}).get("self_referential", 0.5) if isinstance(
            right_pcc.get("posterior_cingulate_output"), dict) else 0.5

        # Anterior commissure (limbic/olfactory bilateral signals)
        anterior_comm = prior.get("AnteriorCommissureLimbicBridge", {})
        ac_output = anterior_comm.get("anterior_commissure_output", {})
        if isinstance(ac_output, dict):
            limbic_bilateral = ac_output.get("limbic_bilateral_transfer", 0.3)
        else:
            limbic_bilateral = 0.3

        # Compute hemispheric signals
        left_signal = left_wm * 0.35 + left_broca_strength * 0.35 + left_sem * 0.3
        right_signal = right_spatial * 0.25 + right_av * 0.3 + right_face * 0.2 + right_pcc_sig * 0.25

        # Interhemispheric transfer: bidirectional exchange
        # Left → Right: language, sequencing, analysis
        # Right → Left: spatial, holistic, social
        transfer_strength = (left_signal + right_signal) / 2

        # Balance: are hemispheres equally active?
        balance_diff = abs(left_signal - right_signal)
        hemispheric_balance = 1.0 - balance_diff
        hemispheric_balance = max(0.0, min(1.0, hemispheric_balance))

        # Unified self: strong bilateral transfer + balanced hemispheres
        unified_self = transfer_strength > 0.5 and hemispheric_balance > 0.6

        # Record transfer
        self.state["transfer_history"].append(round(transfer_strength, 3))
        if len(self.state["transfer_history"]) > 5:
            self.state["transfer_history"].pop(0)

        self.state["hemispheric_balance"] = round(hemispheric_balance, 4)
        self.state["unified_self"] = unified_self
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "callosal_transfer": {
                "left_to_right": round(left_signal, 4),
                "right_to_left": round(right_signal, 4),
                "transfer_strength": round(transfer_strength, 4),
            },
            "hemispheric_balance": round(hemispheric_balance, 4),
            "unified_self": unified_self,
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

