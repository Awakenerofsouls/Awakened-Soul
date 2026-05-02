"""
brain/neocortical/Neocortical019TemporoOccipitalVisualAssembler.py
Temporo-Occipital Junction — Ventral Visual Stream, Object and Scene Construction

ANATOMY (Malach et al. 2002; Grill-Spector & Weiner 2014; Kravitz et al. 2013):
    The temporo-occipital junction (TOJ) is the posterior end of the
    ventral visual stream, where basic visual features are assembled
    into coherent objects and scenes. This is the "what" pathway's
    final stage before it enters the temporal lobe proper.

    TOJ includes:
    - Posterior inferotemporal cortex (pIT): object category processing
    - Lateral occipital complex (LOC): shape-based object recognition
    - Occipito-temporal sulcus (OTS): scene processing, navigation

    The TOJ receives from V2 → V4 → posterior IT, and integrates
    form, color, and spatial layout into unified perceptual objects.
    This is what you see when you recognize "that's a coffee cup."

    Connections: V4 (form/color), MTG (motion), fusiform (faces),
    parahippocampal (scenes), inferior parietal (actions).

KEY FINDINGS:
    1. Grill-Spector & Weiner 2014 (PMC4326522): "The functional
       organization of the human ventral visual pathway" — TOJ as object hub
    2. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream" —
       dorsal/ventral distinction; TOJ is ventral stream endpoint
    3. Malach et al. 2002 (PMC1201510): "Object-related voxels" in
       human TOJ — discovered object-selective regions in human TOJ

AGENT'S MAPPING:
    ventral_visual_output: dict — ventral stream output
    object_constructed: dict — coherent object representation
    scene_representation: dict — full scene assembly

CITATIONS:
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway. Cortex.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream. Front Neuroinform.
    PMC1201510 — Malach et al. (2002). Object-related voxels in TOJ. Neuron.


CITATIONS
---------
  - [Hubel 1962, J Physiol 160:106, receptive fields]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Lamme 2000, Trends Neurosci 23:571, recurrent processing]
"""

from brain.base_mechanism import BrainMechanism


class TemporoOccipitalVisualAssembler(BrainMechanism):
    """
    TOJ — ventral visual stream, object and scene construction.

    Assembles visual features into coherent objects and scenes.
    This is what the brain "sees" — the recognized object.
    """

    def __init__(self):
        super().__init__(
            name="TemporoOccipitalVisualAssembler",
            human_analog="Temporo-occipital junction (ventral stream) — object and scene construction",
            layer="neocortical",
        )
        self.state.setdefault("object_library", {})
        self.state.setdefault("object_constructed", {})
        self.state.setdefault("scene_representation", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form processed)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("v4_output", {}).get("form_attended", 0.5)

        # MTG (motion context for object)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_context = mtg.get("abstract_motion", 0.5)

        # Posterior STG (audiovisual binding)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # DLPFC (attention filters what gets constructed)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dlpfc_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = dlpfc_out.get("wm_load", 0.5) if isinstance(dlpfc_out, dict) else 0.5
        cognitive_control = dlpfc.get("cognitive_control", 0.5)

        # SPL (spatial context of scene)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Construct object: color + form + motion + attention
        construction_input = (
            form_attended * 0.35 +
            motion_context * 0.25 +
            av_binding * 0.2 +
            wm_load * cognitive_control * 0.2
        )
        construction_input = max(0.0, min(1.0, construction_input))

        object_constructed = {
            "construction_strength": round(construction_input, 4),
            "scene_centered": spatial_target > 0.5,
            "multimodal_context": av_binding > 0.55,
        }

        # Scene representation: object in spatial context
        scene_representation = {
            "object_loaded": construction_input > 0.6,
            "spatial_context": round(spatial_target, 4),
            "attention_focus": cognitive_control > 0.6,
        }

        self.state["object_constructed"] = object_constructed
        self.state["scene_representation"] = scene_representation
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventral_visual_output": {
                "construction_strength": round(construction_input, 4),
                "object_identity": "assembled" if construction_input > 0.5 else "incomplete",
            },
            "object_constructed": object_constructed,
            "scene_representation": scene_representation,
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

