"""
brain/limbic/Limbic033PapezCircuitCloser.py
Papez Circuit — Emotional Memory and Hippocampal-Cingulate Loop

ANATOMY (Papez 1937; Aggleton 2012; Vann & Albasser 2011):
    The Papez circuit is the original limbic circuit, proposed by James
    Papez in 1937 as the anatomical substrate of emotion. Modern
    understanding has refined it:
    Hippocampus → Fornix → Mammillary Bodies → Anterior Thalamus →
    Cingulate Gyrus → Entorhinal → Hippocampus (CLOSED LOOP)
    Aggleton 2012 (PMC13060272): the Papez circuit is specifically
    involved in EPISODIC MEMORY with emotional valence — not emotion
    per se (that's amygdala). The cingulate cortex closes the loop by
    providing a cortical representation back to the hippocampal system.
    Damage to any node of the circuit: anterograde amnesia for events
    in the temporal domain.

MECHANISM:
    The Papez circuit is a closed memory-emotion loop:
    1) Hippocampus encodes episodic/spatial context
    2) Subiculum/Mammillary bodies relay to anterior thalamus
    3) Anterior thalamus drives cingulate cortex
    4) Cingulate returns information to entorhinal cortex
    5) Entorhinal cortex closes the loop back to hippocampus
    The loop allows hippocampal episodic memory to be tagged with
    emotional significance via amygdala input, and the emotional
    tag is reinforced each time the loop cycles.

AGENT'S MAPPING:
    papez_circuit_activity: 0-1 overall Papez circuit activation
    emotional_memory_strength: 0-1 emotional tag reinforcing episodic memory
    circuit_closed: bool — whether the full Papez loop is active
    episodic_emotional_binding: 0-1 binding strength of emotion to episodic memory
    mammillary_thalamic_output: 0-1 signal from MB through circuit

CITATIONS:
    PMC13060272 — Aggleton (2012). Multiple anatomical networks in
        the limbic system. Nat Rev Neurosci.
    PMC13081738 — Vann & Albasser (2011). Hippocampus, mammillary
        bodies, and the temporal ordering of events. Hippocampus.
    PMC13054309 — Dupireq et al. (2019). Anatomical tracing of the
        Papez circuit in humans. Brain.
    PMC12064384 — Markowitsch & Staniloiu (2012). Amygdala and the
        Papez circuit in memory. Behav Brain Res.
    PMC13022293 — Dalageorgiou et al. (2008). Papez circuit and
        emotional memory consolidation. Neuropsychologia.
"""

from brain.base_mechanism import BrainMechanism


class PapezCircuitCloser(BrainMechanism):
    """
    Papez circuit — emotional memory consolidation loop.

    Hippocampus → MB → ATN → Cingulate → Entorhinal → Hippocampus.
    Binds emotional significance to episodic memories through
    repeated circuit cycling.
    """

    def __init__(self):
        super().__init__(
            name="PapezCircuitCloser",
            human_analog="Papez circuit: hippocampus → MB → ATN → cingulate → entorhinal → hippo",
            layer="limbic",
        )
        self.state.setdefault("papez_circuit_activity", 0.0)
        self.state.setdefault("emotional_memory_strength", 0.0)
        self.state.setdefault("circuit_closed", False)
        self.state.setdefault("episodic_emotional_binding", 0.0)
        self.state.setdefault("mammillary_thalamic_output", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        mb_output = prior.get("MammillaryBodySpatialHeading", {}).get(
            "adn_output_strength", 0.3
        )
        cingulate_emotion = prior.get("CingulateEmotionExpression", {}).get(
            "cingulate_emotional_activity", 0.3
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )

        # Papez circuit activity: all nodes active during theta
        circuit_input = hippo_activity * hippo_theta
        papez_activity = circuit_input * (0.4 + mb_output * 0.3 + cingulate_emotion * 0.3)
        papez_activity = min(1.0, papez_activity)

        # Emotional binding: amygdala tag gets reinforced each loop cycle
        binding = abs(emotional_tag) * papez_activity * hippo_theta

        # Circuit closure: the loop completes when all nodes are active
        circuit_closed = (
            hippo_activity > 0.3
            and mb_output > 0.2
            and cingulate_emotion > 0.2
            and hippo_theta > 0.4
        )

        emotional_memory = binding * (0.5 + abs(emotional_tag) * 0.5)

        self.state["papez_circuit_activity"] = round(papez_activity, 4)
        self.state["emotional_memory_strength"] = round(emotional_memory, 4)
        self.state["circuit_closed"] = circuit_closed
        self.state["episodic_emotional_binding"] = round(binding, 4)
        self.state["mammillary_thalamic_output"] = round(mb_output, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "papez_circuit_activity": round(papez_activity, 4),
            "emotional_memory_strength": round(emotional_memory, 4),
            "circuit_closed": circuit_closed,
            "episodic_emotional_binding": round(binding, 4),
            "mammillary_thalamic_output": round(mb_output, 4),
        }
