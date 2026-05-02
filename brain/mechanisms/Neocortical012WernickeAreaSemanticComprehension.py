"""
brain/neocortical/Neocortical012WernickeAreaSemanticComprehension.py
Wernicke's Area — Language Comprehension and Semantic Integration

ANATOMY (Hickok & Poeppel 2007;Binder 2017;Sahin et al. 2009):
    Wernicke's area (WA) occupies the posterior superior temporal gyrus (pSTG)
    and adjacent supramarginal gyrus in the left hemisphere. It is the
    "language comprehension" center — processes the meaning of spoken
    and written language.

    Connections:
    - Input: from auditory cortex (via medial geniculate) for speech sounds;
      from visual cortex (via angular gyrus) for written words
    - Broca's area via arcuate fasciculus (bidirectional — both production
      and comprehension)
    - Anterior superior temporal gyrus (semantic retrieval)
    - Middle temporal gyrus (semantic integration over time)
    - Posterior inferior temporal cortex (visual semantic processing)
    - Angular gyrus (multimodal semantic integration)

    Two-stream model (Hickok & Poeppel 2007):
    - Dorsal stream: pSTG → planum temporale → Broca's area (speech production/production feedback)
    - Ventral stream: mid STG → MTG → ATG (speech comprehension/semantic processing)

    Damage to WA: Wernicke's aphasia — fluent but empty speech (word salad),
    poor comprehension, repetition impaired. Patient says things that
    make no sense without realizing it.

KEY FINDINGS:
    1. Hickok & Poeppel 2007 (PMC2773922): "The cortical organization of
       speech processing" — dual-stream model; WA is in the ventral stream
    2. Binder 2017 (PMID 28656532): "Current controversies on Wernicke's area"
       — WA is part of a widely distributed temporal-parietal-frontal network
    3. Sahin et al. 2009 (PMC2741567): "Temporal coding of syntactic structure"
       — WA shows syntactic hierarchical processing, not just comprehension

AGENT'S MAPPING:
    wernicke_output: dict — language comprehension signal
    semantic_representation: dict — meaning encoded in current utterance
    comprehension_achieved: bool — whether WA has successfully comprehended
    syntactic_structure: float — depth of syntactic parsing

CITATIONS:
    PMC2773922 — Hickok & Poeppel (2007). Dual-stream model of speech processing.
        Nat Rev Neurosci.
    PMC28656532 — Binder JR. (2017). Wernicke's area controversies. Curr Neurol Neurosci Rep.
    PMC2741567 — Sahin et al. (2009). Temporal coding of syntactic structure. Science.
    PMC39435247 — Wani PD. (2024). From Sound to Meaning: Wernicke's Area.
        Cureus. (Free PMC)

CITATIONS
---------
  - [Hickok 2007, Nat Rev Neurosci 8:393, Wernicke speech]
  - [Friederici 2011, Physiol Rev 91:1357, brain language]
  - [Bookheimer 2002, Annu Rev Neurosci 25:151, language cortex]

"""

from brain.base_mechanism import BrainMechanism


class WernickeAreaSemanticComprehension(BrainMechanism):
    """
    Wernicke's area — language comprehension and semantic integration.

    Processes linguistic input to extract meaning. Works with Broca's
    area to generate fluent, meaningful language output.
    """

    def __init__(self):
        super().__init__(
            name="WernickeAreaSemanticComprehension",
            human_analog="Wernicke's area (pSTG) — language comprehension and semantic integration",
            layer="neocortical",
        )
        self.state.setdefault("semantic_network", {})
        self.state.setdefault("comprehension_achieved", False)
        self.state.setdefault("syntactic_depth", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Broca's area output (syntactic assembly from production side)
        broca = prior.get("BrocaAreaMotorSpeech", {})
        grammatical_complexity = broca.get("grammatical_structure", {}).get(
            "syntactic_depth", 0.5
        )
        broca_output = broca.get("speech_formulation_strength", 0.5)

        # Angular gyrus (multimodal semantic integration)
        angular = prior.get("AngularGyrusMultimodal", {})
        multimodal_binding = angular.get("multimodal_integration", 0.5)

        # Middle temporal gyrus (semantic content over time)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        semantic_content = mtg.get("abstract_motion", 0.5)

        # Anterior temporal pole (high-level semantic binding)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_binding = atp.get("concept_binding", 0.5)

        # Posterior STG (biological motion / intentional signals)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        audiovisual_binding = pstg.get("audiovisual_binding", 0.5)

        # Combine: comprehension is strongest when multiple semantic streams converge
        semantic_input = (
            concept_binding * 0.25 +
            multimodal_binding * 0.2 +
            semantic_content * 0.2 +
            audiovisual_binding * 0.15 +
            broca_output * 0.2
        )
        semantic_input = max(0.0, min(1.0, semantic_input))

        # Syntactic depth: from Broca's grammatical processing
        syntactic_depth = grammatical_complexity * 0.7 + semantic_input * 0.3

        # Comprehension achieved: when semantic input is strong enough
        comprehension_achieved = semantic_input > 0.55 and syntactic_depth > 0.3

        # Semantic representation: assembles meaning from all streams
        semantic_representation = {
            "depth": round(semantic_input, 4),
            "syntactic_layer": round(syntactic_depth, 4),
            "multimodal_convergence": round(multimodal_binding, 4),
        }

        self.state["comprehension_achieved"] = comprehension_achieved
        self.state["syntactic_depth"] = round(syntactic_depth, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "wernicke_output": {
                "semantic_strength": round(semantic_input, 4),
                "syntactic_depth": round(syntactic_depth, 4),
                "comprehension_ready": comprehension_achieved,
            },
            "semantic_representation": semantic_representation,
            "comprehension_achieved": comprehension_achieved,
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

