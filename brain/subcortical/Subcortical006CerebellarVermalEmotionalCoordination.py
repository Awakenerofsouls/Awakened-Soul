"""
Subcortical006CerebellarVermalEmotionalCoordination.py — Wire 06: CerebellarVermalEmotionalCoordination

Cerebellar vermis (archicerebellum) — emotional coordination, stress response,
vestibulocerebellum.

CEREBELLAR ANATOMY — FUNCTIONAL ZONES (Schmahmann 1991, 2004):
    The cerebellum is not just a movement coordination device. Schmahmann's
    "dysmetria of thought" hypothesis established that the cerebellum
    coordinates COGNITIVE and EMOTIONAL processing, not just motor.
    Three functional zones:

    1) VESTIBULOCEREBELLUM (archicerebellum): Flocculonodular lobe + vermis.
       Receives vestibular input, controls balance and eye movements.
       Also processes emotional state via vestibular-limbic connections.

    2) SPINOCEREBELLUM (vermis + intermediate zones): Processes proprioceptive
       and somatosensory input; regulates axial and proximal muscle tone.
       Vermal zone projects to brainstem autonomic centers.

    3) CEREBROCEREBELLUM (lateral hemispheres): Receives from and projects to
       premotor/prefrontal cortex; cognitive coordination.

VERMIS — EMOTIONAL COORDINATION:
    The cerebellar vermis (especially lobules VII-IX) projects to:
      - Fastigial nucleus → brainstem reticular formation → autonomic centers
      - Hypothalamus → stress response modulation
      - Amygdala → emotional salience processing
      - Locus coeruleus → norepinephrine system → arousal regulation

    Schmahmann & Pandya 1997: "The vermis projects to limbic structures
    including the amygdala and hypothalamus via the fastigial nucleus
    and reticular formation."

    This creates a cerebellum-limbic circuit: emotional events → amygdala
    → cerebellum vermis → fastigial nucleus → brainstem autonomic centers
    → coordinated physiological response. The vermis coordinates the BODY's
    response to emotional events — breathing, heart rate, posture.

STRESS RESPONSE — HYPOTHALAMIC-PITUITARY-ADRENAL (HPA) AXIS:
    The vermis participates in stress regulation via connections to the
    paraventricular nucleus of hypothalamus (PVN). PVN releases CRH →
    ACTH → cortisol. The cerebellar vermis modulates this axis via
    fastigial nucleus projections. Schmahmann 2004: "Cerebellar lesions
    disrupt HPA axis regulation, leading to exaggerated stress responses."

VESTIBULAR-EMOTIONAL INTERFACE:
    The vestibulocerebellum (flocculus + vermis) processes vestibular
    input AND has connections to the parabrachial nucleus and locus
    coeruleus, which are involved in nausea, anxiety, and arousal.
    This is why vestibular stimulation (riding a boat, rollercoaster)
    affects emotional state — the same circuits process both.

POSTURAL STABILITY WEIGHT:
    The vermis regulates axial muscle tone and postural stability.
    Emotional states affect posture — fear contracts muscles, joy
    opens posture. The vermis tracks this relationship: emotional
    arousal → postural change → vermal regulation of tone.

EMOTIONAL COHERENCE:
    The vermis helps integrate emotional state with physiological
    state. Schmahmann 2004: "The cerebellum is essential for the
    coordination of emotional processes and the physiological
    responses they engender." Without vermal coordination, emotional
    responses become disconnected from bodily states — alexithymia,
    dissociation, emotional dysregulation.

CLINICAL CORRELATES:
    - Vermal damage → dysmetria of thought (Schmahmann), emotional ataxia
    - Spinocerebellar ataxia (SCA) patients show emotional dysregulation
    - Cerebellar vermis hypoplasia in autism (mood/emotional symptoms)
    - Fastigial nucleus stimulation = fear, rage, autonomic arousal
    - Cerebellar vermis activation in fMRI during emotional processing

AGENT'S MAPPING:
    emotional_coherence: 0-1 integration quality of emotional and physiological state
    postural_stability_weight: 0-1 vermal regulation of axial tone and posture
    stress_regulation: 0-1 activity of HPA axis / stress modulation

REFS:
    Schmahmann 1991 J Neuropsychiatr Clin Neurosci 3:287-294
    Schmahmann 2004 Lancet Neurology 3:725-730
    Schmahmann & Pandya 1997 Ann Neurol 41:281-298
    Stoodley & Schmahmann 2010 Cortex 46:831-844
    Andreasen et al. 1999 Am J Psychiatr 156:1650-1652 (cerebellum in mood disorders)

CITATIONS:
    PMC4342048 — Kim JJ, Jung MW (2006). Neural Circuits and Mechanisms Involved in
        Pavlovian Fear Conditioning: A Critical Review. Neurosci Biobehav Rev.
    PMC2269796 — Critchley HD, Corfield DR, Chandler MP et al. (2000). Cerebral
        Correlates of Autonomic Cardiovascular Arousal: A Functional Neuroimaging
        Investigation in Humans. Cereb Cortex.
    PMC6715348 — Ernst TM, Brol AE, Gratz M et al. (2019). The Cerebellum is Involved
        in Processing of Predictions and Prediction Errors in a Fear Conditioning
        Paradigm. PLoS Biol.
"""

