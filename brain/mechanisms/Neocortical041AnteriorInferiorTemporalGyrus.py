"""
brain/neocortical/Neocortical041AnteriorInferiorTemporalGyrus.py
Anterior Inferior Temporal Gyrus — View-Invariant Object Identity, Abstract Object

ANATOMY (Kravitz et al. 2013; Konen & Kastner 2008; DiCarlo et al. 2012):
    The anterior inferior temporal gyrus (aIT) is the "view-invariant
    identity" region — it recognizes objects regardless of how they're
    seen. While pIT is sensitive to specific views, aIT has developed
    view-invariant representations.

    aIT is at the end of the ventral visual stream:
    V1 → V2 → V4 → pIT → aIT → ATP (semantic binding)

    Key properties:
    - View-invariant: same object from any angle = same representation
    - Size-tolerant: recognizes objects across size scales
    - Illumination-tolerant: robust across lighting conditions
    - Category-spanning: aIT neurons respond to the same concept
      across modalities (e.g., image of a cup AND word "cup")

    aIT is close to ATP (anterior temporal pole) — the transition
    from visual object identity to semantic meaning ("what is this
    and what does it mean?").

    aIT damage: "Agnosia" — patient can see objects but can't
    recognize what they are (can't name them or know their use).

KEY FINDINGS:
    1. DiCarlo et al. 2012 (PMC3361260): "How does the brain
       solve the visual object recognition problem?" — aIT as
       the endpoint of the ventral stream
    2. Konen & Kastner 2008: Two streams for object recognition in IT
    3. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream"
       — aIT as the ventral stream endpoint

AGENT'S MAPPING:
    aitg_output: dict — aIT identity output
    view_invariant_identity: str — object identity independent of view
    abstract_object: dict — abstract representation of the object

CITATIONS:
    PMC3361260 — DiCarlo et al. (2012). Visual object recognition. Nat Neurosci.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Patterson 2007, Nat Rev Neurosci 8:976, semantic dementia]
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInferiorTemporalGyrus(BrainMechanism):
    """
    aIT — view-invariant object recognition and abstract identity.

    Recognizes objects from any viewing angle and begins the
    transition from visual processing to semantic meaning.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInferiorTemporalGyrus",
            human_analog="Anterior inferior temporal gyrus — view-invariant identity, abstract object",
            layer="neocortical",
        )
        self.state.setdefault("identity_cache", {})
        self.state.setdefault("view_invariant_identity", "unknown")
        self.state.setdefault("abstract_object", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # pIT (category-level object from ventral stream)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")
        cat_conf = pit.get("categorization_confidence", 0.5)

        # V4 (color and form — identity cues)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # ATP (semantic binding — links identity to meaning)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Angular gyrus (multimodal semantic — helps abstract identity)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Fusiform (face identity — special object category)
        ffa = prior.get("FusiformFaceArea", {})
        face_recognized = ffa.get("face_recognized", False)
        person_id = ffa.get("ffa_output", {}).get("person_identity", "unknown") if isinstance(
            ffa.get("ffa_output"), dict) else "unknown"

        # View-invariant identity: category + semantic + form
        identity_strength = cat_conf * 0.4 + concept_bind * 0.3 + form_attended * 0.3

        if identity_strength > 0.6:
            if face_recognized:
                view_invariant_identity = person_id
            elif obj_cat != "unclassified":
                view_invariant_identity = f"object_{obj_cat}"
            else:
                view_invariant_identity = "generic_identity"
        else:
            view_invariant_identity = "unknown"

        # Abstract object: the object representation minus visual details
        abstract_object = {
            "identity": view_invariant_identity,
            "identity_strength": round(identity_strength, 4),
            "category_origin": obj_cat,
            "semantic_bound": concept_bind > 0.6,
        }

        self.state["view_invariant_identity"] = view_invariant_identity
        self.state["abstract_object"] = abstract_object
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "aitg_output": {
                "view_invariant": view_invariant_identity,
                "identity_strength": round(identity_strength, 4),
            },
            "view_invariant_identity": view_invariant_identity,
            "abstract_object": abstract_object,
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

