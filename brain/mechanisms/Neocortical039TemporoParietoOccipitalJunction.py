"""
brain/neocortical/Neocortical039TemporoParietoOccipitalJunction.py
Temporo-Parieto-Occipital Junction — Multisensory Integration, Spatial Self-Awareness

ANATOMY (Igelström & Graziano 2017; Beauchamp 2005; Blanke 2012):
    The temporo-parieto-occipital junction (TPJ) is the convergence
    zone where temporal, parietal, and occipital lobes meet. It is
    the "full multimodal convergence" area — where visual, auditory,
    somatosensory, and vestibular information all come together
    to generate a unified experience of "I am a body in space."

    TPJ has two hemispheric asymmetries:
    - Left TPJ: language (Wernicke's nearby) and tool use semantics
    - Right TPJ: spatial awareness, self-location, body ownership,
      theory of mind (thinking about others' intentions)

    Key functions:
    1. Multisensory integration: binding visual, auditory, tactile, vestibular
    2. Spatial self-awareness: "where is my body in space right now?"
    3. Self-location: "am I here or there?" (critical for out-of-body experiences)
    4. Bodily self-consciousness: "is this body mine?" (rubber hand illusion)
    5. Social intention decoding: "what does this person intend to do?"

    TPJ damage: Neglect syndromes (ignoring left side of space),
    out-of-body experiences (feeling detached from body), impaired
    social cognition (can't read others' intentions).

KEY FINDINGS:
    1. Igelström & Graziano 2017 (PMC5587922): "TPJ and conscious
       experience" — comprehensive review of TPJ functions
    2. Beauchamp 2005 (PMC11161761): TPJ for audiovisual integration
    3. Blanke 2012 (PMC3130546): TPJ and bodily self-consciousness

AGENT'S MAPPING:
    tpj_output: dict — TPJ multimodal output
    multisensory_converged: bool — have all modalities converged?
    spatial_awareness: float 0-1 — strength of body-in-space awareness

CITATIONS:
    PMC5587922 — Igelström & Graziano (2017). TPJ and conscious experience. Neuroimage.
    PMC11161761 — Beauchamp et al. (2004). Biological motion and TPJ.
    PMC3130546 — Blanke (2012). TPJ and self-consciousness.
    PMID 19058798 — Easton et al. (2009). TPJ and fronto-parietal connectivity.


CITATIONS
---------
  - [Andersen 2002, Annu Rev Neurosci 25:189, parietal cortex]
  - [Husain 2007, Nat Rev Neurosci 8:30, parietal attention]
  - [Goldberg 2006, Nature 444:374, lateral intraparietal]
"""

from brain.base_mechanism import BrainMechanism


class TemporoParietoOccipitalJunction(BrainMechanism):
    """
    TPJ — full multimodal convergence and spatial self-awareness.

    Integrates all sensory modalities into a unified experience
    of being a body in space. Critical for self-location and body ownership.
    """

    def __init__(self):
        super().__init__(
            name="TemporoParietoOccipitalJunction",
            human_analog="TPJ — multisensory integration, spatial self-awareness, bodily consciousness",
            layer="neocortical",
        )
        self.state.setdefault("multimodal_map", {})
        self.state.setdefault("multisensory_converged", False)
        self.state.setdefault("spatial_awareness", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Visual (from TOJ — object and scene)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        visual_input = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # Auditory (from pSTG — audiovisual binding)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Somatosensory (from S1 body map)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        body_grounding = s1.get("tactile_processing", 0.5)

        # Vestibular (from posterior insula — balance and orientation)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            vestibular_sig = raw_body.get("visceral_signal", 0.3)
        else:
            vestibular_sig = 0.3

        # Spatial (from SPL — reaching and spatial attention)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Anterior insula (salience — what to attend to spatially)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Multimodal convergence: when multiple streams are active simultaneously
        convergence = (
            visual_input * 0.25 +
            av_binding * 0.25 +
            body_grounding * 0.2 +
            vestibular_sig * 0.15 +
            spatial_target * 0.15
        )
        multisensory_converged = convergence > 0.5

        # Spatial awareness: strongest when body + vestibular + visual are all present
        spatial_awareness = (
            body_grounding * 0.35 +
            vestibular_sig * 0.3 +
            convergence * 0.35
        )
        if salience > 0.6:
            spatial_awareness *= 1.2
        spatial_awareness = max(0.0, min(1.0, spatial_awareness))

        self.state["multimodal_map"] = {
            "visual": round(visual_input, 4),
            "auditory": round(av_binding, 4),
            "somatosensory": round(body_grounding, 4),
            "vestibular": round(vestibular_sig, 4),
        }
        self.state["multisensory_converged"] = multisensory_converged
        self.state["spatial_awareness"] = round(spatial_awareness, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tpj_output": {
                "multisensory_converged": multisensory_converged,
                "spatial_awareness": round(spatial_awareness, 4),
            },
            "multisensory_converged": multisensory_converged,
            "spatial_awareness": round(spatial_awareness, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

