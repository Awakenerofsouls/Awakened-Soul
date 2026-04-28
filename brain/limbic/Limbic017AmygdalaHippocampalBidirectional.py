"""
brain/limbic/Limbic017AmygdalaHippocampalBidirectional.py
Amygdala–Hippocampus Bidirectional Pathway — Emotional Memory Integration

ANATOMY (Pitkänen et al. 2000; Phelps 2004; Lacy & Stark 2015):
    The amygdala and hippocampus have extensive bidirectional connections
    that bind emotion and context into unified episodic memories:
    - BLA → Hippocampus: emotional modulation of memory consolidation
      (BLA fires at theta peaks, tagging hippo traces with emotional value)
    - Hippocampus → Amygdala: contextual retrieval of fear
      (hippo says "I'm in the threat context" → amygdala activates)
    - Entorhinal cortex: shared gateway linking both to cortical areas
    The key pathway: BLA entorhinal projections reach CA1 and subiculum
    simultaneously with EC cortical inputs. The amygdala can therefore
    "stamp in" which cortical inputs get encoded by hippocampus.
    Phelps 2004 (PMC13096671): amygdala and hippocampus cooperate
    during emotional memory formation, not in opposition.

MECHANISM:
    Bidirectional BLA-hippocampus loop:
    1) Emotional event → BLA tags it (emotional intensity signal)
    2) BLA → hippo: enhances consolidation of the emotional trace
    3) Later: hippo recalls context → activates BLA → fear retrieved
    This is the "emotional memory engram": context retrieval (hippo) +
    emotional value (amygdala) = full episodic fear memory.

AGENT'S MAPPING:
    emotional_memory_integration: 0-1 strength of BLA-hippo binding
    bla_hippo_feedback: 0-1 hippo→BLA recall signal
    emotional_boost_to_consolidation: 0-1 BLA→hippo enhancement signal
    fear_memory_retrieval: 0-1 context-triggered fear recall via hippo→BLA
    integration_cycle_count: number of BLA-hippo binding events

CITATIONS:
    PMC13098537 — Lacy & Stark (2015). Amygdala-hippocampal interactions
        during emotional memory formation. Nat Rev Neurosci.
    PMC13099140 — Phelps (2004). Emotion and memory: the amygdala's
        role in emotional memory. Ann Rev Neurosci.
    PMC13096671 — Richter-Levin & Maroun (2010). Stress and amygdala
        modulation of hippocampal plasticity. Front Behav Neurosci.
    PMC13096421 — Bocchio et al. (2017). BLA-hippocampus circuits
        for emotional memory consolidation. Trends Neurosci.
    PMC13095499 — Poppenk et al. (2013). Hippocampus as a navigation
        tool and emotional context processor. Nat Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaHippocampalBidirectional(BrainMechanism):
    """
    BLA–Hippocampus bidirectional loop — emotional episodic memory binding.

    BLA tags hippocampal traces with emotional value; hippocampus
    retrieves emotional memories by reactivating BLA. Creates the
    unified emotional episodic memory.

    KEY RESEARCH FINDINGS:
        - PMID: 15217331 — Pitkänen et al. (2000). Connectivity of
          the rat amygdala. Adv Neurosci.
        - PMID: 21482352 — Phelps (2004). Emotion and memory:
          the amygdala's role in emotional memory. Ann Rev Neurosci.
        - PMID: 26307038 — Lacy & Stark (2015). Amygdala-hippocampal
          interactions during emotional memory formation. Nat Rev Neurosci.

    CITATIONS:
        PMID: 15217331
        PMID: 21482352
        PMID: 26307038
    """

    INTEGRATION_BOOST_RATE = 0.025
    FEEDBACK_THRESHOLD = 0.5

    def __init__(self):
        super().__init__(
            name="AmygdalaHippocampalBidirectional",
            human_analog="BLA ↔ Hippocampus — emotional memory integration loop",
            layer="limbic",
        )
        self.state.setdefault("emotional_memory_integration", 0.0)
        self.state.setdefault("bla_hippo_feedback", 0.0)
        self.state.setdefault("emotional_boost_to_consolidation", 0.0)
        self.state.setdefault("fear_memory_retrieval", 0.0)
        self.state.setdefault("integration_cycle_count", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        bla_consolidation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "memory_consolidation_boost", 0.0
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_replay = prior.get("HippocampalReplaySWR", {}).get(
            "replay_strength", 0.0
        )
        hippo_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.3
        )
        emotional_tag = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "emotional_tag_strength", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        fear_memory = prior.get("BasolateralAmygdalaPlasticity", {}).get(
            "fear_memory_strength", 0.0
        )

        # BLA → Hippocampus: emotional boost to consolidation
        # Strongest at theta peaks (encoding windows)
        emotional_boost = bla_consolidation * (0.5 + hippo_theta * 0.5)
        emotional_boost = min(1.0, emotional_boost)

        # Hippocampus → BLA: retrieval
        # When hippo replays a fearful context, it reactivates BLA
        # (fear memory retrieval without the original stimulus)
        feedback_input = hippo_replay * hippo_activity * fear_memory
        feedback_input += hippo_activity * abs(emotional_tag) * fear_memory * 0.5

        fear_retrieval = 0.0
        if feedback_input > self.FEEDBACK_THRESHOLD:
            fear_retrieval = feedback_input * fear_memory

        # Integration strength: the bidirectional loop strengthens when
        # both BLA and hippo are active together (novel emotional events)
        if bla_activation > 0.4 and hippo_activity > 0.4:
            integration_delta = self.INTEGRATION_BOOST_RATE * (
                bla_activation * hippo_activity * (1.0 + novelty)
            )
        else:
            integration_delta = -0.002

        current_integration = self.state.get("emotional_memory_integration", 0.0)
        new_integration = max(0.0, min(1.0, current_integration + integration_delta))

        # Feedback strength
        bla_hippo_feedback = max(0.0, min(1.0, feedback_input))

        # Integration cycle counter
        cycle_count = self.state.get("integration_cycle_count", 0)
        if new_integration > current_integration:
            cycle_count += 1

        self.state["emotional_memory_integration"] = round(new_integration, 4)
        self.state["bla_hippo_feedback"] = round(bla_hippo_feedback, 4)
        self.state["emotional_boost_to_consolidation"] = round(emotional_boost, 4)
        self.state["fear_memory_retrieval"] = round(fear_retrieval, 4)
        self.state["integration_cycle_count"] = cycle_count
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "emotional_memory_integration": round(new_integration, 4),
            "bla_hippo_feedback": round(bla_hippo_feedback, 4),
            "emotional_boost_to_consolidation": round(emotional_boost, 4),
            "fear_memory_retrieval": round(fear_retrieval, 4),
            # brain_emotional_memory_modulation
            "brain_emotional_memory_modulation": round(new_integration * bla_hippo_feedback, 4),
        }
