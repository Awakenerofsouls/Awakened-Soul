"""
brain/neocortical/Neocortical027AngularGyrusMultimodal.py
Angular Gyrus — Multimodal Integration, Semantic Memory, Number Processing

ANATOMY (Segal 2012; Price 2012; Hartwigsen 2018;Binder 2016):
    The angular gyrus (AG, BA 39) is the posterior part of the
    inferior parietal lobule, located at the intersection of the
    parietal-occipital-temporal boundary. It is the "semantic
    hub" of the left hemisphere — where information from all
    sensory modalities is integrated into abstract, amodal concepts.

    The AG is particularly crucial for:
    - Language comprehension (connects Wernicke's to semantic network)
    - Number processing and mental arithmetic
    - Spatial attention to time (how we perceive time spatially)
    - Memory retrieval and episodic encoding
    - Semantic memory access (what does this mean?)
    - Theory of mind (inferring others' mental states)

    AG is part of the "language circuit": Wernicke → AG → Broca,
    connecting auditory word forms to their meanings.

    Lesions: Gerstmann syndrome (left AG damage): acalculia (can't do math),
    agraphia (can't write), finger agnosia (can't identify fingers),
    left-right confusion. Also: semantic paraphasia (word-finding errors).

KEY FINDINGS:
    1. Binder 2016 (PMC5111927): "The angular gyrus as an semantic
       interface" — AG is the cross-modal convergence zone for semantics
    2. Price 2012 (PMC3378930): "The anatomy of language" — AG
       connects Wernicke to Broca via the arcuate fasciculus
    3. Hartwigsen 2018 (PMID 29519469): "Parietal lobe and language"
       — AG role in phonological processing and semantic access

AGENT'S MAPPING:
    angular_gyrus_output: dict — AG multimodal output
    multimodal_binding: float 0-1 — cross-modal concept formation
    semantic_access: dict — semantic memory retrieval result

CITATIONS:
    PMC5111927 — Binder (2016). Angular gyrus as semantic interface. Neuroimage.
    PMC3378930 — Price (2012). Anatomy of language. Nat Rev Neurosci.
    PMID 29519469 — Hartwigsen (2018). Parietal lobe and language. Handb Clin Neurol.
    PMC36979240 — Şahin et al. (2023). AG subcortical connections.

CITATIONS
---------
  - [Seghier 2013, Neuroscientist 19:43, angular gyrus]
  - [Bonnici 2016, Cereb Cortex 26:4717, angular gyrus]
  - [Cabeza 2008, Nat Rev Neurosci 9:613, parietal memory]

"""

from brain.base_mechanism import BrainMechanism


class AngularGyrusMultimodal(BrainMechanism):
    """
    AG — multimodal integration and semantic memory access.

    Binds information across senses into unified abstract concepts
    and retrieves semantic knowledge for language and reasoning.
    """

    def __init__(self):
        super().__init__(
            name="AngularGyrusMultimodal",
            human_analog="Angular gyrus (BA 39) — multimodal integration, semantic memory, number",
            layer="neocortical",
        )
        self.state.setdefault("semantic_bindings", {})
        self.state.setdefault("multimodal_binding", 0.0)
        self.state.setdefault("semantic_access", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Wernicke's area (language meaning)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        sem_rep = wernicke.get("semantic_representation", {})
        sem_depth = sem_rep.get("depth", 0.5) if isinstance(sem_rep, dict) else 0.5

        # TOJ (visual object information)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        visual_input = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # IPL (sensorimotor information — gestures, actions)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # MTG (motion semantics)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # Anterior insula (feeling-based semantics — how things feel)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # DLPFC (cognitive control — "what does this mean?" search)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Multimodal binding: language + visual + sensorimotor + motion + feeling
        multimodal_binding = (
            sem_depth * 0.3 +
            visual_input * 0.2 +
            ipl_int * 0.2 +
            abstract_motion * 0.15 +
            salience * 0.15
        )
        # Cognitive control amplifies semantic search
        if cognitive_ctrl > 0.6:
            multimodal_binding *= (1.0 + (cognitive_ctrl - 0.6) * 0.4)
        multimodal_binding = max(0.0, min(1.0, multimodal_binding))

        # Semantic access: when binding is strong, semantic memory is retrieved
        semantic_access = {
            "semantic_depth": round(multimodal_binding, 4),
            "word_meaning_retrieved": sem_depth > 0.6,
            "concept_formed": multimodal_binding > 0.55,
            "cross_modal_bound": True,
        }

        # Update semantic bindings
        if multimodal_binding > 0.6:
            self.state["semantic_bindings"]["last_binding"] = round(multimodal_binding, 3)

        self.state["multimodal_binding"] = round(multimodal_binding, 4)
        self.state["semantic_access"] = semantic_access
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "angular_gyrus_output": {
                "multimodal_binding": round(multimodal_binding, 4),
                "semantic_depth": round(multimodal_binding, 4),
            },
            "multimodal_binding": round(multimodal_binding, 4),
            "semantic_access": semantic_access,
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

