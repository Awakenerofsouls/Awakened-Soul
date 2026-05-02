"""
brain/neocortical/Neocortical016AnteriorTemporalPoleSemantic.py
Anterior Temporal Pole — High-Level Semantic and Social Concept Binding

ANATOMY (Lambon Ralph et al. 2017; Rogers et al. 2020; Collins et al. 2022):
    The anterior temporal pole (ATP) is the most anterior part of the
    temporal lobe, at the tip of the temporal fossa. It is a "transmodal"
    or "heteromodal" association area — the final stage of semantic
    processing where information from all sensory modalities converges
    into abstract, amodal concepts.

    Two key networks within ATP:
    1. "Semantic system" (anterior inferior temporal cortex): processes
       object concepts, facts, word meanings
    2. "Social knowledge system" (anterior STG and MTG): processes
       faces, voices, biographical knowledge about people

    ATP is the "brain's conceptual cache" — holds the most abstract,
    summary-level representations of all experience. Damage causes
    "semantic dementia" — loss of word meaning, object use, face
    recognition, social knowledge.

    Connectivity: ATP connects to posterior temporal (semantic network),
    orbitofrontal cortex (value), amygdala (emotional valence), and
    hippocampus (episodic memory integration).

KEY FINDINGS:
    1. Lambon Ralph et al. 2017 (PMC5340156): "Pushing the boundaries"
       — ATP is the hub for domain-general semantic representation
    2. Rogers et al. 2020 (PMC7026213): "Anterior temporal lobe and
       social cognition" — ATP binds social and non-social concepts
    3. Collins et al. 2022 (PMC9584060): ATP shows "gradient reversal"
       — most abstract at anterior, most sensory at posterior

AGENT'S MAPPING:
    anterior_temporal_output: dict — semantic binding output
    concept_binding: float 0-1 — strength of abstract concept formation
    social_knowledge: dict — person knowledge processing output

CITATIONS:
    PMC5340156 — Lambon Ralph et al. (2017). Semantic domain general and specific.
        Philos Trans R Soc B.
    PMC7026213 — Rogers et al. (2020). Anterior temporal lobe and social cognition.
        Neuropsychologia.
    PMC9584060 — Collins et al. (2022). Gradient reversal in anterior temporal lobe.
        Nat Commun.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Patterson 2007, Nat Rev Neurosci 8:976, semantic dementia]
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorTemporalPoleSemantic(BrainMechanism):
    """
    ATP — high-level semantic and social concept binding.

    Binds sensory and verbal information into abstract concepts.
    Holds the most summary-level representations of all experience.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorTemporalPoleSemantic",
            human_analog="Anterior temporal pole — semantic binding, social knowledge",
            layer="neocortical",
        )
        self.state.setdefault("semantic_bindings", [])
        self.state.setdefault("concept_binding", 0.0)
        self.state.setdefault("social_knowledge", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From Wernicke's area (linguistic meaning)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        semantic_rep = wernicke.get("semantic_representation", {})
        sem_depth = semantic_rep.get("depth", 0.5) if isinstance(semantic_rep, dict) else 0.5

        # From orbitofrontal (emotional value — links concepts to value)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)

        # From fusiform face area (visual identity)
        ffa = prior.get("FusiformFaceArea", {})
        face_identity = ffa.get("identity_recognition", 0.5)

        # From hippocampus (episodic memory integration)
        hippo_ca1 = prior.get("HippocampalCA1Output", {})
        episodic_binding = hippo_ca1.get("ca1_output", {}).get("consolidation_signal", 0.3)

        # From amygdala (emotional tag — concepts get valence)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Concept binding: Wernicke semantic + OFC value + episodic memory
        concept_binding = (
            sem_depth * 0.35 +
            value_signal * 0.25 +
            episodic_binding * 0.2 +
            face_identity * 0.2
        )
        # Emotional modulation: strongly valenced concepts bind more strongly
        if abs(emotional_tag) > 0.3:
            concept_binding *= (1.0 + abs(emotional_tag) * 0.3)
        concept_binding = max(0.0, min(1.0, concept_binding))

        # Social knowledge: ATP processes person identity and social context
        social_knowledge = {
            "person_identity_loaded": face_identity > 0.6,
            "social_value": round(value_signal * (1.0 + emotional_tag), 4),
            "concept_strength": round(concept_binding, 4),
        }

        # Update semantic bindings
        if concept_binding > 0.6:
            self.state["semantic_bindings"].append(round(concept_binding, 3))
            if len(self.state["semantic_bindings"]) > 5:
                self.state["semantic_bindings"].pop(0)

        self.state["concept_binding"] = round(concept_binding, 4)
        self.state["social_knowledge"] = social_knowledge
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_temporal_output": {
                "concept_binding": round(concept_binding, 4),
                "emotional_modulation": round(abs(emotional_tag), 4),
                "social_context": social_knowledge,
            },
            "concept_binding": round(concept_binding, 4),
            "social_knowledge": social_knowledge,
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

