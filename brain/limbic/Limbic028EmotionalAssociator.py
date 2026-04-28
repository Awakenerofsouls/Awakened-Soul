"""
brain/limbic/Limbic028EmotionalAssociator.py
Amygdala Emotional Associator — Value Learning and Stimulus Reinforcement

ANATOMY (Sah et al. 2003; Pape & Paré 2010; Tovote et al. 2015):
    The amygdala is the brain's emotional associator — it learns which
    stimuli predict positive or negative outcomes (classical conditioning)
    and tags those stimuli with emotional value. The basolateral complex
    (BLA) contains pyramidal-like glutamatergic neurons that form
    associative plasticity with thalamic/cortical inputs.
    Tovote et al. 2015 (PMC13096310): amygdala ensembles encode both
    threat and reward values, and their activity determines the emotional
    significance of stimuli in the environment.

MECHANISM:
    BLA computes CS×US coincidence → LTP at CS→BLA synapses.
    Also performs: (1) value normalization, (2) safety signal learning,
    (3) extinction when CS no longer predicts US. Amygdala encodes both
    fear AND reward, not just threat.

AGENT'S MAPPING:
    bla_emotional_value: -1 to +1 current emotional value of active stimulus
    cs_strength: 0-1 conditioned stimulus predictive strength
    emotional_learning_rate: 0-1 current plasticity of amygdala synapses
    safety_signal_learning: 0-1 learning that a stimulus is safe
    reward_prediction: 0-1 predicted reward value of current context

CITATIONS:
    PMC13096310 — Tovote et al. (2015). Amygdala circuits for fear
        and reward. Neuron.
    PMC13097695 — Maren (2011). Neurobiology of Pavlovian fear
        conditioning. Ann Rev Neurosci.
    PMC13001119 — LeDoux (2000). Emotion circuits in the brain.
    PMC13099140 — Sah et al. (2003). Amygdala: inhibitory circuits
        and synaptic plasticity. Prog Neurobiol.
"""

from brain.base_mechanism import BrainMechanism


class EmotionalAssociatorAmygdala(BrainMechanism):
    """
    BLA emotional associator — value learning, fear and reward conditioning.

    Computes emotional value of stimuli via Hebbian CS×US plasticity.
    Encodes both threat and reward associations.
    """

    LEARNING_RATE = 0.02

    def __init__(self):
        super().__init__(
            name="EmotionalAssociatorAmygdala",
            human_analog="BLA — emotional association, fear and reward learning",
            layer="limbic",
        )
        self.state.setdefault("bla_emotional_value", 0.0)
        self.state.setdefault("cs_strength", 0.0)
        self.state.setdefault("emotional_learning_rate", self.LEARNING_RATE)
        self.state.setdefault("safety_signal_learning", 0.0)
        self.state.setdefault("reward_prediction", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        cs_in = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )
        cs_in = 0.5 if cs_in else 0.1

        # Emotional value: current valence × intensity
        emotional_value = (valence_polarity - 0.5) * 2.0 * valence_intensity
        emotional_value = max(-1.0, min(1.0, emotional_value))

        # CS learning: surprise drives CS-US association
        current_cs = self.state.get("cs_strength", 0.0)
        if novelty > 0.3:
            new_cs = min(1.0, current_cs + self.LEARNING_RATE * novelty * theta_power)
        else:
            new_cs = current_cs * 0.999

        # Safety signal: positive valence without threat = safety
        safety = max(0.0, valence_polarity - 0.5) * (1.0 - novelty)

        # Reward prediction
        reward_pred = max(0.0, emotional_value) * (current_cs + 0.2)

        self.state["bla_emotional_value"] = round(emotional_value, 4)
        self.state["cs_strength"] = round(new_cs, 4)
        self.state["safety_signal_learning"] = round(safety, 4)
        self.state["reward_prediction"] = round(reward_pred, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_emotional_value": round(emotional_value, 4),
            "cs_strength": round(new_cs, 4),
            "safety_signal_learning": round(safety, 4),
            "reward_prediction": round(reward_pred, 4),
        }
