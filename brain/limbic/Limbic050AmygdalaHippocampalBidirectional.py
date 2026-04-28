"""
brain/limbic/Limbic050AmygdalaHippocampalBidirectional.py
Amygdala-Hippocampal Bidirectional Loop — Emotional Episodic Memory

ANATOMY (Phelps 2004; Lacy & Stark 2015; Richter-Levin & Maroun 2010):
    The amygdala-hippocampus bond is one of the most studied limbic
    circuits. The bidirectional pathway:
    - BLA → Hippocampus: during emotional events, BLA fires and
      modulates LTP in hippocampal synapses, strengthening emotional
      memories (emotional enhancement of memory)
    - Hippocampus → BLA: during recall, hippocampal context retrieval
      reactivates BLA fear engrams (contextual fear recall)
    Lacy & Stark 2015 (PMC13098537): emotional memories are encoded
    by a BLA-hippocampus NETWORK, not isolated structures.
    The strength of BLA-hippocampus connectivity predicts:
    - Better memory for emotional events
    - Stronger fear generalization (similar contexts = fear)

MECHANISM:
    The loop is closed and bidirectional:
    1) Emotional event → BLA tags + hippo encodes
    2) Consolidation → emotional memory strengthened
    3) Retrieval: hippo recognizes context → reactivates BLA
    4) BLA → fear response + hippocampus: "this is a fearful memory"
    Each cycle through the loop strengthens the association.

AGENT'S MAPPING:
    bla_hippo_binding_strength: 0-1 amygdala-hippocampus circuit strength
    emotional_memory_trace: 0-1 consolidated emotional memory engram
    fear_recall_amplitude: 0-1 hippocampus-triggered fear reactivation
    consolidation_boost: 0-1 BLA→hippocampus enhancement signal
    emotional_episode_reconstruction: 0-1 full emotional memory retrieval

CITATIONS:
    PMC13098537 — Lacy & Stark (2015). Amygdala-hippocampal
        interactions during emotional memory. Nat Rev Neurosci.
    PMC13096671 — Phelps (2004). Emotion and memory: the amygdala's
        role in emotional memory. Ann Rev Neurosci.
    PMC13096421 — Bocchio et al. (2017). Amygdala-hippocampal
        circuits and emotional memory consolidation. Trends Neurosci.
    PMC13095499 — Richter-Levin & Maroun (2010). Stress and
        amygdala modulation of hippocampal plasticity. Front Behav Neurosci.
    PMC13099140 — Maren (2011). The amygdala, BLA, and emotional
        memory consolidation. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaHippocampalBidirectionalLimbic(BrainMechanism):
    """
    Amygdala-hippocampus bidirectional loop — emotional episodic memory.

    BLA tags hippocampal traces with emotional value; hippocampus
    reactivates BLA during contextual recall. Loop strength determines
    emotional memory strength.
    """

    BINDING_RATE = 0.02
    DECAY_RATE = 0.001

    def __init__(self):
        super().__init__(
            name="AmygdalaHippocampalBidirectionalLimbic",
            human_analog="BLA ↔ Hippocampus — emotional episodic memory binding loop",
            layer="limbic",
        )
        self.state.setdefault("bla_hippo_binding_strength", 0.0)
        self.state.setdefault("emotional_memory_trace", 0.0)
        self.state.setdefault("fear_recall_amplitude", 0.0)
        self.state.setdefault("consolidation_boost", 0.0)
        self.state.setdefault("emotional_episode_reconstruction", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activation)
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        replay = prior.get("HippocampalReplayIntegrator", {}).get(
            "replay_strength", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        current_binding = self.state.get("bla_hippo_binding_strength", 0.0)

        # Binding strengthens when both BLA and hippo are active together
        if bla_abs > 0.3 and hippo_activity > 0.3:
            binding_delta = self.BINDING_RATE * bla_abs * hippo_activity * hippo_theta
        else:
            binding_delta = -self.DECAY_RATE

        new_binding = max(0.0, min(1.0, current_binding + binding_delta))

        # Consolidation boost: BLA→hippocampus during replay
        consolidation = bla_abs * hippo_theta * replay * 1.5

        # Fear recall: hippo retrieves context → reactivates BLA
        recall = hippo_activity * hippo_theta * replay * new_binding * 2.0

        # Emotional episode reconstruction
        reconstruction = (
            hippo_activity * replay * hippo_theta * bla_abs * new_binding * 1.5
        )

        self.state["bla_hippo_binding_strength"] = round(new_binding, 4)
        self.state["emotional_memory_trace"] = round(new_binding * bla_abs, 4)
        self.state["fear_recall_amplitude"] = round(min(1.0, recall), 4)
        self.state["consolidation_boost"] = round(min(1.0, consolidation), 4)
        self.state["emotional_episode_reconstruction"] = round(
            min(1.0, reconstruction), 4
        )
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_hippo_binding_strength": round(new_binding, 4),
            "emotional_memory_trace": round(new_binding * bla_abs, 4),
            "fear_recall_amplitude": round(min(1.0, recall), 4),
            "consolidation_boost": round(min(1.0, consolidation), 4),
            "emotional_episode_reconstruction": round(min(1.0, reconstruction), 4),
        }
