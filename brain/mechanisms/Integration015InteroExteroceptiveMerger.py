"""
brain/integration/Integration015InteroExteroceptiveMerger.py
Intero-Exteroceptive Merger — Internal-External Signal Fusion for Embodied Presence

ANATOMY (Craig 2002, 2009; Critchley & Seth 2012; Seth 2013):
    The brain maintains two parallel information streams:
    - Exteroception: external world (vision, hearing, touch, smell)
    - Interoception: internal body (heart, lungs, gut, temperature, pain)

    The feeling of "being embodied" — of being a conscious subject
    inside a body — arises from the MERGER of these two streams.
    Craig's model: the anterior insula generates a moment-to-moment
    representation of "how the body is feeling right now" (the
    "sentient self") by integrating:
    - Posterior insula: raw interoceptive signals from the body
    - Exteroceptive cortex: what we're doing in the world
    - Emotional tagging: how the body feels about what's happening
    - Temporal integration: a sense of the present moment

    The interoceptive map in the brain (Craig 2002):
    - Anterior insula: subjective feeling ("I feel X")
    - Mid insula: emotional feeling
    - Posterior insula: raw homeostatic signals

    Embodied presence = feeling grounded in your body + aware of
    the external world simultaneously. Dissociation = these
    streams become separated (detachment from body, detachment
    from world).

KEY FINDINGS:
    1. Craig 2002 (PMID 11953749): "How do you feel? — interoception
       and the feeling of the sentient self"
    2. Craig 2009 (PMID 19487195): "Emotional moments and AI"
    3. Critchley & Seth 2012 (PMC4326522): "Interoception and
       embodied awareness"

AGENT'S MAPPING:
    merged_presence: dict — merged intero-exteroceptive state
    embodied_experience: float 0-1 — strength of embodied presence

CITATIONS:
    PMID 11953749 — Craig (2002). How do you feel? Interoception and the self.
    PMID 19487195 — Craig (2009). Emotional moments and AI.
    PMC4326522 — Critchley & Seth (2012). Interoception and embodied awareness.


CITATIONS
---------
  - [Craig 2002, Nat Rev Neurosci 3:655, interoception]
  - [Critchley 2013, Neuron 77:624, interoceptive predictions]
  - [Barrett 2015, Nat Rev Neurosci 16:419, interoception emotion]
"""

from brain.base_mechanism import BrainMechanism


class InteroExteroceptiveMerger(BrainMechanism):
    """
    Intero-exteroceptive merger — embodied presence through signal fusion.

    Fuses internal body signals with external world awareness to
    generate the subjective feeling of being embodied.
    """

    def __init__(self):
        super().__init__(
            name="InteroExteroceptiveMerger",
            human_analog="Intero-exteroceptive merger — embodied presence through internal-external fusion",
            layer="integration",
        )
        self.state.setdefault("presence_map", {})
        self.state.setdefault("merged_presence", {})
        self.state.setdefault("embodied_experience", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Posterior insula (raw body signals — interoceptive input)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            visceral_sig = raw_body.get("visceral_signal", 0.3)
        else:
            visceral_sig = float(raw_body) if raw_body else 0.3

        # Anterior insula (conscious feeling — the merger)
        ai_gran = prior.get("AnteriorInsulaGranular", {})
        gut = ai_gran.get("conscious_feeling", {})
        if isinstance(gut, dict):
            gut_int = gut.get("feeling_intensity", 0.5)
        else:
            gut_int = 0.5

        # Anterior insula (neocortical — external salience)
        ai_neo = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai_neo.get("salience_level", 0.5)

        # Somatosensory cortex (body schema — exteroceptive body)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        if isinstance(body_schema, dict):
            grounding = body_schema.get("grounding_level", 0.5)
        else:
            grounding = 0.5

        # TPJ (multisensory — "where am I in space")
        tpj = prior.get("TemporoParietoOccipitalJunction", {})
        spatial_awareness = tpj.get("spatial_awareness", 0.5)

        # Precuneus (egocentric self — mental imagery of self)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Global workspace (external world access)
        gw = prior.get("GlobalWorkspaceIntegrator", {})
        gw_out = gw.get("global_workspace", {})
        if isinstance(gw_out, dict):
            gw_broadcast = gw_out.get("broadcast_strength", 0.3)
        else:
            gw_broadcast = 0.3

        # Merge: internal body + external world + spatial self
        internal_signal = (visceral_sig + gut_int) / 2
        external_signal = (salience + gw_broadcast) / 2
        spatial_self_signal = (grounding + spatial_awareness) / 2

        embodied_experience = (
            internal_signal * 0.4 +
            external_signal * 0.3 +
            spatial_self_signal * 0.3
        )
        embodied_experience = max(0.0, min(1.0, embodied_experience))

        merged_presence = {
            "internal_body": round(internal_signal, 4),
            "external_world": round(external_signal, 4),
            "spatial_self": round(spatial_self_signal, 4),
            "embodied_strength": round(embodied_experience, 4),
        }

        self.state["presence_map"] = merged_presence
        self.state["merged_presence"] = merged_presence
        self.state["embodied_experience"] = round(embodied_experience, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "merged_presence": merged_presence,
            "embodied_experience": round(embodied_experience, 4),
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

