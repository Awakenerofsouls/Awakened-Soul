"""
Build 53: Foundational053MammillaryBodyOutput — Mammillary Body Memory/Eye Movement Relay
================================================================================

PLACEMENT:
  Layer:    foundational (diencephalon — mammillary bodies, body of Forel)
  Filename: brain/foundational/Foundational053MammillaryBodyOutput.py
  Instance name: MammillaryBodyOutput

NEURAL SUBSTRATE:
  Mammillary bodies (MB) — the output node of the hippocampal formation.
  Receives the hippocampal fimbria/fornix and projects to anterior
  thalamic nucleus (ANT) via the mammillothalamic tract (MTT).

  CIRCUIT: Subiculum → fimbria → mammillary bodies → ANT → cingulate cortex → entorhinal

  This circuit is critical for:
  - Spatial memory (Papez circuit)
  - Episodic memory consolidation
  - Head direction cell processing
  - Mammillary bodies contain head direction cells

  MB also receives input from tegmental nuclei (raphe, locus coeruleus)
  and projects to the ventral tegmental area.

  Human analog: Korsakoff syndrome (mammillary body damage → anterograde amnesia),
  spatial memory, head direction system.

Output keys:
  hippocampal_consolidation_pathway: float [0.0–1.0] — Papez circuit activity
  head_direction_signal: float [0.0–1.0] — head direction cell activity
  mammillary_body_tone: float [0.0–1.0] — overall MB activity
  memory_consolidation_strength: float [0.0–1.0] — consolidation drive
  mammillary_integrator: float [0.0–1.0] — composite MB output

CITATIONS:
    PMC8137464 — Dillingham CM, Milczarek MM, Perry JC et al. (2021). Time to Put
        the Mammillothalamic Pathway Into Context. Neurosci Biobehav Rev.
    PMC3691571 — Vann SD (2013). Dismantling the Papez Circuit for Memory in Rats.
        Trends Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodyOutput(BrainMechanism):
    """
    Mammillary bodies: Papez circuit output, head direction, spatial memory.

    Models the mammillary bodies as hippocampal memory consolidation output
    and head direction signal integrator.
    """

    STATE_FIELDS = [
        "hippocampal_consolidation_pathway", "head_direction_signal",
        "mammillary_body_tone", "memory_consolidation_strength",
        "mammillary_integrator", "tick_count",
    ]

    CONSOLIDATION_GAIN = 0.55
    HEAD_DIRECTION_GAIN = 0.50

    def __init__(self, name: str = "MammillaryBodyOutput",
                 human_analog: str = "Mammillary bodies — Papez circuit output",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["hippocampal_consolidation_pathway"] = 0.40
        self.state["head_direction_signal"] = 0.30
        self.state["mammillary_body_tone"] = 0.40
        self.state["memory_consolidation_strength"] = 0.30
        self.state["mammillary_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        hippocampal = prior.get("HippocampalReplayIntegrator", {}).get("replay_strength", 0.30)
        subicular = prior.get("HippocampalSubiculumOutput", {}).get("subicular_output", 0.30)
        theta = prior.get("HippocampalReplayIntegrator", {}).get("theta_power", 0.30)
        cingulate = prior.get("AnteriorCingulateConflict", {}).get("conflict_signal", 0.0)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        reward = prior.get("VentralStriatumOutput", {}).get("reward_signal", 0.0)

        # Hippocampal consolidation pathway: Papez circuit drive
        consolidation = hippocampal * self.CONSOLIDATION_GAIN
        consolidation += subicular * 0.30
        # Theta rhythm facilitates Papez consolidation
        consolidation += theta * 0.20
        hippocampal_consolidation_pathway = min(1.0, consolidation)

        # Head direction signal: vestibular + hippocampal place cells
        head_direction = abs(vestibular - 0.5) * self.HEAD_DIRECTION_GAIN
        head_direction += theta * 0.20
        head_direction_signal = min(1.0, head_direction)

        # Mammillary body tone: overall activity
        mammillary_body_tone = (hippocampal * 0.40) + (head_direction * 0.30) + 0.30
        mammillary_body_tone = min(1.0, mammillary_body_tone)

        # Memory consolidation strength
        memory_consolidation = hippocampal_consolidation_pathway * 0.60
        memory_consolidation += reward * 0.20  # reward enhances consolidation
        memory_consolidation_strength = min(1.0, memory_consolidation)

        # Mammillary integrator
        mammillary_integrator = (mammillary_body_tone + memory_consolidation) / 2.0

        # --- Persist ---
        self.state["hippocampal_consolidation_pathway"] = round(hippocampal_consolidation_pathway, 4)
        self.state["head_direction_signal"] = round(head_direction_signal, 4)
        self.state["mammillary_body_tone"] = round(mammillary_body_tone, 4)
        self.state["memory_consolidation_strength"] = round(memory_consolidation, 4)
        self.state["mammillary_integrator"] = round(mammillary_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hippocampal_consolidation_pathway": round(hippocampal_consolidation_pathway, 4),
            "head_direction_signal": round(head_direction_signal, 4),
            "mammillary_body_tone": round(mammillary_body_tone, 4),
            "memory_consolidation_strength": round(memory_consolidation, 4),
            "mammillary_integrator": round(mammillary_integrator, 4),
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

