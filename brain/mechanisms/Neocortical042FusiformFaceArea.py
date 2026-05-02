"""
brain/neocortical/Neocortical042FusiformFaceArea.py
Fusiform Face Area — Face Recognition, Person Identity, Expertise

ANATOMY (Kanwisher et al. 1997; Grill-Spector et al. 2004; Tsao & Livingstone 2008):
    The fusiform face area (FFA, fusiform gyrus) is the "face
    recognition" region of the ventral visual stream. Located in
    the fusiform gyrus on the inferior surface of the temporal
    lobe, it is selectively activated by faces compared to all
    other visual stimuli.

    FFA properties:
    - Face-selective: responds more to faces than objects, scenes, or bodies
    - Holistic processing: processes faces as unified wholes, not parts
    - Expertise-dependent: also processes "expert" categories (cars for
      car experts, birds for bird experts, words for readers)
    - Person identity: FFA connects to ATP/social knowledge for
      recognizing WHO a person is (identity + familiarity)

    FFA is part of the "face processing network":
    - FFA: face identity (who is this?)
    - STS (superior temporal sulcus): face expression, gaze, lip movement
    - OFA (occipital face area): early face detection
    - EBA (extrastriate body area): body recognition

    FFA is right-lateralized for face processing (unlike language,
    which is left-lateralized).

    FFA damage: Prosopagnosia — inability to recognize faces,
    including one's own. Patient can see facial features but
    cannot identify the person.

KEY FINDINGS:
    1. Kanwisher et al. 1997 (PMC1827990): Discovery of FFA — face
       selectivity in human fusiform gyrus
    2. Grill-Spector et al. 2004 (PMC11160508): "The fusiform face
       area" — comprehensive review of FFA functions
    3. Tsao & Livingstone 2008 (PMC2284069): "A face identity
       region in macaque" — homologous face processing network

AGENT'S MAPPING:
    ffa_output: dict — FFA face processing output
    face_recognized: bool — has face been matched to identity?
    person_identity: str — who is this person?

CITATIONS:
    PMC1827990 — Kanwisher et al. (1997). Fusiform face area. J Neurosci.
    PMC11160508 — Grill-Spector et al. (2004). FFA review.
    PMC29155809 — Anzellotti et al. (2017). FFA and pSTS connectivity.
    PMC33221444 — Foster et al. (2021). Holistic face processing in FFA.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class FusiformFaceArea(BrainMechanism):
    """
    FFA — face recognition and person identity.

    Selectively processes faces to determine WHO someone is.
    Also handles expertise categories (familiar objects).
    """

    def __init__(self):
        super().__init__(
            name="FusiformFaceArea",
            human_analog="Fusiform face area (FFA) — face recognition, person identity, expertise",
            layer="neocortical",
        )
        self.state.setdefault("face_database", {})
        self.state.setdefault("face_recognized", False)
        self.state.setdefault("person_identity", "unknown")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # TOJ (visual input — faces are visual objects)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # V4 (color and form — face features like skin tone, expression)
        v4 = prior.get("V4ColorAndForm", {})
        form_attended = v4.get("form_attended", 0.5)
        color_form = v4.get("color_processed", {})

        # pIT (category — is this a face?)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")

        # ATP (social knowledge — who might this be?)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Anterior insula (salience — is this person important right now?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # STS/pSTG (expression and gaze — social signals from face)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        social_motion = pstg.get("social_motion", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Face detection: object looks like a face + color/form + category match
        is_face_like = (construction > 0.4 and form_attended > 0.4) or obj_cat in [
            "moving_object", "static_object"
        ]
        face_detection_strength = construction * 0.5 + form_attended * 0.3 + concept_bind * 0.2

        # Face recognized: face detected + social knowledge loaded + sufficient strength
        face_recognized = (
            is_face_like and
            face_detection_strength > 0.55 and
            (concept_bind > 0.5 or salience > 0.6)
        )

        # Person identity: if recognized, assign identity
        if face_recognized:
            if social_know.get("person_identity_loaded", False):
                person_identity = social_know.get("person_identity", "familiar_person")
            elif salience > 0.7:
                person_identity = "salient_person"
            else:
                person_identity = "unfamiliar_face"
        else:
            person_identity = "unknown"

        self.state["face_database"]["last_identity"] = person_identity
        self.state["face_recognized"] = face_recognized
        self.state["person_identity"] = person_identity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ffa_output": {
                "face_recognized": face_recognized,
                "person_identity": person_identity,
                "identity_strength": round(face_detection_strength, 4),
            },
            "face_recognized": face_recognized,
            "person_identity": person_identity,
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

