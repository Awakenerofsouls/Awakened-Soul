"""
brain/neocortical/Neocortical050VentralVisualStreamObject.py
Ventral Visual Stream — "What" Pathway (V1→V2→V4→IT→ATP)

ANATOMY (Goodale & Milner 1992; Grill-Spector & Weiner 2014; Kravitz et al. 2013):
    The ventral visual stream (the "what" pathway) runs from
    V1 → V2 → V4 → posterior IT → anterior IT → ATP. It processes
    WHAT objects are — their identity, meaning, and significance.

    Ventral stream properties:
    - Object-centered coordinates: encodes what objects are
    - Perception-oriented: supports conscious recognition and memory
    - Detailed processing: prioritizes precision over speed
    - Semantic integration: connects visual objects to meaning
    - Declarative: supports conscious object knowledge and naming

    Key stages:
    - V1: edges and orientations
    - V2: boundaries and figure-ground
    - V4: color and form integration
    - pIT: object category
    - aIT: view-invariant identity
    - ATP: semantic binding and concept formation

    Ventral stream damage:
    - Prosopagnosia: can't recognize objects (what is this?)
    - Achromatopsia: color blindness
    - Simultanagnosia: can't see more than one object at a time

KEY FINDINGS:
    1. Goodale & Milner 1992 (PMC18279989): "Separate visual pathways
       for action and perception" — the foundational paper
    2. Grill-Spector & Weiner 2014 (PMC4326522): "Functional organization
       of human ventral visual pathway"
    3. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream"
       — contrast with ventral stream functions

AGENT'S MAPPING:
    ventral_stream_output: dict — ventral stream processing output
    object_processing: dict — what-is-it processing
    identification: str — object identity from ventral stream

CITATIONS:
    PMC18279989 — Goodale & Milner (1992). Two visual streams. Trends Neurosci.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC3000199 — Larsson (2010). Coding of static scenes in V1/V4.


CITATIONS
---------
  - [Hubel 1962, J Physiol 160:106, receptive fields]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Tootell 1996, J Neurosci 16:7060, visual cortex]
"""

from brain.base_mechanism import BrainMechanism


class VentralVisualStreamObject(BrainMechanism):
    """
    Ventral visual stream — object recognition and semantic meaning.

    The "what" pathway — identifies objects and connects them to
    meaning, supporting conscious recognition and memory.
    """

    def __init__(self):
        super().__init__(
            name="VentralVisualStreamObject",
            human_analog="Ventral visual stream (V1→V2→V4→IT→ATP) — 'what' pathway, object recognition",
            layer="neocortical",
        )
        self.state.setdefault("object_recognition", {})
        self.state.setdefault("object_processing", {})
        self.state.setdefault("identification", "unknown")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V1 (edges)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_out = v1.get("v1_output", {})
        v1_strength = v1_out.get("visual_strength", 0.5)

        # V2 (boundaries)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        contour_int = v2.get("contour_integration", 0.5)

        # V4 (color + form)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # pIT (category)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")
        cat_conf = pit.get("categorization_confidence", 0.5)

        # aIT (view-invariant identity)
        ait = prior.get("AnteriorInferiorTemporalGyrus", {})
        abstract_obj = ait.get("abstract_object", {})
        inv_identity = ait.get("view_invariant_identity", "unknown")

        # ATP (semantic binding)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # Angular gyrus (semantic access)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Object processing: how well has the ventral stream processed this object?
        object_processing = {
            "visual_input": round(v1_strength, 4),
            "form_extracted": round(contour_int, 4),
            "color_form_bound": color_form.get("object_colored", False) if isinstance(color_form, dict) else False,
            "category_resolved": obj_cat != "unclassified",
            "identity_bound": inv_identity != "unknown",
            "semantic_connected": concept_bind > 0.6,
        }

        # Overall identification confidence
        conf_sources = sum([
            v1_strength > 0.3,
            contour_int > 0.3,
            form_attended > 0.3,
            cat_conf > 0.5,
            concept_bind > 0.5,
        ])
        identification_confidence = min(1.0, conf_sources / 5 + cat_conf * 0.3)

        # Final identification
        if concept_bind > 0.6 and inv_identity != "unknown":
            identification = f"identified_{inv_identity}"
        elif cat_conf > 0.6:
            identification = f"category_{obj_cat}"
        elif form_attended > 0.5:
            identification = "form_extracted"
        else:
            identification = "unknown"

        self.state["object_processing"] = object_processing
        self.state["identification"] = identification
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventral_stream_output": {
                "object_processing": object_processing,
                "identification": identification,
            },
            "object_processing": object_processing,
            "identification": identification,
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