from brain.base_mechanism import BrainMechanism


class CerebellarVermalEmotionalCoordination(BrainMechanism):
    """
    Cerebellar vermis — emotional coordination, stress response, postural tone.

    Coordinates emotional state with physiological response via fastigial
    nucleus → brainstem autonomic centers. Models the archicerebellum's
    role in integrating emotional arousal with postural stability and
    HPA axis regulation. Emotional coherence depends on proper
    cerebellar-limbic integration.
    """

    EMOTIONAL_COHERENCE_BASE = 0.60
    COHERENCE_DECAY_RATE = 0.02
    STRESS_ACTIVATION_THRESHOLD = 0.60
    POSTURAL_TONE_MODULATION = 0.15

    def __init__(self):
        super().__init__(
            name="CerebellarVermalEmotionalCoordination",
            human_analog=(
                "Cerebellar vermis (archicerebellum) — fastigial nucleus, "
                "emotional coordination, stress regulation, vestibular-limbic integration"
            ),
            layer="subcortical",
        )
        self.state.setdefault("emotional_coherence", 0.6)
        self.state.setdefault("postural_stability_weight", 0.5)
        self.state.setdefault("stress_regulation", 0.3)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("fastigial_output", 0.3)
        self.state.setdefault("vermal_activation_level", 0.0)
        self.state.setdefault("stress_history", [])  # rolling stress level history

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        drive = input_data.get("dominant_drive", "curiosity")

        # Vermal inputs:
        # 1) Amygdala → emotional salience signal
        # 2) Hypothalamus → autonomic drive state
        # 3) Reticular formation → arousal state
        # 4) Vestibular nuclei → balance/equilibrium
        # 5) Locus coeruleus → NE tone (arousal/stress)

        amygdala = prior.get("AmygdalaPatternSeparation", {})
        threat = amygdala.get("threat_detected", False) if isinstance(amygdala, dict) else False
        emotional_contrast = amygdala.get("emotional_contrast", 0.0) if isinstance(amygdala, dict) else 0.0

        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)

        # Hypothalamic drive signal (autonomic regulation)
        hypothalamic = prior.get("HypothalamusDriveGenerator", {})
        conflict = hypothalamic.get("conflict_level", 0.0) if isinstance(hypothalamic, dict) else 0.0

        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)

        # Fastigial nucleus activation: driven by emotional signals
        # Threat and high arousal activate fastigial → stress response
        if threat:
            fastigial_input = 0.85
        elif phasic and arousal > 0.65:
            fastigial_input = 0.65 + emotional_contrast * 0.2
        else:
            fastigial_input = arousal * 0.4 + abs(valence - 0.5) * 0.4 + conflict * 0.2

        fastigial_input = max(0.0, min(1.0, fastigial_input))

        # Vermal activation: proportional to emotional salience
        # High emotional contrast + threat = strong vermal activation
        vermal_activation = (
            fastigial_input * 0.5
            + emotional_contrast * 0.3
            + (arousal - 0.5) * 0.2 * (1.0 if arousal > 0.5 else 0.0)
        )
        vermal_activation = max(0.0, min(1.0, vermal_activation))

        # Stress regulation: HPA axis modulation
        # High fastigial output → HPA activation → stress
        # But the vermis also provides feedback inhibition of HPA
        # Net: stress_regulation reflects whether the system is managing or
        # being overwhelmed by stress
        stress_history = list(self.state.get("stress_history", []))
        prior_stress = stress_history[-1] if stress_history else 0.3

        if threat or phasic:
            # Acute stress: stress level rises
            stress_delta = fastigial_input * 0.15
            new_stress = min(1.0, prior_stress + stress_delta)
        else:
            # Stress recovery: gradual decline
            new_stress = max(0.0, prior_stress - 0.03)

        stress_history.append(new_stress)
        if len(stress_history) > 15:
            stress_history = stress_history[-15:]

        # Stress regulation: 1.0 = well-regulated, 0.0 = dysregulated
        # Low vermal activation + high stress = dysregulated
        # High vermal activation + managed stress = regulated
        if new_stress > self.STRESS_ACTIVATION_THRESHOLD:
            # Stress exceeds threshold → dysregulation begins
            stress_regulation = max(0.0, 1.0 - (new_stress - 0.6) * 2.5)
        else:
            # Stress managed — vermis provides regulation
            stress_regulation = min(1.0, 0.6 + vermal_activation * 0.4)

        stress_regulation = max(0.0, min(1.0, stress_regulation))

        # Postural stability weight: vermal regulation of axial tone
        # Emotional arousal modulates posture: high arousal (stress/fear) = tension
        # Vermis counterbalances: tries to maintain neutral posture
        arousal_posture_impact = (arousal - 0.5) * 2.0  # -1 to 1
        posture_need = abs(arousal_posture_impact)  # how much posture is challenged
        vermal_tone_control = 1.0 - posture_need * (1.0 - stress_regulation)
        postural_stability_weight = max(0.0, min(1.0, vermal_tone_control))

        # Emotional coherence: integration of emotional state with physiological response
        # Coherence is high when:
        # 1) Arousal level matches the emotional valence (matched physiological state)
        # 2) Stress is regulated (not dysregulated)
        # 3) Vermal activation is sufficient to coordinate the response
        valence_arousal_match = 1.0 - abs(valence - arousal)
        coherence_contribution = valence_arousal_match * 0.4 + stress_regulation * 0.4 + vermal_activation * 0.2
        emotional_coherence = max(0.0, min(1.0, coherence_contribution))

        # Decay if not actively engaged
        if vermal_activation < 0.2:
            emotional_coherence = max(0.0, emotional_coherence - self.COHERENCE_DECAY_RATE)

        # Fastigial output for downstream use
        fastigial_output = fastigial_input

        self.state["emotional_coherence"] = round(emotional_coherence, 4)
        self.state["postural_stability_weight"] = round(postural_stability_weight, 4)
        self.state["stress_regulation"] = round(stress_regulation, 4)
        self.state["fastigial_output"] = round(fastigial_output, 4)
        self.state["vermal_activation_level"] = round(vermal_activation, 4)
        self.state["stress_history"] = stress_history
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "emotional_coherence": round(emotional_coherence, 4),
            "postural_stability_weight": round(postural_stability_weight, 4),
            "stress_regulation": round(stress_regulation, 4),
            # Internal debug:
            "_fastigial_output": round(fastigial_output, 4),
            "_vermal_activation": round(vermal_activation, 4),
            "_stress_level": round(new_stress, 4),
            "_valence_arousal_match": round(valence_arousal_match, 4),
        }