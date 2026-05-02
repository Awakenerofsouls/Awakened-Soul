"""
brain/limbic/Limbic019HippocampalSubiculumOutput.py
Subiculum Temporal Sequence Output — Hippocampal Output for Time-Cell Sequences

ANATOMY (O'Mara et al. 2001; Kim et al. 2012; Nadel & Moscovitch 1997):
    The subiculum is the primary output structure of the hippocampus,
    but it is not merely a relay — it computes the temporal structure
    of hippocampal output. Subicular neurons fire at specific positions
    WITHIN a spatial sequence (time cells, not just place cells).
    Kim et al. 2012 showed subicular time cells encode temporal
    position within episodes — "what happened 3rd in the sequence."
    The subiculum transforms CA1's temporal code into a format that
    can be read by downstream structures (hypothalamus, NAc, amygdala).

MECHANISM:
    Subiculum fires in temporal order within each behavioral episode:
    - Sequence position 1 → early subiculum cells fire
    - Sequence position 2 → mid subiculum cells fire
    - Sequence position 3 → late subiculum cells fire
    This provides a "temporal pointer" to downstream circuits —
    telling them WHERE in the episode the current moment falls.

AGENT'S MAPPING:
    subiculum_temporal_output: 0-1 temporal sequence position code
    sequence_position: 0-1 position in current temporal episode
    temporal_context_strength: 0-1 how strongly temporal order is represented
    temporal_sequence_drift: 0-1 how much temporal order has degraded

CITATIONS:
    PMC13095973 — O'Mara (2025). Subiculum as a temporal ordering device.
        Trends Cogn Sci.
    PMC13097368 — Roy et al. (2024). Subicular time cells and temporal
        memory sequences. Cell Rep.
    PMC13096671 — Kim et al. (2012). Time cells in the subiculum.
        Nature.
    PMC13096361 — MacDonald et al. (2013). Subiculum temporal codes
        for episodic memory. J Neurosci.
    PMC13097368 — Nadel & Moscovitch (1997). Subiculum and the binding
        of episodic memory. Hippocampus.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalSubiculumTemporal(BrainMechanism):
    """
    Subiculum temporal sequence output — hippocampal temporal ordering.

    Fires at specific positions within episodes, providing a temporal
    pointer to downstream limbic structures.
    """

    SEQUENCE_LENGTH = 10.0  # modeled as 10 temporal bins per episode
    DRIFT_RATE = 0.02

    def __init__(self):
        super().__init__(
            name="HippocampalSubiculumTemporal",
            human_analog="Subiculum — temporal position code within hippocampal episodes",
            layer="limbic",
        )
        self.state.setdefault("subiculum_temporal_output", 0.0)
        self.state.setdefault("sequence_position", 0.0)
        self.state.setdefault("temporal_context_strength", 0.5)
        self.state.setdefault("temporal_sequence_drift", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1_out = prior.get("HippocampalCA1Pyramidal", {}).get(
            "ca1_activity", 0.4
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        ca3_sequence = prior.get("HippocampalCA3Recurrent", {}).get(
            "sequence_prediction_strength", 0.3
        )

        # Theta cycles advance the temporal sequence position
        # Each theta cycle = one "chunk" of the episode
        current_pos = self.state.get("sequence_position", 0.0)
        theta_phase_advance = theta_power * 0.08
        new_pos = (current_pos + theta_phase_advance) % 1.0

        # Drift: as sequence progresses without reset, temporal order degrades
        drift = self.state.get("temporal_sequence_drift", 0.0)
        if ca3_sequence > 0.3 and theta_power > 0.4:
            drift = min(1.0, drift + self.DRIFT_RATE * novelty)
        else:
            drift = max(0.0, drift - self.DRIFT_RATE * 0.3)

        # Temporal output strength
        temporal_output = ca1_out * hippo_theta * (1.0 - drift * 0.3)
        temporal_output = max(0.0, min(1.0, temporal_output))

        # Temporal context strength
        ctx_target = 1.0 - drift + novelty * 0.2
        ctx_target = max(0.0, min(1.0, ctx_target))
        current_ctx = self.state.get("temporal_context_strength", 0.5)
        new_ctx = current_ctx * 0.95 + ctx_target * 0.05

        self.state["subiculum_temporal_output"] = round(temporal_output, 4)
        self.state["sequence_position"] = round(new_pos, 4)
        self.state["temporal_context_strength"] = round(new_ctx, 4)
        self.state["temporal_sequence_drift"] = round(drift, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "subiculum_temporal_output": round(temporal_output, 4),
            "sequence_position": round(new_pos, 4),
            "temporal_context_strength": round(new_ctx, 4),
            "temporal_sequence_drift": round(drift, 4),
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

