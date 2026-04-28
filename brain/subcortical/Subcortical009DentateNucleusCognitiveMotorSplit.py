"""
Subcortical009DentateNucleusCognitiveMotorSplit.py — Wire 9: DentateOutputSplit

Dentate nucleus cognitive/motor output split mechanism.

Maintains parallel cognitive and motor output channels from the cerebellar
dentate nucleus, tracking the output split ratio which reflects how much
dentate output is directed to prefrontal cortex (cognitive) vs motor cortex
(motor) based on the prevailing input context.

Neural analog: Dentate nucleus of the cerebellum — the largest deep
cerebellar nucleus. Ramnani 2006 (Nat Rev Neurosci 7:511-522) provided
the definitive anatomical mapping:

1. Dentate nucleus is functionally divided:
   - Ventromedial (small-celled) portion → ventral lateral thalamic
     nucleus → prefrontal cortex (BA46, 9) → cognitive operations
   - Dorsolateral (large-celled) portion → motor thalamus → motor
     cortex (M1, premotor) → motor operations

2. This anatomical split mirrors the cortical hemispheric zones:
   - Lateral cerebellar cortex → dentate motor portion → motor output
   - Medial cerebellar cortex → dentate cognitive portion → prefrontal

3. Ito 2008 (Scholarpedia) confirmed that "the dentate nucleus receives
   input from the cerebellar cortex and sends output to the thalamus"
   and that "the ventral dentate (cognitively-associated portion) is
   particularly developed in humans and non-human primates."

4. Strick et al. 2009 demonstrated single-neuron firing in dentate
   during purely cognitive tasks — no movement involved — confirming
   the cognitive output channel fires independently of motor commands.

5. The split is dynamic: during active movement execution, motor
   output dominates. During cognitive planning/delayed intervals,
   cognitive output dominates. Ramnani & Passingham 2006 showed the
   proportion shifts with task demands.

This mechanism tracks the split ratio based on:
- Cognitive input signals (working memory load, sequence planning)
- Motor input signals (active movement, proprioceptive feedback)
- Arousal state (moderate arousal → balanced split; high arousal → motor bias)

REFS:
- Ramnani 2006 Nat Rev Neurosci 7:511-522
  "The primate cerebellar sensory-motor and cognitive circuitry"
- Ramnani & Passingham 2006 J Neurosci 21:525-533
- Ito 2008 Scholarpedia 3:1410
- Strick et al. 2009 Nat Rev Neurosci 10:264-270
- Purves et al. Neuroscience 5th ed. 2018

CITATIONS:
    PMC7688491 — Thanawalla AR, Chen AI, Azim E (2020). The Cerebellar Nuclei and
        Dexterous Limb Movements. J Neurosci.
    PMC8062874 — Amore G, Spoto G, Ieni A et al. (2021). A Focus on the Cerebellum:
        From Embryogenesis to an Age-Related Clinical Perspective. Cerebellum.
    PMC8273235 — Kakei S, Manto M, Tanaka H et al. (2021). Pathophysiology of
        Cerebellar Tremor: The Forward Model-Related Tremor. Front Neurol.
"""

from brain.base_mechanism import BrainMechanism


class DentateOutputSplit(BrainMechanism):
    """
    Dentate nucleus cognitive/motor output split tracker.

    Models the functional split in dentate nucleus between:
    - cognitive_output: ventromedial dentate → prefrontal thalamus
    - motor_output: dorsolateral dentate → motor thalamus

    The split ratio shifts dynamically based on input context.
    Tracks output_split_ratio over time for state persistence.
    """

    SPLIT_STABILITY = 0.08
    MOTOR_BIAS_AROUSAL = 0.65
    COGNITIVE_BIAS_LOAD = 0.6

    def __init__(self):
        super().__init__(
            name="DentateOutputSplit",
            human_analog="Cerebellar dentate nucleus (ventromedial/cognitive + dorsolateral/motor)",
            layer="subcortical",
        )
        self.state.setdefault("cognitive_output", 0.5)
        self.state.setdefault("motor_output", 0.5)
        self.state.setdefault("output_split_ratio", 0.5)
        self.state.setdefault("last_motor_dominance", 0.0)
        self.state.setdefault("last_cognitive_dominance", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        lateral_data = prior.get("CognitiveTimingPrecision", {})
        limb_data = prior.get("LimbCoordinationDrift", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        cognitive_load = input_data.get("cognitive_load", 0.5)
        sequence_planning = input_data.get("sequence_planning_active", False)
        motor_active = input_data.get("motor_active", False)
        movement_onset = input_data.get("movement_onset", False)
        limb_coherence = limb_data.get("limb_coherence", 0.8)
        timing_precision = lateral_data.get("timing_precision", 0.85)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Cognitive output channel ---
        # Driven by: cognitive_load, sequence_planning, timing_precision
        cognitive_raw = (
            cognitive_load * 0.35
            + (0.3 if sequence_planning else 0.0)
            + timing_precision * 0.3
            + (1.0 - limb_coherence) * 0.05  # Coordination difficulty → cognitive recruitment
        )
        cognitive_raw = max(0.0, min(1.0, cognitive_raw))

        # --- Motor output channel ---
        # Driven by: motor_active, movement_onset, limb_coherence
        motor_raw = (
            (0.7 if movement_onset else 0.0)
            + (0.3 if motor_active else 0.0)
            + limb_coherence * 0.25
        )
        motor_raw = max(0.0, min(1.0, motor_raw))

        # --- Split ratio: cognitive / (cognitive + motor) ---
        total = cognitive_raw + motor_raw
        if total > 0.0:
            split_ratio = cognitive_raw / total
        else:
            split_ratio = 0.5  # Balanced default

        # Arousal modulates split ratio
        # High arousal (> 0.65) biases toward motor output
        # Moderate arousal → more cognitive contribution
        if arousal > self.MOTOR_BIAS_AROUSAL:
            split_ratio = max(0.0, split_ratio - (arousal - self.MOTOR_BIAS_AROUSAL) * 0.4)
        elif arousal < 0.4:
            # Low arousal: motor fades faster than cognitive
            split_ratio = min(1.0, split_ratio + 0.15)

        # Smooth split ratio with temporal stability (prevents rapid oscillation)
        prev_ratio = self.state["output_split_ratio"]
        new_ratio = prev_ratio + self.SPLIT_STABILITY * (split_ratio - prev_ratio)

        # --- Apply split to outputs ---
        # Cognitive output is weighted by split ratio
        cognitive_output = cognitive_raw * new_ratio
        # Motor output is weighted by (1 - split ratio)
        motor_output = motor_raw * (1.0 - new_ratio)

        self.state["cognitive_output"] = round(cognitive_output, 4)
        self.state["motor_output"] = round(motor_output, 4)
        self.state["output_split_ratio"] = round(new_ratio, 4)
        self.state["last_motor_dominance"] = round(float(motor_raw > cognitive_raw), 4)
        self.state["last_cognitive_dominance"] = round(float(cognitive_raw > motor_raw), 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cognitive_output": round(cognitive_output, 4),
            "motor_output": round(motor_output, 4),
            "output_split_ratio": round(new_ratio, 4),
        }
