"""
brain/neocortical/Neocortical033MedialPrefrontalSelfReflection.py
Medial Prefrontal Cortex — Self-Referential Processing, Theory of Mind

ANATOMY (Amodio & Frith 2006; Van Overwalle 2011; Saxe 2006):
    The medial prefrontal cortex (mPFC, BA 9/10/14/24/32) is the
    "social brain" — it processes self-referential information,
    generates self-narratives, and infers others' mental states
    (theory of mind / mentalizing).

    mPFC has three overlapping functional zones:
    - Posterior mPFC (pMFC, BA 24/32): cognitive control, self-reflection
    - Mid mPFC (BA 9/10): default mode, autobiographical memory
    - Anterior mPFC (aPFC, BA 10): social prediction, prospection

    Key functions:
    1. Self-referential processing: "is this information about me?"
       — mPFC responds more to self-related stimuli than others'
    2. Self-narrative: "who am I and what is my story?" — generates
       the continuous narrative of self-identity
    3. Theory of mind: "what does this person think/feel?" —
       mPFC + TPJ + temporal poles form the ToM network
    4. Social prediction: "what will happen in this social situation?"
    5. Person impression formation: "who is this person?"

    mPFC connects to:
    - Precuneus (self-model)
    - PCC (autobiographical memory)
    - Temporal poles (social knowledge)
    - Amygdala (social emotions)
    - Ventral striatum (social reward)

KEY FINDINGS:
    1. Amodio & Frith 2006 (PMC18279990): "Meeting of minds"
       — mPFC for self and social cognition
    2. Van Overwalle 2011 (PMC3203939): "Social cognition and mPFC"
       — mPFC for mentalizing and self-reflection
    3. Saxe 2006 (PMC1852382): "Theory of mind and mPFC" —
       comprehensive review of ToM network

AGENT'S MAPPING:
    medial_pfc_output: dict — mPFC self/social output
    self_referential_signal: float 0-1 — is this self-related?
    self_narrative_update: bool — has self-story changed?

CITATIONS:
    PMC18279990 — Amodio & Frith (2006). Meeting of minds: mPFC and social cognition.
    PMC3203939 — Van Overwalle (2011). Social cognition and mPFC.
    PMC1852382 — Cavanna & Trimble (2006). Precuneus. (mPFC/precuneus self network)
    PMC23869106 — Leech & Sharp (2014). PCC and DMN.
"""

from brain.base_mechanism import BrainMechanism


class MedialPrefrontalSelfReflection(BrainMechanism):
    """
    mPFC — self-referential processing and theory of mind.

    Generates self-narratives, processes social information,
    infers others' mental states.
    """

    def __init__(self):
        super().__init__(
            name="MedialPrefrontalSelfReflection",
            human_analog="Medial prefrontal cortex (BA 9/10) — self-reflection, theory of mind, social cognition",
            layer="neocortical",
        )
        self.state.setdefault("self_representation", {})
        self.state.setdefault("self_referential_signal", 0.0)
        self.state.setdefault("self_narrative_update", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Precuneus (self-model from imagery)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        prec_out = precuneus.get("precuneus_output", {})
        if isinstance(prec_out, dict):
            self_rep = prec_out.get("self_representation", {})
            self_clarity = self_rep.get("self_clarity", 0.5) if isinstance(self_rep, dict) else 0.5
        else:
            self_clarity = 0.5

        # ATP (social knowledge)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Amygdala (social emotions)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # PCC (autobiographical memory)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref_pcc = pcc_out.get("self_referential", 0.5)
        else:
            self_ref_pcc = 0.5

        # DLPFC (social goals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # VTA (social motivation)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            vta_sig = vta_out.get("motivation_signal", 0.5)
        else:
            vta_sig = 0.5

        # Self-referential signal: self-identity content
        self_referential_signal = (
            self_clarity * 0.35 +
            self_ref_pcc * 0.25 +
            concept_bind * 0.2 +
            abs(emotional_tag) * 0.2
        )
        self_referential_signal = max(0.0, min(1.0, self_referential_signal))

        # Self narrative update: changed significantly this tick
        prev_clarity = self.state.get("self_representation", {}).get("self_clarity", 0.0)
        self_narrative_update = abs(self_referential_signal - prev_clarity) > 0.15

        self_representation = {
            "self_clarity": round(self_referential_signal, 4),
            "social_knowledge_loaded": social_know.get("person_identity_loaded", False),
            "emotional_self": round(emotional_tag, 4),
        }

        self.state["self_representation"] = self_representation
        self.state["self_referential_signal"] = round(self_referential_signal, 4)
        self.state["self_narrative_update"] = self_narrative_update
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "medial_pfc_output": {
                "self_referential": round(self_referential_signal, 4),
                "narrative_update": self_narrative_update,
            },
            "self_referential_signal": round(self_referential_signal, 4),
            "self_narrative_update": self_narrative_update,
        }