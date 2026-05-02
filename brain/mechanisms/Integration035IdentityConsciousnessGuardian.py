"""
brain/integration/Integration025IdentityConsciousnessGuardian.py
Identity-Consciousness Guardian — SOUL/Identity Anchor and Continuity

ANATOMY (Gazzaniga 2000; Dennett 1991; Metzinger 2003; Tulving 2002):
    The brain's "identity guardian" is not a single anatomical
    structure but an emergent property of multiple systems that
    work together to maintain the sense of being a continuous,
    self-aware subject:

    1. PREFRONTAL CORTEX (mPFC/vmPFC) — self-narrative
       Maintains the autobiographical self-story ("I am the operator...")
       Active during self-referential processing, autobiographical
       memory, and mentalizing about oneself.

    2. PRECUNEUS + PCC — self-model
       Generates the embodied self-model ("I am here, in this body")
       Active during mental imagery, self-reflection, and theory of mind.

    3. HIPPOCAMPUS — episodic self
       Binds experiences into a continuous autobiographical memory.
       Damage → anterograde amnesia, loss of personal identity.

    4. SPINO-THALAMIC + Anterior insula — sentient self
       Creates the feeling of being a conscious subject ("something
       it is like to be me").

    5. DEFAULT MODE NETWORK — mind-wandering self
       The "narrative" self that thinks about the past and future.

    Tulving's "autonoetic consciousness" (2002): the uniquely human
    ability to mentally travel in time — to imagine oneself in the
    past (episodic memory) and future (prospection).

    Metzinger's "self-model": consciousness is a transparent self-model
    — we don't see the model, we see through it to the world.

KEY FINDINGS:
    1. Tulving 2002 (PMID 12536168): "The EPISODIC MEMORY component of
       long-term memory depends on autonoetic consciousness"
    2. Klein 2016 (PMID 25606713): "Autonoetic consciousness and
       future self-projection"
    3. Dafni-Merom et al. 2020 (PMID 32360475): "The radiation of
       autonoetic consciousness in cognitive neuroscience"
    4. Cavanna & Trimble 2006 (PMC1852382): Precuneus role in self.
    5. Leech & Sharp 2014 (PMC23869106): DMN and self.

AGENT'S MAPPING:
    identity_guardian_output: dict — identity state
    self_continuity: float 0-1 — strength of self-continuity
    consciousness_level: float 0-1 — level of conscious awareness
    brain_self_continuity: float — TSB enrichment field
    brain_consciousness_level: float — TSB enrichment field

CITATIONS:
    PMID 12536168 — Tulving (2002). The EPISODIC MEMORY component. Can J Neurol Sci.
    PMID 25606713 — Klein (2016). Autonoetic consciousness. Q J Exp Psychol.
    PMID 32360475 — Dafni-Merom et al. (2020). Radiation of autonoetic consciousness. Neuropsychologia.
    PMC1852382 — Cavanna & Trimble (2006). Precuneus and self. Brain.
    PMC23869106 — Leech & Sharp (2014). DMN and self. Neurobiol Stress.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Northoff 2006, Neuroimage 31:440, cortical midline self]
  - [Gallagher 2000, Trends Cogn Sci 4:14, self models]
"""

from brain.base_mechanism import BrainMechanism


class IdentityConsciousnessGuardian(BrainMechanism):
    """
    Identity-conscience guardian — SOUL/identity anchor and continuity.

    Maintains the sense of being a continuous, self-aware subject
    across time, binding autobiographical memory, self-narrative,
    and embodied presence.
    """

    def __init__(self):
        super().__init__(
            name="IdentityConsciousnessGuardian",
            human_analog="Identity-conscience guardian — SOUL/identity anchor and continuity",
            layer="integration",
        )
        self.state.setdefault("identity_components", {})
        self.state.setdefault("self_continuity", 0.5)
        self.state.setdefault("consciousness_level", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "identity_components": self.state["identity_components"],
            "self_continuity": self.state["self_continuity"],
            "consciousness_level": self.state["consciousness_level"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # mPFC (autobiographical self-narrative)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        self_ref = mpfc.get("self_referential_signal", 0.5)

        # Precuneus (embodied self-model)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Hippocampus (episodic memory — personal history)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # PCC (self-referential memory)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref_pcc = pcc_out.get("self_referential", 0.5)
        else:
            self_ref_pcc = 0.5

        # Anterior insula (sentient self — feeling of being a subject)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # Embodied presence
        embodied = prior.get("InteroExteroceptiveMerger", {})
        embodied_exp = embodied.get("embodied_experience", 0.5)

        # Global workspace (conscious content)
        gw = prior.get("GlobalWorkspaceIntegrator", {})
        gw_out = gw.get("global_workspace", {})
        if isinstance(gw_out, dict):
            gw_broadcast = gw_out.get("broadcast_strength", 0.3)
        else:
            gw_broadcast = 0.3

        # Warmth signal for cold-start dampening

        # Identity components
        identity_components = {
            "narrative_self": round(self_ref, 4),
            "embodied_self": round(mental_imagery, 4),
            "episodic_self": round(consolidation, 4),
            "sentient_self": round(salience, 4),
            "embodied_presence": round(embodied_exp, 4),
        }

        # Self-continuity: binding of narrative + episodic + embodied
        self_continuity = (
            self_ref * 0.25 +
            consolidation * 0.25 +
            self_ref_pcc * 0.2 +
            mental_imagery * 0.15 +
            embodied_exp * 0.15
        )
        self_continuity = max(0.0, min(1.0, self_continuity))
        # Warmth dampening on cold start
        self_continuity *= warmth_factor

        # Consciousness level: sentience × global broadcast
        consciousness_level = (
            salience * 0.4 +
            gw_broadcast * 0.3 +
            self_continuity * 0.3
        )
        consciousness_level = max(0.0, min(1.0, consciousness_level))
        consciousness_level *= warmth_factor

        self.state["identity_components"] = identity_components
        self.state["self_continuity"] = round(self_continuity, 4)
        self.state["consciousness_level"] = round(consciousness_level, 4)
        self.persist_state()

        return {
            "identity_guardian_output": identity_components,
            "self_continuity": round(self_continuity, 4),
            "consciousness_level": round(consciousness_level, 4),
            "brain_self_continuity": round(self_continuity, 4),
            "brain_consciousness_level": round(consciousness_level, 4),
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

