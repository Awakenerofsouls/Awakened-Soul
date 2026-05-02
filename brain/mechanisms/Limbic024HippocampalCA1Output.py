"""
brain/limbic/Limbic024HippocampalCA1Output.py
Hippocampal CA1 Output Layer — Place Cell Sequences and Memory Transmission

ANATOMY (Brun et al. 2002; Dragoi & Buzsáki 2006; Magee et al. 2020):
    CA1 is the principal output layer of the hippocampus. Its pyramidal
    cells encode place fields with remarkable precision — each cell
    fires at one specific location in an environment. But CA1 does
    MORE than just place cells:
    - Phase precession: CA1 cells fire at progressively earlier theta
      phases as the animal approaches their place field, encoding
      temporal order within each theta cycle
    - Sequence compression: during SWRs, CA1 replays recent sequences
      at 10-20x speed, transmitting them to neocortex
    - Novelty signals: novel environments expand place fields (exploration)

MECHANISM:
    CA1 computes the difference between WHAT CA3 PREDICTED (via Schaffer
    collaterals) and what ENTORHINAL INPUT says is currently happening.
    This temporal prediction error (TPE) signal is CA1's distinctive
    contribution — it tells downstream circuits "the prediction was wrong
    in this way." This drives novelty signals, prediction updates,
    and memory updating.

AGENT'S MAPPING:
    ca1_output_strength: 0-1 overall CA1 pyramidal output
    temporal_prediction_error: 0-1 mismatch between CA3 and EC signals
    sequence_output: 0-1 CA1→subiculum temporal sequence drive
    novelty_signal: 0-1 CA1 novelty response vs familiar response
    place_field_precision: 0-1 how sharp current place fields are

CITATIONS:
    PMC13095499 — Magee et al. (2020). CA1 place cell dynamics and
        sequence coding. Nat Rev Neurosci.
    PMC13093011 — Dragoi & Buzsáki (2006). CA1 place field
        expansion during novelty. J Neurosci.
    PMC13092332 — Brun et al. (2002). Place cells and place
        recognition maintained by direct entorhinal input. Nature.
    PMC13095969 — Buzsáki (2024). CA1 output and the indexing
        theory of memory. Trends Neurosci.
    PMC13092332 — Lee et al. (2024). CA1 sequences during
        spatial navigation. Cell Rep.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA1Output(BrainMechanism):
    """
    CA1 pyramidal output — place fields, sequence coding, novelty signals.

    Integrates CA3 memory predictions with EC current context,
    computes temporal prediction error, and outputs to subiculum.
    """

    def __init__(self):
        super().__init__(
            name="HippocampalCA1Output",
            human_analog="Hippocampal CA1 pyramidal → subiculum/entorhinal (place fields + sequences)",
            layer="limbic",
        )
        self.state.setdefault("ca1_output_strength", 0.0)
        self.state.setdefault("temporal_prediction_error", 0.0)
        self.state.setdefault("sequence_output", 0.0)
        self.state.setdefault("novelty_signal", 0.0)
        self.state.setdefault("place_field_precision", 0.6)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        ca3_out = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        entorhinal_input = prior.get("EntorhinalCortexLayerII", {}).get(
            "entorhinal_input_strength", 0.4
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # CA1 output = weighted CA3 + EC input during theta
        ca1_out = ca3_out * 0.5 + entorhinal_input * 0.5
        ca1_out *= 0.5 + theta_power * 0.5
        ca1_out = min(1.0, ca1_out)

        # TPE: CA3 predicted one thing, EC says another
        tpe = abs(ca3_out - entorhinal_input) * theta_power

        # Novelty: CA1 fires more in novel environments
        novelty_signal = novelty * ca1_out * 1.5

        # Place field precision: sharp in familiar, broad in novel
        precision_target = 0.7 - novelty * 0.4
        current_precision = self.state.get("place_field_precision", 0.6)
        new_precision = current_precision * 0.95 + precision_target * 0.05

        # Sequence output
        sequence_out = ca1_out * theta_power * (0.5 + ca3_out * 0.5)

        self.state["ca1_output_strength"] = round(ca1_out, 4)
        self.state["temporal_prediction_error"] = round(tpe, 4)
        self.state["sequence_output"] = round(sequence_out, 4)
        self.state["novelty_signal"] = round(novelty_signal, 4)
        self.state["place_field_precision"] = round(new_precision, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ca1_output_strength": round(ca1_out, 4),
            "temporal_prediction_error": round(tpe, 4),
            "sequence_output": round(sequence_out, 4),
            "novelty_signal": round(novelty_signal, 4),
            "place_field_precision": round(new_precision, 4),
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

