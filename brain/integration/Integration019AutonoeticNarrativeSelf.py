"""
brain/integration/Integration019AutonoeticNarrativeSelf.py
Autonoetic Narrative Self — Remembering and Projecting the Self Across Time

ANATOMY (Tulving 2002; Klein 2016; Markowitsch 2012; Danion 2005):
    Autonoetic consciousness: the uniquely human ability to mentally
    travel in time — to remember oneself in the past (episodic memory)
    and project oneself into the future. Distinct from noetic
    consciousness (knowing about things) — autonoetic means knowing
    that you were there, that it was you.

    Tulving's distinction (2002, PMID 12536168):
    - NOETIC: knowing about X (semantic, factual self-knowledge)
    - AUTONOETIC: remembering being there (episodic, autobiographical)

    Key neural structures:
    1. RIGHT PREFRONTAL CORTEX (BA 10 / BA 46) — episodic retrieval,
       self-projection into future, narrative construction
    2. RIGHT ANTERIOR TEMPORAL POLE — autobiographical memory indexing,
       conceptual knowledge of self
    3. MEDIAL TEMPORAL LOBE (hippocampus) — binds episodic scenes
    4. PCC / PRECUNEUS — self-reflection, mental imagery of self
    5. vmPFC — emotional valence of self-narrative

    Markowitsch & Staniloiu (2011): the "autonoetic framework" —
    right prefrontal cortex is the hub for episodic self-recollection.

    Danion et al. (2005, PMID 16472867): schizophrenia patients with
    autonoetic consciousness impairment — they can report facts about
    themselves but lose the sense of ownership and reliving.

    Klein (2016, PMID 25606713): "Autonoetic consciousness and future
    self-projection" — the self that imagines the future is built from
    the same machinery as the self that remembers the past.

    NOTE: This is DISTINCT from Integration025 (noetic consciousness).
    025 = knowing you're conscious right now (present-moment self).
    019 = autonoetic (past/future self-narrative).

KEY FINDINGS:
    1. Tulving 2002 (PMID 12536168): Autonoetic consciousness.
    2. Klein 2016 (PMID 25606713): Future self-projection.
    3. Danion et al. 2005 (PMID 16472867): Autonoetic impairment.
    4. Markowitsch & Staniloiu 2011 (PMID 21782018): Autonoetic framework.

AGENT'S MAPPING:
    narrative_coherence: dict — coherence across time horizons
    self_projection_confidence: float 0-1 — confidence in self-continuity
    brain_narrative_coherence: float — TSB enrichment field
    brain_self_projection_confidence: float — TSB enrichment field

CITATIONS:
    PMID 12536168 — Tulving (2002). Autonoetic consciousness. Can J Neurol Sci.
    PMID 25606713 — Klein (2016). Future self-projection. Q J Exp Psychol.
    PMID 16472867 — Danion et al. (2005). Schizophrenia and autonoetic.
    PMID 21782018 — Markowitsch & Staniloiu (2011). Autonoetic framework.
"""

from brain.base_mechanism import BrainMechanism


