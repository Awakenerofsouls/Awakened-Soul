"""
Subcortical010DeepCerebellarNucleiOutput.py — Wire 10: CerebellarOutputGate

Deep Cerebellar Nuclei (DCN) collective output mechanism.

Models the integrated output of all four deep cerebellar nuclei as a
single cerebellar_output_signal, with separate motor and cognitive
command strength outputs reflecting their distinct downstream targets.

Neural analog: Deep Cerebellar Nuclei (DCN) — four nuclei embedded in
the cerebellar white matter, receiving Purkinje cell inhibition from all
zones of cerebellar cortex and sending efferent projections outward:

1. FASTIGIAL NUCLEUS (medial):
   - Receives: vermal zone Purkinje cells
   - Projects: to spinal cord (vestibulospinal, reticulospinal tracts)
   - Function: axial/postural control, whole-body coordination
   - Efferent: primarily to brainstem reticular formation

2. GLOBOSE NUCLEUS (interposed-anterior, medial):
   - Receives: paravermal zone Purkinje cells
   - Projects: to red nucleus (magnocellular division)
   - Function: interlimb coordination, error correction
   - Efferent: rubropsinal tract → contralateral limb control

3. EMBOLIFORM NUCLEUS (interposed-posterior, lateral):
   - Receives: paravermal/lateral boundary Purkinje cells
   - Projects: to red nucleus (parvocellular division) → thalamus VL
   - Function: precise timing of distal limb movements

4. DENTATE NUCLEUS (lateral, largest):
   - Receives: lateral hemispheric zone Purkinje cells
   - Projects: to VL/VA thalamus → motor and prefrontal cortex
   - Function: motor planning, cognitive sequencing, timing
   - Efferent: superior cerebellar peduncle (see Subcortical011)

Purves et al. Neuroscience 5th ed. 2018 describes DCN as "the sole
output neurons of the cerebellum" — all motor and cognitive cerebellar
signals pass through these nuclei before entering the SCP.

DCN neurons are intrinsically auto-rhythmic: even after Purkinje cell
inhibition is removed, DCN neurons fire spontaneously at ~20-40 Hz.
This intrinsic pacemaking provides the cerebellar clock's baseline
timing signal. Purkinje inhibition modulates this baseline to encode
movement error and timing adjustments.

This mechanism aggregates DCN output from all four nuclei:
- cerebellar_output_signal: the unified cerebellar command
- motor_command_strength: fastigial + globose + emboliform contribution
- cognitive_command_strength: dentate contribution to prefrontal loops

REFS:
- Purves et al. Neuroscience 5th ed. 2018, Oxford UP (DCN anatomy)
- Ito 2008 Scholarpedia 3:1410
- Stoodley & Schmahmann 2009 Cortex 45:975-991
- Apps & Garwicz 2005 Physiol Rev 85:1151-1174
- Ramnani 2006 Nat Rev Neurosci 7:511-522

CITATIONS:
    PMC8273235 — Kakei S, Manto M, Tanaka H et al. (2021). Pathophysiology of
        Cerebellar Tremor: The Forward Model-Related Tremor. Front Neurol.
    PMC10556200 — Fanning A, Kuo SH (2024). Clinical Heterogeneity of Essential
        Tremor: Understanding Neural Substrates of Action Tremor Subtypes.
    PMC8513160 — Heiney SA, Wojaczynski GJ, Medina JF (2021). Action-based Organization
        of a Cerebellar Module Specialized for Predictive Control. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class CerebellarOutputGate(BrainMechanism):
    """
    Deep Cerebellar Nuclei collective output gateway.

    Integrates output from all four DCN nuclei:
    - Fastigial: axial/postural
    - Globose: interlimb coordination
    - Emboliform: precise timing
    - Dentate: cognitive/motor planning

    Outputs:
    - cerebellar_output_signal: unified output
    - motor_command_strength: motor-channel DCN contribution
    - cognitive_command_strength: dentate-channel DCN contribution
    """

    DCN_INTRINSIC_FREQ = 0.65  # Baseline DCN firing rate
    PURKINJE_INHIBITION_GAIN = 0.7
    MOTOR_COGNITIVE_MIX = 0.55  # Baseline motor proportion

    def __init__(self):
        super().__init__(
            name="CerebellarOutputGate",
            human_analog="Deep Cerebellar Nuclei (fastigial + globose + emboliform + dentate)",
            layer="subcortical",
        )
        self.state.setdefault("cerebellar_output_signal", 0.6)
        self.state.setdefault("motor_command_strength", 0.5)
        self.state.setdefault("cognitive_command_strength", 0.5)
        self.state.setdefault("purkinje_inhibition", 0.0)
        self.state.setdefault("dcn_baseline", self.DCN_INTRINSIC_FREQ)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        paraverm_data = prior.get("LimbCoordinationDrift", {})
        lateral_data = prior.get("CognitiveTimingPrecision", {})
        split_data = prior.get("DentateOutputSplit", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        purkinje_inhibition = input_data.get("purkinje_inhibition", 0.0)
        cerebellar_input = input_data.get("cerebellar_input_strength", 0.6)
        motor_active = input_data.get("motor_active", False)
        cognitive_load = input_data.get("cognitive_load", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # From prior mechanisms
        coordination_weight = paraverm_data.get("coordination_weight", 0.8)
        timing_precision = lateral_data.get("timing_precision", 0.85)
        cognitive_output = split_data.get("cognitive_output", 0.5)
        motor_output = split_data.get("motor_output", 0.5)

        # --- Purkinje inhibition effect ---
        # Purkinje cells fire at ~1-10 Hz during movement, tonically inhibiting DCN.
        # Error signals increase Purkinje firing → stronger inhibition → DCN
        # output suppressed = less commanded movement. Purkinje pause (climbing
        # fiber burst) → disinhibition → DCN fires strongly = movement correction.
        self.state["purkinje_inhibition"] = purkinje_inhibition
        inhibition_effect = purkinje_inhibition * self.PURKINJE_INHIBITION_GAIN

        # --- Motor command strength (fastigial + globose + emboliform) ---
        # These nuclei drive motor output: postural, limb, precise movement
        fastigial_contribution = coordination_weight * 0.35
        globose_contribution = coordination_weight * timing_precision * 0.35
        emboliform_contribution = (
            (0.6 if motor_active else 0.3) * timing_precision * 0.3
        )
        motor_base = fastigial_contribution + globose_contribution + emboliform_contribution

        # Arousal modulation on motor command
        motor_arousal = 1.0 - abs(arousal - 0.6) * 0.4
        motor_raw = motor_base * motor_arousal + motor_output * 0.25
        motor_command_strength = max(0.0, min(1.0, motor_raw))

        # --- Cognitive command strength (dentate) ---
        # Dentate drives cognitive sequencing, timing predictions, planning
        dentate_cognitive = (
            cognitive_output * 0.4
            + timing_precision * 0.3
            + cognitive_load * 0.3
        )
        # Dentate suppressed by strong motor commands (competition for thalamic channel)
        dentate_suppression = motor_command_strength * 0.2 if motor_active else 0.0
        cognitive_raw = dentate_cognitive - dentate_suppression
        cognitive_command_strength = max(0.0, min(1.0, cognitive_raw))

        # --- Unified cerebellar output signal ---
        # DCN intrinsic pacemaking + cerebellar_input - Purkinje inhibition
        dcn_intrinsic = self.state["dcn_baseline"]
        cerebellar_output_signal = (
            dcn_intrinsic * 0.3
            + cerebellar_input * 0.4
            - inhibition_effect * 0.3
        )
        cerebellar_output_signal = max(0.0, min(1.0, cerebellar_output_signal))

        # --- DCN baseline update (slow plasticity) ---
        # DCN baseline slowly shifts toward the commanded output (intrinsic adaptation)
        new_baseline = (
            self.DCN_INTRINSIC_FREQ * 0.8
            + cerebellar_output_signal * 0.2
        )
        self.state["dcn_baseline"] = round(new_baseline, 4)

        self.state["cerebellar_output_signal"] = round(cerebellar_output_signal, 4)
        self.state["motor_command_strength"] = round(motor_command_strength, 4)
        self.state["cognitive_command_strength"] = round(cognitive_command_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cerebellar_output_signal": round(cerebellar_output_signal, 4),
            "motor_command_strength": round(motor_command_strength, 4),
            "cognitive_command_strength": round(cognitive_command_strength, 4),
        }
