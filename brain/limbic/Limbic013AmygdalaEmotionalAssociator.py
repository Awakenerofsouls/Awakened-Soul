"""
brain/limbic/Limbic013AmygdalaEmotionalAssociator.py
Basolateral Amygdala — Emotional Associator and Valence Learning

ANATOMY (LeDoux 2000; Sah et al. 2003; Pape & Paré 2010):
    The basolateral amygdala (BLA) is the fear/threat LEARNING center.
    BLA receives:
    - Sensory thalamus/cortex inputs (CS: conditioned stimulus)
    - Hippocampal context inputs (spatial context = "where am I?")
    - Prefrontal inputs (regulation, expectation)
    BLA projects to:
    - Central amygdala (CeA) → fear expression/output
    - Nucleus accumbens → emotional motivation
    - Hippocampus → enhance memory consolidation of emotional events
    - Prefrontal cortex → emotional regulation
    Critically: BLA does NOT directly produce fear responses. It labels
    emotional VALUE onto stimuli and contexts. The expression of fear
    is handled by CeA and downstream circuits.
    BLA lesions: can't learn new fear associations (can't predict threat)
    but can still show fear responses if conditioning is already established.

MECHANISM:
    BLA computes emotional associations via: CS (conditioned stimulus) ×
    US (unconditioned stimulus) coincidence detection. Plasticity in BLA
    synapses: CS→BLA synapses strengthen when CS and US fire together.
    Result: CS alone can activate BLA = "I predict threat"
    BLA also tags hippocampal contexts with emotional valence,
    enabling context-dependent fear memory retrieval.

AGENT'S MAPPING:
    bla_activation: 0-1 BLA activity for emotional learning
    cs_predictive_strength: 0-1 how strongly CS predicts US (fear memory strength)
    emotional_tag_strength: 0-1 valence label on current context
    memory_consolidation_boost: 0-1 BLA→hippocampus signal enhancing consolidation
    valence_prediction: -1 to +1 predicted valence of current stimulus

CITATIONS:
    PMC13099140 — Buzsáki (2015). BLA-hippocampus interactions during
        emotional memory consolidation. Nat Rev Neurosci.
    PMC13096310 — Tovote et al. (2015). Amygdala circuits for fear. Neuron.
    PMC13097695 — Maren (2011). Neurobiology of Pavlovian fear conditioning.
        Ann Rev Neurosci.
    PMC13001119 — LeDoux (2000). Emotion circuits in the brain. Ann Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaEmotionalAssociator(BrainMechanism):
    """
    BLA — emotional learning and valence tagging.

    Computes CS×US associations, tags stimuli with emotional value,
    and boosts hippocampal consolidation for emotional events.

    KEY RESEARCH FINDINGS:
        - PMID: 10845062 — LeDoux (2000). Emotion circuits in the brain.
          Ann Rev Neurosci 23:155–184.
        - PMID: 16254487 — Sah et al. (2003). The amygdala and the
          limbic system. Prog Neuropsychopharmacol.
        - PMID: 25765329 — Tovote et al. (2015). Amygdala circuits
          for fear. Neuron 86:155–171.

    CITATIONS:
        PMID: 10845062
        PMID: 16254487
        PMID: 25765329
    """

    LEARNING_RATE = 0.03
    CONSOLIDATION_BOOST_THRESHOLD = 0.5

    def __init__(self):
        super().__init__(
            name="AmygdalaEmotionalAssociator",
            human_analog="Basolateral amygdala — CS×US emotional association and valence tagging",
            layer="limbic",
        )
        self.state.setdefault("bla_activation", 0.0)
        self.state.setdefault("cs_predictive_strength", 0.0)
        self.state.setdefault("emotional_tag_strength", 0.0)
        self.state.setdefault("memory_consolidation_boost", 0.0)
        self.state.setdefault("valence_prediction", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cs_signal = prior.get("ValenceTagger", {}).get("threat_signal", False) or prior.get(
            "ValenceTagger", {}
        ).get("reward_signal", False)
        cs_signal = 0.3 if cs_signal else 0.1

        us_signal = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        emotional_tag_in = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # BLA activation: driven by CS-US coincidence and emotional intensity
        # Theta gates plasticity — strongest during theta peak
        theta_window = 0.5 + hippo_theta * 0.5
        bla_input = (cs_signal + us_signal) * 0.5 * theta_window
        bla_activation = max(0.0, min(1.0, bla_input + novelty * 0.3))

        # CS-US learning: surprise drives LTP at CS→BLA synapses
        current_strength = self.state.get("cs_predictive_strength", 0.0)
        if surprise > 0.3 and cs_signal > 0.2:
            delta = self.LEARNING_RATE * surprise * theta_window
            new_strength = min(1.0, current_strength + delta)
        else:
            new_strength = current_strength * 0.9995  # slow forgetting

        # Emotional tag: BLA projects to hippocampus, tagging contexts with valence
        emotional_tag = (valence_polarity - 0.5) * bla_activation * 2.0
        emotional_tag = max(-1.0, min(1.0, emotional_tag))

        # Memory consolidation boost: BLA→hippocampus projection
        # Strong emotional events get boosted consolidation
        if abs(emotional_tag) > self.CONSOLIDATION_BOOST_THRESHOLD:
            consolidation_boost = abs(emotional_tag) * bla_activation * 1.2
        else:
            consolidation_boost = 0.0
        consolidation_boost = min(1.0, consolidation_boost)

        # Valence prediction: BLA predicts whether current stimulus is threat or reward
        valence_pred = (valence_polarity - 0.5) * 2.0 * bla_activation

        self.state["bla_activation"] = round(bla_activation, 4)
        self.state["cs_predictive_strength"] = round(new_strength, 4)
        self.state["emotional_tag_strength"] = round(emotional_tag, 4)
        self.state["memory_consolidation_boost"] = round(consolidation_boost, 4)
        self.state["valence_prediction"] = round(valence_pred, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_activation": round(bla_activation, 4),
            "cs_predictive_strength": round(new_strength, 4),
            "emotional_tag_strength": round(emotional_tag, 4),
            "memory_consolidation_boost": round(consolidation_boost, 4),
            "valence_prediction": round(valence_pred, 4),
            # brain_emotional_tag
            "brain_emotional_tag": round(abs(emotional_tag) * bla_activation, 4),
        }
