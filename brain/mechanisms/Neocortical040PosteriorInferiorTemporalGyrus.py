"""
brain/neocortical/Neocortical040PosteriorInferiorTemporalGyrus.py
Posterior Inferior Temporal Gyrus — Object Category Processing, Advanced Recognition

ANATOMY (Kravitz et al. 2013; Grill-Spector & Weiner 2014; Connolly et al. 2012):
    The posterior inferior temporal gyrus (pIT/IT) is the "category
    hub" of the ventral visual stream — the final stage before
    anterior IT where visual objects are categorized.

    pIT has multiple category-selective regions:
    - pIT: general object recognition (complex objects)
    - FFA: face recognition (see FFA mechanism)
    - PPA: place/.scene recognition (parahippocampal)
    - EBA: extrastriate body area (bodies)
    - pSTS: biological motion

    pIT computes "what category?" — taking the output of V4
    (color+form) and matching it against stored object categories.

    Key properties:
    - View-invariant: recognizes the same object from different viewing angles
    - Size-invariant: recognizes the same object at different sizes
    - Position-invariant: recognizes the same object at different positions
    - Illumination-invariant: recognizes objects across lighting conditions

    pIT is where visual object recognition becomes "semantic" — it's
    the transition from visual processing to semantic meaning.

KEY FINDINGS:
    1. Grill-Spector & Weiner 2014 (PMC4326522): "The functional
       organization of the human ventral visual pathway"
    2. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream" —
       ventral stream object processing through pIT
    3. Connolly et al. 2012 (PMC3378930): pIT category processing
       for objects, faces, scenes

AGENT'S MAPPING:
    pitg_output: dict — pIT object category output
    object_category: str — the recognized category
    categorization_confidence: float 0-1 — how certain is the categorization

CITATIONS:
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC3378930 — Price (2012). Anatomy of language and object processing.
    PMC3000199 — Larsson (2010). Visual coding in V1/V2/V4.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Patterson 2007, Nat Rev Neurosci 8:976, semantic dementia]
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorInferiorTemporalGyrus(BrainMechanism):
    """
    pIT — advanced visual object recognition and categorization.

    Takes processed visual features and assigns them to
    object categories, enabling "what is this?" recognition.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorInferiorTemporalGyrus",
            human_analog="Posterior inferior temporal gyrus — object category processing, advanced recognition",
            layer="neocortical",
        )
        self.state.setdefault("category_hierarchy", {})
        self.state.setdefault("object_category", "unclassified")
        self.state.setdefault("categorization_confidence", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # TOJ (assembled object from ventral stream)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # MTG (motion context — does the object move?)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # DLPFC (attention — what are we looking for?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # Angular gyrus (semantic context — what could this be?)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Anterior insula (salience — does this object matter?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Categorization: object constructed + form attended + semantic binding
        cat_input = (
            construction * 0.3 +
            form_attended * 0.3 +
            sem_bind * 0.2 +
            cognitive_ctrl * 0.1 +
            salience * 0.1
        )
        cat_input = max(0.0, min(1.0, cat_input))

        # Confidence: higher when multiple sources agree
        confidence_sources = sum([
            construction > 0.5,
            form_attended > 0.5,
            sem_bind > 0.5,
            cognitive_ctrl > 0.5,
        ])
        categorization_confidence = min(1.0, (cat_input * 0.5 + confidence_sources * 0.125))

        # Object category (simplified)
        if construction > 0.6:
            if abstract_motion > 0.6:
                object_category = "moving_object"
            elif form_attended > 0.65:
                object_category = "static_object"
            else:
                object_category = "generic_object"
        else:
            object_category = "unclassified"

        self.state["object_category"] = object_category
        self.state["categorization_confidence"] = round(categorization_confidence, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pitg_output": {
                "object_category": object_category,
                "categorization_confidence": round(categorization_confidence, 4),
            },
            "object_category": object_category,
            "categorization_confidence": round(categorization_confidence, 4),
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

