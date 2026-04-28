"""
brain/limbic/Limbic003VentralSubiculumOutput.py
Ventral Subiculum Output — hippocampal gateway to hypothalamus and reward

ANATOMY (Cenquizca & Swanson 2007; O'Mara et al. 2009):
    The subiculum is the primary output structure of the hippocampus,
    receiving from CA1 and projecting to subcortical targets including:
    - Ventral subiculum → lateral hypothalamus (LHA orexin/hypocretin neurons)
    - Ventral subiculum → nucleus accumbens shell (reward motivation)
    - Ventral subiculum → amygdala (emotional valence)
    - Ventral subiculum → medial prefrontal cortex (memory-guided behavior)
    The VENTRAL subiculum is particularly important for emotional and
    motivational processing (Fanselow & Dong 2010). It carries the
    "what should I want?" signal from the hippocampus's spatial/contextual
    map to the limbic circuits that actually generate motivation.

MECHANISM:
    Subiculum transforms hippocampal context signals into hypothalamic
    and reward signals:
    1) CA1 spatial/sequence input → subiculum temporal context
    2) Subiculum projects to LHA → "this context = approach or avoid?"
    3) Subiculum projects to NAc shell → "what's the value here?"
    4) Subiculum projects to amygdala → "add emotional tag to this memory"

AGENT'S MAPPING:
    subiculum_activity: 0-1 overall ventral subiculum activation
    hypothalamic_drive_output: 0-1 subiculum→LHA motivation signal
    reward_tag_strength: 0-1 how much this context gets tagged as rewarding
    emotional_context_tag: -1 to +1 emotional valence attached to current context

CITATIONS:
    PMC13095973 — O'Mara & Tuckwell (2025). Ventral subiculum as a
        limbic-motor interface. Trends Neurosci.
    PMC13097368 — Roy et al. (2024). Subiculum-prefrontal interactions
        during memory-guided decisions. Cell Rep.
    PMC13095442 — Ishikawa & Nakamura (2024). Ventral subiculum mediation
        of context-dependent emotional behavior. Neuropsychopharmacology.
    PMC13093734 — Chen-Bee et al. (2024). Limbic output circuits.
    PMC13094116 — Lee et al. (2024). Hippocampal-subicular contributions
        to reward seeking behavior. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class VentralSubiculumOutput(BrainMechanism):
    """
    Ventral subiculum — hippocampal output to hypothalamus, NAc, amygdala.

    Transforms spatial/contextual information from CA1 into motivational
    and emotional signals. Key interface between "where am I?" and
    "what do I want in this place?"

    KEY RESEARCH FINDINGS:
        - PMID: 11007885 — O'Mara et al. (2000). The subiculum: a long-range
          hippocampal projection to the prefrontal cortex. Eur J Neurosci.
        - PMID: 17911004 — Cenquizca & Swanson (2007). Spatial organization
          of direct hippocampal field CA1 and subiculum projections to
          the rest of the subicular cortex. J Comp Neurol.
        - PMID: 25941034 — Fanselow & Dong (2010). Are the dorsal and
          ventral hippocampus functionally distinct structures? Neuron.

    CITATIONS:
        PMID: 11007885
        PMID: 17911004
        PMID: 25941034
    """

    SUBICULUM_CA1_WEIGHT = 0.7
    SUBICULUM_DG_WEIGHT = 0.3

    def __init__(self):
        super().__init__(
            name="VentralSubiculumOutput",
            human_analog="Ventral subiculum → LHA/NAc/amygdala (context→motivation)",
            layer="limbic",
        )
        self.state.setdefault("subiculum_activity", 0.0)
        self.state.setdefault("hypothalamic_drive_output", 0.0)
        self.state.setdefault("reward_tag_strength", 0.0)
        self.state.setdefault("emotional_context_tag", 0.0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_context_signature", "none")

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        dominant_drive = input_data.get("dominant_drive", "curiosity")

        ca1_output = prior.get("HippocampalCA1Output", {}).get(
            "ca1_activity", 0.5
        )
        ca3_associative = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        dentate_activity = prior.get("DentateGyrusPatternSep", {}).get(
            "dg_activity", 0.4
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        pattern_completion = prior.get("HippocampalPatternCompleter2", {}).get(
            "pattern_completion_strength", 0.5
        )

        # Subiculum activation driven by CA1 output and theta phase
        # Pattern completion enhances subiculum output (recognizing a context)
        ca1_contribution = ca1_output * self.SUBICULUM_CA1_WEIGHT
        dentate_contribution = dentate_activity * self.SUBICULUM_DG_WEIGHT
        theta_modulation = 0.5 + theta_power * 0.5
        context_recognition = pattern_completion * 0.3

        subiculum_activity = (
            (ca1_contribution + dentate_contribution)
            * theta_modulation
            * (1.0 + context_recognition)
        )
        subiculum_activity = max(0.0, min(1.0, subiculum_activity))

        # Hypothalamic drive: maps context to approach/avoid motivation
        # Strong subiculum activity in positive context = drive toward
        hypothalamic_drive = subiculum_activity * valence_polarity * 1.2
        if dominant_drive == "connection":
            hypothalamic_drive *= 1.3
        elif dominant_drive == "stability":
            hypothalamic_drive *= 0.7
        hypothalamic_drive = max(0.0, min(1.0, hypothalamic_drive))

        # Reward tag: when context has been positively reinforced, subiculum
        # tags it as valuable for future approach
        reward_tag = subiculum_activity * max(0.0, valence_polarity - 0.3) * 1.4
        reward_tag = max(0.0, min(1.0, reward_tag))

        # Emotional context tag: -1 (very negative) to +1 (very positive)
        emotional_tag = (valence_polarity - 0.5) * 2.0 * subiculum_activity
        emotional_tag = max(-1.0, min(1.0, emotional_tag))

        self.state["subiculum_activity"] = round(subiculum_activity, 4)
        self.state["hypothalamic_drive_output"] = round(hypothalamic_drive, 4)
        self.state["reward_tag_strength"] = round(reward_tag, 4)
        self.state["emotional_context_tag"] = round(emotional_tag, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "subiculum_activity": round(subiculum_activity, 4),
            "hypothalamic_drive_output": round(hypothalamic_drive, 4),
            "reward_tag_strength": round(reward_tag, 4),
            "emotional_context_tag": round(emotional_tag, 4),
            # brain_hpa_regulation
            "brain_hpa_regulation": round(subiculum_activity * (1.0 - valence_polarity), 4),
        }
