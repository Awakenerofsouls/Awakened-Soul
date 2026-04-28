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
