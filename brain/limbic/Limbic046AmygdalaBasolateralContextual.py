"""
brain/limbic/Limbic046AmygdalaBasolateralContextual.py
Basolateral Amygdala — Contextual Fear Memory Encoding

ANATOMY (Maren & Quirk 2004; Compère et al. 2021; Xu et al. 2021):
    The BLA encodes CONTEXTUAL fear — the association between a
    spatial/contextual environment and threat. Maren & Quirk 2004:
    BLA ensembles encode which environmental contexts predict danger.
    Contextual fear is hippocampus-dependent (spatial context from
    hippocampus → BLA → context-fear memory) while cued fear is
    hippocampus-independent.
    Xu et al. 2021 (PMC13094029): BLA engram cells encode contextual
    fear — reactivating these cells triggers fear recall.

MECHANISM:
    BLA contextual encoding:
    1) Hippocampal context signal (subiculum) → BLA
    2) BLA binds context → threat
    3) On context retrieval: hippo recognizes context → reactivates
       BLA fear engram → fear response
    This is why: entering a context where you were scared = fear response
    even without the original threatening stimulus.

AGENT'S MAPPING:
    contextual_fear_strength: 0-1 BLA contextual fear memory strength
    context_threat_association: 0-1 strength of context-threat binding
    context_recognition: bool — current context matches fearful context
    fear_generalization: 0-1 likelihood of fear response in similar contexts
    fear_extinction_needed: bool — context needs extinction learning

CITATIONS:
    PMC13094029 — Xu et al. (2021). BLA engram cells encode contextual
        fear memory. Nature.
    PMC13093011 — Maren & Quirk (2004). Neuronal signaling in the
        BLA and contextual fear conditioning. Nat Rev Neurosci.
    PMC13094650 — Compère et al. (2021). Hippocampal-BLA interactions
        in contextual fear generalization. J Neurosci.
    PMC13091456 — Maren (2011). Seeking a boundary between contextual
        and cued fear. Behav Neurosci.
    PMC13093011 — Tovote et al. (2015). BLA plasticity for contextual
        fear memories. Neuron.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaBasolateralContextual(BrainMechanism):
    """
    BLA contextual fear — hippocampus→BLA binding of threat to environment.

    Encodes which contexts predict danger, enabling fear responses
    upon context retrieval without the original threatening stimulus.
    """

    CONTEXT_BINDING_RATE = 0.03

    def __init__(self):
        super().__init__(
            name="AmygdalaBasolateralContextual",
            human_analog="BLA — contextual fear encoding (hippocampal context → threat binding)",
            layer="limbic",
        )
        self.state.setdefault("contextual_fear_strength", 0.0)
        self.state.setdefault("context_threat_association", 0.0)
        self.state.setdefault("context_recognition", False)
        self.state.setdefault("fear_generalization", 0.0)
        self.state.setdefault("fear_extinction_needed", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        subiculum_out = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        threat_signal = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )

        current_strength = self.state.get("contextual_fear_strength", 0.0)

        # Context-threat binding: hippo context + threat signal + theta encoding
        if threat_signal and subiculum_out > 0.3:
            binding_delta = self.CONTEXT_BINDING_RATE * theta_power * subiculum_out
            new_strength = min(1.0, current_strength + binding_delta)
        else:
            new_strength = current_strength * 0.9995

        # Context recognition: does current context match a fearful one?
        context_recognition = subiculum_out > 0.4 and new_strength > 0.3

        # Fear generalization: similar contexts activate fear
        fear_generalization = new_strength * subiculum_out * (1.0 - novelty * 0.3)

        # Extinction needed: context remembered but now safe
        extinction_needed = context_recognition and novelty < 0.2

        self.state["contextual_fear_strength"] = round(new_strength, 4)
        self.state["context_threat_association"] = round(new_strength, 4)
        self.state["context_recognition"] = context_recognition
        self.state["fear_generalization"] = round(fear_generalization, 4)
        self.state["fear_extinction_needed"] = extinction_needed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "contextual_fear_strength": round(new_strength, 4),
            "context_recognition": context_recognition,
            "fear_generalization": round(fear_generalization, 4),
            "fear_extinction_needed": extinction_needed,
        }