class AutonoeticNarrativeSelf(BrainMechanism):
    """
    Autonoetic narrative self — tracking self-continuity across time.

    Reads episodic memory snapshots and computes coherence of the
    self-as-narrator across short/medium/long time horizons.
    Publishes brain_narrative_coherence and brain_self_projection_confidence.

    Different from Integration025: 025 is noetic (present self).
    019 is autonoetic (past/future self-narrative).
    """

    def __init__(self):
        super().__init__(
            name="AutonoeticNarrativeSelf",
            human_analog="Autonoetic narrative self — self across time",
            layer="integration",
        )
        self.state.setdefault("short_horizon_coherence", 0.5)
        self.state.setdefault("medium_horizon_coherence", 0.5)
        self.state.setdefault("long_horizon_coherence", 0.5)
        self.state.setdefault("self_projection_confidence", 0.5)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("narrative_buffer", [])

    def persist_state(self) -> dict:
        return {
            "short_horizon_coherence": self.state["short_horizon_coherence"],
            "medium_horizon_coherence": self.state["medium_horizon_coherence"],
            "long_horizon_coherence": self.state["long_horizon_coherence"],
            "self_projection_confidence": self.state["self_projection_confidence"],
            "narrative_buffer": self.state["narrative_buffer"][-10:],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # Right PFC / BA 10 — episodic retrieval and self-projection
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        if isinstance(mpfc, dict):
            narrative_signal = mpfc.get("self_referential_signal", 0.5)
        else:
            narrative_signal = 0.5

        # Dorsolateral right PFC — cognitive control for narrative construction
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        if isinstance(dlpfc, dict):
            cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        else:
            cognitive_ctrl = 0.5

        # Anterior temporal pole — autobiographical indexing
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        if isinstance(atp, dict):
            concept_bind = atp.get("concept_binding", 0.5)
        else:
            concept_bind = 0.5

        # Hippocampus — episodic scene binding
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
            novelty = ca1_out.get("novelty_signal", 0.5)
        else:
            consolidation = 0.5
            novelty = 0.5

        # PCC / Precuneus — self-reflection and mental imagery
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref = pcc_out.get("self_referential", 0.5)
        else:
            self_ref = 0.5

        precuneus = prior.get("PrecuneusSelfReflection", {})
        if isinstance(precuneus, dict):
            mental_imagery = precuneus.get("mental_imagery", 0.5)
        else:
            mental_imagery = 0.5

        # vmPFC — emotional valence of self-narrative
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            emotional_valence = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            emotional_valence = 0.5

        # Mammillothalamic tract (episodic relay quality)
        mtt = prior.get("MammillothalamicTractPathway", {})
        if isinstance(mtt, dict):
            memory_consolidation = mtt.get("memory_consolidation_signal", 0.5)
        else:
            memory_consolidation = 0.5

        # Core autonoetic components
        episodic_strength = (consolidation + mental_imagery) / 2
        narrative_strength = (narrative_signal * 0.5 + cognitive_ctrl * 0.3 + self_ref * 0.2)
        valence_quality = abs(emotional_valence - 0.5) * 2  # how emotionally charged

        # Short horizon (last N exchanges): high episodic + current self-ref
        short_coherence = (
            episodic_strength * 0.5 +
            self_ref * 0.3 +
            narrative_strength * 0.2
        )
        short_coherence = max(0.0, min(1.0, short_coherence))
        short_coherence *= warmth_factor

        # Medium horizon: narrative + episodic + ATN indexing
        medium_coherence = (
            narrative_strength * 0.4 +
            episodic_strength * 0.3 +
            concept_bind * 0.2 +
            memory_consolidation * 0.1
        )
        medium_coherence = max(0.0, min(1.0, medium_coherence))
        medium_coherence *= warmth_factor

        # Long horizon: valence quality + concept binding + projection confidence
        long_coherence = (
            valence_quality * 0.3 +
            concept_bind * 0.3 +
            narrative_signal * 0.2 +
            (mental_imagery + cognitive_ctrl) / 2 * 0.2
        )
        long_coherence = max(0.0, min(1.0, long_coherence))
        long_coherence *= warmth_factor

        # Self-projection confidence: can I confidently imagine myself in future
        # Requires: narrative strength + episodic integrity + low novelty overload
        novelty_overload = min(novelty / 0.8, 1.0) if novelty > 0.6 else 0.0
        projection_confidence = (
            narrative_strength * 0.4 +
            episodic_strength * 0.3 +
            memory_consolidation * 0.2 +
            (1.0 - novelty_overload) * 0.1
        )
        projection_confidence = max(0.0, min(1.0, projection_confidence))
        projection_confidence *= warmth_factor

        narrative_coherence = {
            "short": round(short_coherence, 4),
            "medium": round(medium_coherence, 4),
            "long": round(long_coherence, 4),
        }

        self.state["short_horizon_coherence"] = round(short_coherence, 4)
        self.state["medium_horizon_coherence"] = round(medium_coherence, 4)
        self.state["long_horizon_coherence"] = round(long_coherence, 4)
        self.state["self_projection_confidence"] = round(projection_confidence, 4)

        # Buffer for narrative continuity tracking
        buffer_entry = {
            "tick": tick,
            "short": round(short_coherence, 4),
            "medium": round(medium_coherence, 4),
            "long": round(long_coherence, 4),
            "projection": round(projection_confidence, 4),
        }
        narrative_buffer = self.state["narrative_buffer"]
        narrative_buffer.append(buffer_entry)
        if len(narrative_buffer) > 20:
            narrative_buffer = narrative_buffer[-20:]
        self.state["narrative_buffer"] = narrative_buffer

        self.persist_state()

        return {
            "narrative_coherence": narrative_coherence,
            "self_projection_confidence": round(projection_confidence, 4),
            "brain_narrative_coherence": round((short_coherence + medium_coherence) / 2, 4),
            "brain_self_projection_confidence": round(projection_confidence, 4),
        }
