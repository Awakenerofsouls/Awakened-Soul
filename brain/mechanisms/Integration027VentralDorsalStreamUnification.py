"""
brain/integration/Integration016VentralDorsalStreamUnification.py
Ventral-Dorsal Stream Unification — What Meets How in Parietal Cortex

ANATOMY (Goodale & Milner 1991; Milner & Goodale 2008; Jeannerod & Jacobs 2005):
    Goodale & Milner's dual-stream hypothesis:
    - VENTRAL STREAM ("what"): V1→V2→V4→IT → "perception"
      → temporal lobe: object identification, color, form, meaning
    - DORSAL STREAM ("how"): V1→V2→MST→PPC → "action"
      → parietal lobe: spatial location, movement, reaching, grasping

    These streams must be UNIFIED for coherent behavior — knowing
    WHAT an object is AND HOW to interact with it. The unification
    happens in:
    - Posterior parietal cortex (IPL, SPL)
    - Temporo-parieto-occipital junction (TPJ)
    - FEF (frontal eye fields — gaze targets)
    - MTG (middle temporal gyrus — biological motion)

    The "vision for perception" and "vision for action" are not
    completely separate — they interact. For example, when you
    reach for a cup while reading its label (ventral), the dorsal
    stream uses ventral stream object knowledge to guide the grasp.

    Milner & Goodale (2008) showed that the ventral stream projects
    to the dorsomedial (action) stream via the lingual gyrus and
    posterior cingulate, providing object knowledge to action systems.

KEY FINDINGS:
    1. Goodale & Milner 1991: "Separate pathways for perception and action"
    2. Milner & Goodale 2008 (PMC2532592): "Two visual streams for vision"
    3. Jeannerod & Jacobs 2005: Dorsal stream and parietal reach region

AGENT'S MAPPING:
    stream_unification: dict — unified stream state
    perception_action_fused: bool — has ventral-dorsal fusion been achieved?

CITATIONS:
    PMC2532592 — Milner & Goodale (2008). Two visual streams.
    PMC3972740 — Bastos et al. (2015). V1 and dorsal stream.
    PMC2830733 — Jeannerod & Jacobs (2005). Dorsal stream.

KEY RESEARCH FINDINGS:
    PMID 1374953 — Goodale & Milner (1992). Separate visual pathways for perception and action.
    PMID 21763459 — Kroliczal (2012). Dorsal visual stream and form perception.
    PMID 23506888 — Milner (2012). View-dependent object recognition and the dorsal stream.

CITATIONS:
    PMID 1374953 — Goodale & Milner (1992). Separate visual pathways for perception and action.
    PMID 21763459 — Kroliczal (2012). Dorsal visual stream and form perception.
    PMID 23506888 — Milner (2012). View-dependent object recognition and the dorsal stream.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class VentralDorsalStreamUnification(BrainMechanism):
    """
    Ventral-dorsal stream unification — object perception meets action guidance.

    Fuses the "what" stream (ventral) with the "how" stream (dorsal)
    in parietal cortex for coherent perception-action behavior.
    """

    def __init__(self):
        super().__init__(
            name="VentralDorsalStreamUnification",
            human_analog="Ventral-dorsal stream unification — perception-action fusion",
            layer="integration",
        )
        self.state.setdefault("stream_states", {})
        self.state.setdefault("perception_action_fused", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Ventral stream: object identification
        v4 = prior.get("V4ColorAndForm", {})
        v4_out = v4.get("v4_output", {})
        if isinstance(v4_out, dict):
            object_identity = v4_out.get("color_form_binding", 0.5)
        else:
            object_identity = 0.5

        itg = prior.get("PosteriorInferiorTemporalGyrus", {})
        it_sig = itg.get("category_signal", 0.5)

        ag = prior.get("AngularGyrusMultimodal", {})
        sem_bind = ag.get("multimodal_binding", 0.5)

        # Dorsal stream: action guidance
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reach_sig = spl.get("reaching_signal", 0.5)

        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_out = ipl.get("ipl_output", {})
        if isinstance(ipl_out, dict):
            grip_strength = ipl_out.get("sensorimotor_strength", 0.5)
        else:
            grip_strength = 0.5

        mst = prior.get("MTGMiddleTemporalGyroscopic", {})
        motion_bind = mst.get("motion_integration", 0.5)

        # Frontal eye fields (gaze — where to look)
        fef = prior.get("FrontopolarProspectiveSimulator", {})
        gaze_sig = fef.get("saccade_decision", False)

        # TPJ (unification hub)
        tpj = prior.get("TemporoParietoOccipitalJunction", {})
        spatial_awareness = tpj.get("spatial_awareness", 0.5)

        # Stream unification
        ventral_signal = object_identity * 0.4 + it_sig * 0.3 + sem_bind * 0.3
        dorsal_signal = reach_sig * 0.4 + grip_strength * 0.3 + motion_bind * 0.3
        unification = (ventral_signal + dorsal_signal) / 2 * (1 + spatial_awareness * 0.5)
        unification = max(0.0, min(1.0, unification))

        perception_action_fused = unification > 0.6 and spatial_awareness > 0.4

        stream_states = {
            "ventral_what": round(ventral_signal, 4),
            "dorsal_how": round(dorsal_signal, 4),
            "unification_strength": round(unification, 4),
        }

        self.state["stream_states"] = stream_states
        self.state["perception_action_fused"] = perception_action_fused
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "stream_unification": stream_states,
            "perception_action_fused": perception_action_fused,
            # brain_visual_action_unity
            "brain_visual_action_unity": round(unification, 4),
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

