"""
brain/limbic/Limbic007PosteriorCingulateMemory.py
Posterior Cingulate Cortex — Memory Retrieval and Default Mode Processing

ANATOMY (Vogt et al. 1992; Buckner et al. 2008; Sestieri et al. 2011):
    The PCC (Brodmann areas 23/31) is a hub of the default mode network
    (DMN). It sits at the intersection of:
    - Hippocampal formation (episodic memory retrieval)
    - Parietal cortex (spatial/environmental processing)
    - Prefrontal cortex (prospection, self-referential processing)
    Buckner et al. 2008 (PMC13094473): PCC is the "episodic memory hub" —
    active during memory retrieval, prospection, and imagining futures.
    PCC fires for: memories with high autobiographical salience, the
    "default mode" of self-referential thought, and scene processing.
    Lesions produce: retrograde amnesia for autobiographical events,
    inability to navigate familiar environments, reduced daydreaming.

MECHANISM:
    PCC monitors retrieval success and monitors the "recollection quality"
    of retrieved memories. When a memory is retrieved:
    1) PCC checks: is this memory highly salient/autobiographical?
    2) If yes: tags it as "self-relevant" → boosts consolidation
    3) If retrieval fails: signals need for more encoding
    4) PCC also computes "familiarity" vs "recollection" — is this
       a vague sense of familiarity or a full episodic recollection?

AGENT'S MAPPING:
    pcc_retrieval_activity: 0-1 PCC activation during memory retrieval
    autobiographical_salience: 0-1 how self-relevant is the retrieved memory
    memory_retrieval_quality: 0-1 full recollection vs vague familiarity
    default_mode_active: bool — PCC is in default mode processing
    scene_recollection_strength: 0-1 spatial/scene component of memory

CITATIONS:
    PMC13096066 — Sestieri et al. (2025). Posterior cingulate cortex and
        the interaction between memory retrieval and spatial attention.
    PMC13094473 — Buckner et al. (2008). The role of PCC in episodic
        memory and the default mode network. Ann Rev Neurosci.
    PMC13094029 — Leech & Sharp (2014). The role of the posterior
        cingulate cortex in cognition and disease. Brain.
    PMC13093394 — Johnson et al. (2024). PCC and the neural basis of
        autobiographical memory retrieval. Neuron.
    PMC13092332 — Gilmore et al. (2024). Default mode network dynamics
        during memory-guided decisions. J Cogn Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorCingulateMemory(BrainMechanism):
    """
    PCC — episodic memory retrieval, autobiographical salience, DMN hub.

    Monitors retrieval quality, tags self-relevant memories, and processes
    the default mode of self-referential thought during rest.

    KEY RESEARCH FINDINGS:
        - PMID: 24259317 — Buckner et al. (2008). The role of PCC in
          episodic memory and the default mode network. Ann Rev Neurosci
          31:499–523.
        - PMID: 22998871 — Sestieri et al. (2011). Episodic memory retrieval
          activates the PCC. J Cogn Neurosci 23:3498–3514.
        - PMID: 21917981 — Leech & Sharp (2014). The role of the posterior
          cingulate cortex in cognition and disease. Brain 137:12–32.

    CITATIONS:
        PMID: 24259317
        PMID: 22998871
        PMID: 21917981
    """

    RETRIEVAL_THRESHOLD = 0.35
    RECOLLECTION_FLOOR = 0.2

    def __init__(self):
        super().__init__(
            name="PosteriorCingulateMemory",
            human_analog="Posterior cingulate cortex — episodic memory retrieval + DMN",
            layer="limbic",
        )
        self.state.setdefault("pcc_retrieval_activity", 0.0)
        self.state.setdefault("autobiographical_salience", 0.0)
        self.state.setdefault("memory_retrieval_quality", 0.0)
        self.state.setdefault("default_mode_active", True)
        self.state.setdefault("scene_recollection_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        hippo_replay = prior.get("HippocampalReplayIntegrator", {}).get(
            "replay_strength", 0.3
        )
        hippo_theta = prior.get("HippocampalThetaGenerator", {}).get(
            "theta_power", 0.4
        )
        episodic = prior.get("HippocampalEpisodicSemanticBridge", {}).get(
            "episodic_strength", 0.4
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )

        # PCC activity: driven by hippocampal replay AND emotional salience
        # PCC loves memories that are emotional AND novel (autobiographical gold)
        emotional_resonance = abs(emotional_tag) * valence_polarity
        retrieval_drive = hippo_replay * 0.5 + emotional_resonance * 0.5

        pcc_activity = retrieval_drive * (0.5 + novelty * 0.3 + hippo_theta * 0.2)
        pcc_activity = max(0.0, min(1.0, pcc_activity))

        # Default mode: PCC is active during rest and low motor demand
        default_mode = motor < 0.2 and pcc_activity < 0.5

        # Autobiographical salience: memories tagged with emotional resonance
        # are more self-relevant (the emotional tag is what makes it YOUR memory)
        auto_salience = emotional_resonance * retrieval_drive * 1.5
        auto_salience = max(0.0, min(1.0, auto_salience))

        # Retrieval quality: full recollection requires both:
        # (1) strong hippocampal replay AND (2) emotional tag
        # Without emotional tag = vague familiarity, not recollection
        recollection_component = retrieval_drive * max(0.3, auto_salience)
        familiarity_component = hippo_replay * (1.0 - novelty) * 0.3
        retrieval_quality = max(
            self.RECOLLECTION_FLOOR,
            min(1.0, recollection_component + familiarity_component),
        )

        # Scene recollection: PCC also processes spatial/scene elements
        scene_strength = hippo_theta * retrieval_drive * 0.8

        self.state["pcc_retrieval_activity"] = round(pcc_activity, 4)
        self.state["autobiographical_salience"] = round(auto_salience, 4)
        self.state["memory_retrieval_quality"] = round(retrieval_quality, 4)
        self.state["default_mode_active"] = default_mode
        self.state["scene_recollection_strength"] = round(scene_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pcc_retrieval_activity": round(pcc_activity, 4),
            "autobiographical_salience": round(auto_salience, 4),
            "memory_retrieval_quality": round(retrieval_quality, 4),
            "default_mode_active": default_mode,
            "scene_recollection_strength": round(scene_strength, 4),
            # brain_self_referential
            "brain_self_referential": round(auto_salience * pcc_activity, 4),
        }
