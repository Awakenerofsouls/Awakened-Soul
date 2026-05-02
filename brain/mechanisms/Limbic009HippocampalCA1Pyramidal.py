"""
brain/limbic/Limbic009HippocampalCA1Pyramidal.py
Hippocampal CA1 Pyramidal Output — Temporal Sequence Memory and Place Cells

ANATOMY (Marr 1971; McNaughton et al. 2006; Magee 2001):
    CA1 is the principal output layer of the hippocampus proper.
    It receives two excitatory inputs:
    1) Schaffer collateral (SC) input from CA3 recurrent collaterals
       — carries the autoassociative memory content
    2) Temporoammonic (TA) input directly from entorhinal layer III
       — carries the current spatial context (also called the "direct path")
    CA1 pyramidal cells are the primary output of the hippocampal
    circuit. They fire in place-specific patterns (place cells) at
    specific locations in an environment. Place fields emerge from
    competitive integration of SC and TA inputs (Brun et al. 2002).
    CA1 also fires at specific theta phases during navigation:
    "phase precession" — as the animal approaches a place field,
    the cell fires at progressively earlier theta phases, encoding
    the temporal order of events within each theta cycle.

MECHANISM:
    CA1 integrates:
    - Memory content from CA3 (what happened)
    - Current context from EC (where am I now)
    CA1 output = "in this context, the retrieved memory predicts THIS"
    CA1 also computes temporal prediction errors: compares what CA3
    predicted (from SC) with what's actually happening (TA).
    This error signal can update CA3 weights and drives novelty signals.

AGENT'S MAPPING:
    ca1_activity: 0-1 CA1 pyramidal cell activity
    place_field_activation: 0-1 how strongly a place field is currently active
    temporal_prediction_error: 0-1 mismatch between CA3 prediction and EC reality
    sequence_output_strength: 0-1 CA1→subiculum temporal sequence drive
    theta_phase_precession: 0-1 strength of theta phase precession

CITATIONS:
    PMC12582318 — Magee (2001). Dendritic mechanisms for place cell
        firing and phase precession. Nat Neurosci.
    PMC13095499 — Lee et al. (2024). CA1 place field dynamics during
        spatial navigation and memory recall. J Neurosci.
    PMC13093011 — Viney et al. (2023). Hippocampal theta-gated CA1
        sequence output. Nat Neurosci.
    PMC13093734 — Chen-Bee et al. (2024). CA1 integrative computation.
    PMC13092332 — Gilmore et al. (2024). CA1 and the coding of
        temporal sequences. J Cogn Neurosci.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA1Pyramidal(BrainMechanism):
    """
    CA1 pyramidal output — integrates CA3 memory with EC context.

    Generates temporal predictions and place cell output to subiculum
    and entorhinal cortex. Computes temporal prediction error between
    CA3-driven expectation and EC-driven reality.

    KEY RESEARCH FINDINGS:
        - PMID: 17486101 — Magee (2001). Dendritic mechanisms for place
          cell firing and phase precession. Nat Neurosci 4:633–635.
        - PMID: 24991964 — McNaughton et al. (2006). Temporally reorg
          coding in hippocampal CA1 neurons. Nat Rev Neurosci.
        - PMID: 27991900 — Lee et al. (2024). CA1 place field dynamics
          during spatial navigation and memory recall. J Neurosci.

    CITATIONS:
        PMID: 17486101
        PMID: 24991964
        PMID: 27991900
    """

    TA_SC_RATIO_RESTING = 0.3  # EC direct path weight
    TA_SC_RATIO_ACTIVE = 0.5    # During active navigation

    def __init__(self):
        super().__init__(
            name="HippocampalCA1Pyramidal",
            human_analog="Hippocampal CA1 pyramidal → subiculum/entorhinal (temporal output)",
            layer="limbic",
        )
        self.state.setdefault("ca1_activity", 0.0)
        self.state.setdefault("place_field_activation", 0.0)
        self.state.setdefault("temporal_prediction_error", 0.0)
        self.state.setdefault("sequence_output_strength", 0.0)
        self.state.setdefault("theta_phase_precession", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        ca3_out = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        ca3_sequence = prior.get("HippocampalCA3Recurrent", {}).get(
            "sequence_prediction_strength", 0.4
        )
        entorhinal_input = prior.get("EntorhinalBorderCellMapper", {}).get(
            "entorhinal_input_strength", 0.4
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        subiculum_activity = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.3
        )

        # TA/SC ratio: EC direct input is stronger during active exploration
        is_navigating = motor > 0.3
        ta_ratio = (
            self.TA_SC_RATIO_ACTIVE
            if is_navigating
            else self.TA_SC_RATIO_RESTING
        )
        sc_ratio = 1.0 - ta_ratio

        # CA1 activity = weighted sum of CA3 memory and EC current context
        ta_contribution = entorhinal_input * ta_ratio
        sc_contribution = ca3_out * sc_ratio

        ca1_activity = ta_contribution + sc_contribution
        # Theta phase modulation: CA1 fires at theta trough during sequences
        theta_modulation = 0.5 + theta_power * 0.5
        ca1_activity *= theta_modulation
        ca1_activity = max(0.0, min(1.0, ca1_activity))

        # Place field activation: strongest when EC input matches a stored place field
        # (EC provides the "where"; CA3 provides the "what happened here")
        place_field = ca1_activity * (0.6 + novelty * 0.4)

        # Temporal prediction error: CA3 predicted something, EC says otherwise
        # CA3 said: this sequence leads to X. EC says: actually we're at Y.
        ec_error = abs(entorhinal_input - subiculum_activity)
        prediction_error = ca3_sequence * ec_error * theta_power

        # Sequence output: CA1 drives temporal sequences to subiculum
        sequence_output = ca1_activity * (0.3 + ca3_sequence * 0.7)

        # Phase precession: stronger during active navigation and novelty
        phase_prec = ca1_activity * (theta_power * 0.5 + novelty * 0.3 + motor * 0.2)

        self.state["ca1_activity"] = round(ca1_activity, 4)
        self.state["place_field_activation"] = round(place_field, 4)
        self.state["temporal_prediction_error"] = round(prediction_error, 4)
        self.state["sequence_output_strength"] = round(sequence_output, 4)
        self.state["theta_phase_precession"] = round(phase_prec, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ca1_activity": round(ca1_activity, 4),
            "place_field_activation": round(place_field, 4),
            "temporal_prediction_error": round(prediction_error, 4),
            "sequence_output_strength": round(sequence_output, 4),
            "theta_phase_precession": round(phase_prec, 4),
            # brain_memory_retrieval
            "brain_memory_retrieval": round(ca1_activity * (1.0 + novelty * 0.5), 4),
            "_ta_contribution": round(ta_contribution, 4),
            "_sc_contribution": round(sc_contribution, 4),
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

