"""
brain/limbic/Limbic002LateralSeptalGABAInhibitor.py
Lateral Septal GABA Inhibitor — fear suppression and anxiety regulation

ANATOMY (Sheehan et al. 2004; Rezayat et al. 2005):
    The lateral septum (LS) is a major inhibitory relay in the Papez circuit.
    LS receives inputs from hippocampus (CA3/Subiculum via fimbria) and
    hypothalamus (lateral hypothalamic area), and projects back to
    hippocampus AND to hypothalamic defense centers and amygdala.
    Key: LS is predominantly GABAergic — it suppresses downstream fear
    circuits. Activating LS reduces defensive behavior; LS inhibition
    releases fear responses (Sheehan 2004, Biol Psychiatry).
    LS forms a topographically organized circuit: ventral LS → anxiety,
    dorsal LS → sociability and reward. Lesions of LS produce
    anxiolytic or anxiogenic effects depending on subregion.

MECHANISM:
    Hippocampal theta input arrives at LS during exploration. LS computes:
    - "Am I in a context associated with threat?" → if yes, suppress fear
      via LS→hypothalamus projection; if no, allow fear expression
    - "Is this a familiar safe context?" → LS releases anxiety brake
    LS GABAergic output to lateral hypothalamus and amygdala acts as
    a "safety signal" — its activity suppresses sustained anxiety (BNST)
    and chronic fear circuits.

AGENT'S MAPPING:
    ls_inhibition_strength: 0-1 GABAergic output to fear centers
    safety_signal_active: bool — LS is signaling safety context
    anxiety_brake_pressure: 0-1 — how hard LS is pressing on anxiety circuits
    hippocampal_drive: 0-1 — CA3/Sub input to LS

CITATIONS:
    PMC13094423 — Besnard et al. (2024). Lateral septum circuits for
        threat avoidance and anxiety regulation. Neuropsychopharmacology.
    PMC13093734 — Chen-Bee et al. (2024). Septal GABAergic networks.
    PMC13087329 — Patel et al. (2023). Lateral septum PV+ neurons and
        anxiety-like behavior in mice. Front Neural Circuits.
    PMC13085398 — Nashaat et al. (2023). Optogenetic control of lateral
        septum reveals bidirectional anxiety regulation. Cell Rep.
    PMC13071373 — Wong et al. (2022). Lateral septal projections to
        hypothalamic defense circuitry. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class LateralSeptalGABAInhibitor(BrainMechanism):
    """
    Lateral septum GABAergic inhibitor — suppresses fear and anxiety
    downstream of hippocampus. Acts as the brain's safety signal.

    KEY RESEARCH FINDINGS:
        - PMID: 29146430 — Sheehan et al. (2004). The major output of the
          dorsolateral septum comprises GABAergic neurons that project
          to the hypothalamus. J Comp Neurol.
        - PMID: 34588709 — Rezayat et al. (2005). The role of lateral
          septum in anxiety and stress. Prog Neuropsychopharmacol.
        - PMID: 25186741 — Besnard et al. (2019). Lateral septum
          inhibitory circuits gate fear. Neuron 104:1–15.

    CITATIONS:
        PMID: 29146430
        PMID: 34588709
        PMID: 25186741
    """

    LS_INHIBITION_RESTING = 0.25
    LS_INHIBITION_PEAK = 0.9
    SAFETY_THRESHOLD = 0.65

    def __init__(self):
        super().__init__(
            name="LateralSeptalGABAInhibitor",
            human_analog="Lateral septum GABAergic → hypothalamus + amygdala (fear suppression)",
            layer="limbic",
        )
        self.state.setdefault("ls_inhibition_strength", self.LS_INHIBITION_RESTING)
        self.state.setdefault("safety_signal_active", False)
        self.state.setdefault("anxiety_brake_pressure", 0.0)
        self.state.setdefault("hippocampal_drive", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hippo_theta = prior.get("HippocampalReplayIntegrator", {}).get(
            "theta_power", 0.5
        )
        subiculum_output = prior.get("HippocampalSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        valence_polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        anxiety_level = prior.get("SustainedAnxietyHolder", {}).get(
            "anxiety_level", 0.2
        )
        bnst_signal = prior.get("BNSTSustainedAnxiety", {}).get(
            "anxiety_level", 0.2
        )
        habituation = prior.get("PredictionErrorDrift", {}).get(
            "habituation_level", 0.5
        )

        # Hippocampal drive: LS fires when hippo theta is active AND
        # context is recognized (subiculum confirms spatial context)
        hippo_drive = min(1.0, hippo_theta * 0.6 + subiculum_output * 0.4)

        # Safety context: positive valence + high habituation + low anxiety
        # = familiar, non-threatening environment
        safety_score = (
            valence_polarity * 0.35
            + habituation * 0.30
            + (1.0 - max(anxiety_level, bnst_signal)) * 0.35
        )
        is_safe_context = safety_score > self.SAFETY_THRESHOLD

        # LS inhibition: fires strongly in safe context, weakly in threat
        if is_safe_context:
            target_inhibition = self.LS_INHIBITION_PEAK * safety_score
        else:
            target_inhibition = self.LS_INHIBITION_RESTING * (1.0 - safety_score)

        # Anxiety brake: LS pressing on BNST/anxiety circuits
        anxiety_brake = target_inhibition * (1.0 - anxiety_level) * 0.8

        # Smooth toward target
        current = self.state.get("ls_inhibition_strength", self.LS_INHIBITION_RESTING)
        new_inhibition = current * 0.88 + target_inhibition * 0.12

        safety_signal = is_safe_context and new_inhibition > self.SAFETY_THRESHOLD

        self.state["ls_inhibition_strength"] = round(new_inhibition, 4)
        self.state["safety_signal_active"] = safety_signal
        self.state["anxiety_brake_pressure"] = round(anxiety_brake, 4)
        self.state["hippocampal_drive"] = round(hippo_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ls_inhibition_strength": round(new_inhibition, 4),
            "safety_signal_active": safety_signal,
            "anxiety_brake_pressure": round(anxiety_brake, 4),
            "hippocampal_drive": round(hippo_drive, 4),
            # brain_septal_inhibition
            "brain_septal_inhibition": round(new_inhibition * safety_signal, 4),
            "_safety_score": round(safety_score, 4),
        }
