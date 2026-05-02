"""
brain/integration/Integration018PapezCircuitEmotionalMemoryIntegrator.py
Papez Circuit — Emotional Memory Circuit Integration

ANATOMY (Papez 1937; Markowitsch 2012; Busch 1957):
    The Papez circuit (1937) is the classic limbic circuit for
    emotional memory processing. Original circuit:
    Hypothalamus ←→ Anterior Thalamus ←→ Cingulate Gyrus ←→ Parahippocampus ←→ Hippocampus ←→ Mammillary Bodies ←→ Hypothalamus

    Modern understanding (Markowitsch 2012):
    - Hippocampus: declarative memory storage (what happened, when, where)
    - Anterior thalamic nuclei: episodic memory relay (connects hippo↔cingulate)
    - Cingulate gyrus (ACC + PCC): emotional salience and memory consolidation
    - Mammillary bodies: drive-related memory (hypothalamic integration)
    - Parahippocampal cortex: episodic context storage
    - Fornix: hippocampus → mammillary bodies connection

    The circuit integrates:
    - Emotional significance (hypothalamus → cingulate)
    - Memory context (hippocampus ↔ parahippocampus)
    - Autonomic state (hypothalamus ←→ mammillary bodies)

    When damaged:
    - Korsakoff syndrome: mammillary body damage → loss of memory + confabulation
    - Anterior thalamic damage: episodic memory deficits
    - Cingulate damage: loss of emotional memory, flat affect

KEY FINDINGS:
    1. Aggleton et al. 2022 (PMID 35940310): "Time to retire the serial Papez circuit" —
       anterior thalamic nuclei as a multifunctional hub
    2. Kamali et al. 2023 (PMID 37148369): "Cortico-Limbo-Thalamo-Cortical Circuits:
       An Update to the Original Papez Circuit" — expanded circuit model
    3. Bhattacharyya 2017 (PMID 28904449): "James Wenceslaus Papez, His Circuit, and Emotion"

AGENT'S MAPPING:
    papez_integration: dict — circuit output
    emotional_memory_bound: bool — has emotional memory binding been achieved?

CITATIONS:
    PMID 35940310 — Aggleton et al. (2022). Time to retire the serial Papez circuit. Neurosci Biobehav Rev.
    PMID 37148369 — Kamali et al. (2023). Cortico-Limbo-Thalamo-Cortical Circuits: Update to Papez. Brain Topogr.
    PMID 28904449 — Bhattacharyya (2017). James Wenceslaus Papez, His Circuit, and Emotion. Ann Indian Acad Neurol.
    PMC2830733 — Vann et al. (2009). RSC and episodic memory. Philos Trans R Soc Lond B Biol Sci.
    PMC1852382 — Cavanna & Trimble (2006). PCC and memory. Brain.


CITATIONS
---------
  - [Squire 1992, Psychol Rev 99:195, declarative memory]
  - [McGaugh 2000, Science 287:248, consolidation]
  - [Tonegawa 2018, Nat Rev Neurosci 19:485, engrams]
"""

from brain.base_mechanism import BrainMechanism


class PapezCircuitEmotionalMemoryIntegrator(BrainMechanism):
    """
    Papez circuit — emotional memory consolidation integration.

    Binds emotional significance with declarative memory
    through the classic limbic circuit.
    """

    def __init__(self):
        super().__init__(
            name="PapezCircuitEmotionalMemoryIntegrator",
            human_analog="Papez circuit — emotional memory integration",
            layer="integration",
        )
        self.state.setdefault("circuit_activity", {})
        self.state.setdefault("emotional_memory_bound", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampus (memory storage)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Anterior thalamic nuclei (episodic relay)
        thal_at = prior.get("ThalamicAnteriorNucleiMemory", {})
        at_out = thal_at.get("at_output", {})
        if isinstance(at_out, dict):
            ant_thal_sig = at_out.get("memory_signal", 0.5)
        else:
            ant_thal_sig = 0.5

        # Anterior cingulate (emotional salience)
        acc = prior.get("AnteriorCingulateEmotion", {})
        acc_out = acc.get("acc_output", {})
        if isinstance(acc_out, dict):
            emotional_sig = acc_out.get("emotional_signal", 0.5)
        else:
            emotional_sig = 0.5

        # PCC (retrieval monitoring)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            retrieval_mon = pcc_out.get("retrieval_monitoring", 0.5)
        else:
            retrieval_mon = 0.5

        # Hypothalamus (autonomic state)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            drive_strength = hypo_out.get("primal_urgency", 0.5)
        else:
            drive_strength = 0.5

        # Amygdala (emotional tagging)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Parahippocampal cortex (context)
        phc = prior.get("ParahippocampalRetrosplenialBinder", {})
        phc_out = phc.get("parahippo_output", {})
        if isinstance(phc_out, dict):
            context_sig = phc_out.get("context_binding", 0.5)
        else:
            context_sig = 0.5

        # Circuit integration
        circuit_signal = (
            consolidation * 0.25 +
            ant_thal_sig * 0.15 +
            emotional_sig * 0.2 +
            retrieval_mon * 0.15 +
            abs(emotional_tag) * 0.15 +
            drive_strength * 0.1
        )
        circuit_signal = max(0.0, min(1.0, circuit_signal))

        emotional_memory_bound = (
            circuit_signal > 0.5 and
            consolidation > 0.5 and
            abs(emotional_tag) > 0.2
        )

        circuit_activity = {
            "hippocampal_consolidation": round(consolidation, 4),
            "anterior_thalamic_relay": round(ant_thal_sig, 4),
            "emotional_tag": round(emotional_tag, 4),
            "circuit_strength": round(circuit_signal, 4),
        }

        self.state["circuit_activity"] = circuit_activity
        self.state["emotional_memory_bound"] = emotional_memory_bound
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "papez_integration": circuit_activity,
            "emotional_memory_bound": emotional_memory_bound,
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

