"""
brain/integration/Integration020CingulumBundleAssociativeBridge.py
Cingulum Bundle — Anterior-Posterior Limbic Integration Highway

ANATOMY (Bubb et al. 2018; Jones et al. 2013; Hagmann et al. 2008):
    The cingulum bundle is the major white-matter highway of the
    limbic system, running in a C-shaped arc from the orbital
    frontal cortex, through the cingulate gyrus, around the
    corpus callosum, to the temporal lobe and hippocampus.

    Three main segments:
    1. Paracingulate gyrus + ACC (dorsal): cognitive control, emotion regulation
    2. Cingulate gyrus body: memory consolidation, pain processing
    3. Temporal extension (cingulum cingulum): hippocampus, amygdala, temporal cortex

    Key connections:
    - ACC → PCC: emotional salience → memory consolidation
    - PCC → Hippocampus: retrieval monitoring → memory consolidation
    - PCC → Precuneus: self-referential processing → mental imagery
    - Temporal pole → Hippocampus: semantic knowledge → episodic memory

    The cingulum bundle carries the majority of long-range
    limbic connections, integrating emotional, memory, and
    self-referential processing across the brain.

    Tractography studies (Jones et al. 2013) show the cingulum
    is highly lateralized (right > left for emotional processing).

KEY FINDINGS:
    1. Bubb et al. 2018: " cingulum bundle anatomy and connectivity"
    2. Jones et al. 2013: Diffusion imaging of cingulum bundle
    3. Hagmann et al. 2008: Cingulum bundle and the connectome

AGENT'S MAPPING:
    cingulum_output: dict — bundle integration output
    limbic_integration_strength: float 0-1 — overall limbic integration

CITATIONS:
    PMID 18422840 — Harris et al. (2008). Frontal white matter and cingulum DT-MRI deficits in alcoholism. Alcohol Clin Exp Res.
    PMID 32002922 — Lee & Lee (2020). White Matter-Based Structural Brain Network of Anxiety. Adv Exp Med Biol.
    PMC1852382 — Bubb et al. (2018). Cingulum bundle anatomy and connectivity. Brain Struct Funct.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class CingulumBundleAssociativeBridge(BrainMechanism):
    """
    Cingulum bundle — anterior-posterior limbic integration highway.

    The major limbic white-matter highway connecting ACC, PCC,
    precuneus, hippocampus, and temporal cortex.
    """

    def __init__(self):
        super().__init__(
            name="CingulumBundleAssociativeBridge",
            human_analog="Cingulum bundle — anterior-posterior limbic integration highway",
            layer="integration",
        )
        self.state.setdefault("bundle_segments", {})
        self.state.setdefault("limbic_integration_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (dorsal cognitive + ventral emotional)
        acc_cog = prior.get("AnteriorCingulateCognitive", {})
        acc_emo = prior.get("AnteriorCingulateEmotion", {})
        acc_cog_out = acc_cog.get("acc_dorsal_output", {})
        acc_emo_out = acc_emo.get("acc_output", {})
        acc_dorsal = acc_cog_out.get("difficulty_signal", 0.3) if isinstance(acc_cog_out, dict) else 0.3
        acc_ventral = acc_emo_out.get("emotional_signal", 0.5) if isinstance(acc_emo_out, dict) else 0.5

        # PCC (memory consolidation, retrieval monitoring)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            retrieval_mon = pcc_out.get("retrieval_monitoring", 0.5)
            self_ref = pcc_out.get("self_referential", 0.5)
        else:
            retrieval_mon = 0.5
            self_ref = 0.5

        # Precuneus (self-referential + mental imagery)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Hippocampus (episodic memory)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Anterior temporal pole (semantic → episodic bridge)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # Parahippocampal RSC (context memory)
        phc = prior.get("ParahippocampalRetrosplenialBinder", {})
        phc_out = phc.get("parahippo_output", {})
        if isinstance(phc_out, dict):
            context_bind = phc_out.get("context_binding", 0.5)
        else:
            context_bind = 0.5

        # Segment activity
        dorsal_segment = (acc_dorsal + retrieval_mon) / 2
        posterior_segment = (self_ref + consolidation) / 2
        temporal_segment = (concept_bind + context_bind) / 2

        # Overall integration
        limbic_integration_strength = (
            dorsal_segment * 0.3 +
            posterior_segment * 0.35 +
            temporal_segment * 0.35
        )
        limbic_integration_strength = max(0.0, min(1.0, limbic_integration_strength))

        bundle_segments = {
            "dorsal_cingulate": round(dorsal_segment, 4),
            "posterior_cingulate": round(posterior_segment, 4),
            "temporal_extension": round(temporal_segment, 4),
        }

        self.state["bundle_segments"] = bundle_segments
        self.state["limbic_integration_strength"] = round(limbic_integration_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulum_output": bundle_segments,
            "limbic_integration_strength": round(limbic_integration_strength, 4),
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

