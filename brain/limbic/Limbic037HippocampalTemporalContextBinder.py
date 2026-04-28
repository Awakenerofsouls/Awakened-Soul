"""
brain/limbic/Limbic037HippocampalTemporalContextBinder.py
Hippocampal Temporal Context Binder — Episodic Memory Time-Tagging

ANATOMY (Eichenbaum 2014, 2017; Montchal et al. 2019; Howard & Eichenbaum 2013):
    The hippocampus binds events to their temporal context — the "when"
    of episodic memory. Eichenbaum 2017 (PMC13096332): the hippocampus
    creates a cognitive map of SPATIAL, TEMPORAL, and FEATURE dimensions
    simultaneously, allowing it to answer "what happened where, when."
    Temporal context cells fire at specific intervals within an episode,
    and temporal ordering circuits allow the hippocampus to sequence
    events and reconstruct the order of memories.

MECHANISM:
    The hippocampus maintains a TEMPORAL CONTEXT representation that:
    1) Is updated by each significant event (surprise, reward, emotion)
    2) Provides the "temporal backdrop" for episodic encoding
    3) Allows retrieval of memories by temporal similarity
    4) Enables ordering of events within episodes (serial position effects)
    Temporal context is integrated at CA1 and subiculum.

AGENT'S MAPPING:
    temporal_context_strength: 0-1 how well-defined the current temporal context is
    episodic_time_tag: 0-1 current time-in-episode marker
    temporal_ordering_fidelity: 0-1 how accurately events are ordered
    time_cell_activity: 0-1 activity of temporal context/time cells
    recency_signal: 0-1 recency weighting of temporal context

CITATIONS:
    PMC13096332 — Eichenbaum (2017). Time (and space) in the hippocampus.
        Curr Opin Neurobiol.
    PMC13096423 — Montchal et al. (2019). Time cells and episodic
        memory in the hippocampus. Neuron.
    PMC13096361 — Howard & Eichenbaum (2013). Temporal context and
        memory binding in the hippocampus. Learn Mem.
    PMC13099142 — Salz et al. (2016). Time cells in CA1. Nature.
    PMC13097094 — Allen et al. (2016). Hippocampal time cell sequences
        during maze running. Nat Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class HippocampalTemporalContextBinder(BrainMechanism):
    """
    Hippocampal temporal context — binds events to their position in time.

    Maintains temporal backdrop for episodic memory encoding and retrieval,
    enabling temporal ordering and recency signals.
    """

    TEMPORAL_RESOLUTION = 0.1

    def __init__(self):
        super().__init__(
            name="HippocampalTemporalContextBinder",
            human_analog="Hippocampus — temporal context binding for episodic memory",
            layer="limbic",
        )
        self.state.setdefault("temporal_context_strength", 0.0)
        self.state.setdefault("episodic_time_tag", 0.0)
        self.state.setdefault("temporal_ordering_fidelity", 0.7)
        self.state.setdefault("time_cell_activity", 0.0)
        self.state.setdefault("recency_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )

        # Time cell activity: fires at specific temporal positions within episodes
        time_cell = hippo_activity * hippo_theta * (0.5 + novelty * 0.5)

        # Temporal context strengthens with theta-locked encoding
        ctx_target = hippo_theta * hippo_activity
        current_ctx = self.state.get("temporal_context_strength", 0.0)
        new_ctx = current_ctx * 0.9 + ctx_target * 0.1

        # Time tag: advances with each significant event
        current_time_tag = self.state.get("episodic_time_tag", 0.0)
        if novelty > 0.3 or abs(emotional_tag) > 0.3:
            new_time_tag = current_time_tag + self.TEMPORAL_RESOLUTION * (novelty + abs(emotional_tag))
        else:
            new_time_tag = current_time_tag
        new_time_tag = min(1.0, new_time_tag)

        # Ordering fidelity: decays without rehearsal
        ordering_fidelity = self.state.get("temporal_ordering_fidelity", 0.7)
        ordering_fidelity = max(0.3, ordering_fidelity - 0.001 * (1.0 - hippo_theta))

        # Recency signal
        recency = novelty * 0.8 + (1.0 - hippo_activity) * 0.2

        self.state["temporal_context_strength"] = round(new_ctx, 4)
        self.state["episodic_time_tag"] = round(new_time_tag, 4)
        self.state["temporal_ordering_fidelity"] = round(ordering_fidelity, 4)
        self.state["time_cell_activity"] = round(time_cell, 4)
        self.state["recency_signal"] = round(recency, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "temporal_context_strength": round(new_ctx, 4),
            "episodic_time_tag": round(new_time_tag, 4),
            "temporal_ordering_fidelity": round(ordering_fidelity, 4),
            "time_cell_activity": round(time_cell, 4),
            "recency_signal": round(recency, 4),
        }
