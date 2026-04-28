"""
Subcortical012MiddleCerebellarPeduncleInput.py — Wire 12: PontocerebellarInput

Middle Cerebellar Peduncle (MCP) pontocerebellar input mechanism.

Models the MCP as the major cerebellar input pathway carrying
information from the pontine nuclei (and ultimately from cerebral
cortex) into the cerebellar cortex. Computes pontine_input_strength,
motor_cortex_relay quality, and granule_cell_activation as a proxy for
the expanded mossy fiber → granule cell representation in cerebellar
input layer.

Neural analog: Middle Cerebellar Peduncle (MCP) — the largest
cerebellar afferent pathway. Unlike the SCP (output) and ICP (input
from spinal cord and vestibular apparatus), the MCP carries
CORTICALLY DERIVED information into the cerebellum.

1. ANATOMY:
   - Origin: Pontine nuclei (basilar pons, ventral brainstem)
   - Course: purely ipsilateral (uncrossed) → enters cerebellum from below
   - Termination: Granule cell layer of cerebellar cortex
   - Pathway: Cerebral cortex (M1, premotor, somatosensory, prefrontal)
     → Pontine nuclei (basilar pons) → MCP → Cerebellar cortex granule cells

2. CORTICAL INPUT RELAY:
   Ramnani 2006 established that the basilar pons is a major relay
   station: cortical signals from motor and prefrontal areas project
   to pontine nuclei, which then send mossy fibers through the MCP
   to the cerebellum. This is the basis of the cerebello-cortical loop.

   - Motor cortex → pontine nuclei → MCP → cerebellum (motor timing)
   - Premotor cortex → pontine nuclei → MCP → cerebellum (movement planning)
   - Prefrontal cortex → pontine nuclei → MCP → cerebellum (cognitive sequencing)

3. GRANULE CELL EXPANSION (critical computational role):
   Each mossy fiber terminal in the cerebellar cortex contacts
   thousands of granule cells. Each granule cell receives input from
   only 4-5 mossy fiber rosettes. This creates a massive expansion:
   ~10^8 granule cells in human cerebellum receiving input from ~10^5
   mossy fiber inputs. This expansion is the cerebellar "expander" circuit
   (Marr-Albus-Ito theory) — it creates sparse, combinatorial
   representations of sensorimotor context.

   Purves et al. Neuroscience 2018: granule cells "transform a relatively
   small number of mossy fiber inputs into a much larger space of
   combinatorial activity patterns."

4. INPUT SIGNAL TYPES via MCP:
   - Motor commands (efference copy from M1)
   - Proprioceptive predictions (temporal/context signals)
   - Cognitive context (prefrontal signals about task state)
   - Somatosensory feedback (via pontine relay from SI/SII)

5. MCP DYSFUNCTION:
   - MCP lesions → ataxia of ipsilateral limbs (cerebellar ataxia pattern)
   - Pontine lesions interrupt the cortical → cerebellar relay
   - Results in dysmetria, intention tremor, dysdiadochokinesia

REFS:
- Ramnani 2006 Nat Rev Neurosci 7:511-522
  "The primate cerebellar sensory-motor and cognitive circuitry"
- Ramnani & Passingham 2006 J Neurosci 21:525-533
- Purves et al. Neuroscience 5th ed. 2018 (MCP anatomy, granule cell expansion)
- Marr D 1969 J Physiol 202:437-470 (granule cell expansion theory)
- Albus JS 1971 Math Biosci 10:25-61 (expander circuit)
- Ito M 2008 Scholarpedia 3:1410
- Apps & Garwicz 2005 Physiol Rev 85:1151-1174

CITATIONS:
    PMC3035609 — Kalinovsky A, Boukhtouche F, Blazeski R et al. (2011). Development of
        Axon-Target Specificity of Ponto-Cerebellar Afferents. J Neurosci.
    PMC4552263 — Rahimi-Balaei M, Afsharinezhad P, Bailey K et al. (2015). Embryonic
        Stages in Cerebellar Afferent Development. Cerebellum.
"""

from brain.base_mechanism import BrainMechanism


class PontocerebellarInput(BrainMechanism):
    """
    Middle Cerebellar Peduncle pontocerebellar input gateway.

    Models the MCP as a convergent input channel:
    - pontine_input_strength: total pontine relay activation
    - motor_cortex_relay: M1 → pontine → MCP motor signal
    - granule_cell_activation: granule cell layer activation level

    Granule cells encode the expanded combinatorial representation
    of cortical context. High granule cell activation = rich
    sensorimotor context representation.
    """

    GRANULE_EXPANSION_RATIO = 0.025  # Granule activation per unit input (sparse coding)
    MCP_LATENCY = 2  # Ticks of delay for cortical→pontine→cerebellar relay
    GRANULE_DECAY = 0.05
    MOTOR_BASELINE = 0.4

    def __init__(self):
        super().__init__(
            name="PontocerebellarInput",
            human_analog="Middle Cerebellar Peduncle → pontine relay → granule cell layer",
            layer="subcortical",
        )
        self.state.setdefault("pontine_input_strength", 0.5)
        self.state.setdefault("motor_cortex_relay", 0.5)
        self.state.setdefault("granule_cell_activation", 0.4)
        self.state.setdefault("relay_buffer", [0.0] * self.MCP_LATENCY)
        self.state.setdefault("last_cortical_input", 0.0)
        self.state.setdefault("cognitive_input_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal_data = prior.get("ArousalRegulator", {})
        prediction_data = prior.get("PredictionErrorDrift", {})

        # Input signals from cortical areas
        motor_cortical_input = input_data.get("motor_cortical_efference", self.MOTOR_BASELINE)
        prefrontal_input = input_data.get("prefrontal_context", 0.5)
        somatosensory_input = input_data.get("somatosensory_feedback", 0.3)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Pontine input strength ---
        # Pontine nuclei integrate cortical inputs: motor cortex, prefrontal,
        # and somatosensory. The basilar pons is the bottleneck relay.
        # Under high cognitive load, pontine nuclei may saturate.
        pontine_base = (
            motor_cortical_input * 0.45
            + prefrontal_input * 0.35
            + somatosensory_input * 0.20
        )

        # Arousal modulates pontine throughput
        pontine_base *= 0.6 + arousal * 0.4

        # MCP latency buffer: cortical input takes ~2 ticks to reach granule cells
        buffer = list(self.state["relay_buffer"])
        buffer.append(motor_cortical_input)
        buffer = buffer[-self.MCP_LATENCY:] if len(buffer) > self.MCP_LATENCY else buffer
        self.state["relay_buffer"] = buffer

        # Delayed pontine signal (MCP latency)
        delayed_input = buffer[0] if buffer else pontine_base

        # Slow pontine adaptation (prevents saturation under sustained load)
        prev_pontine = self.state["pontine_input_strength"]
        pontine_input_strength = prev_pontine * 0.85 + delayed_input * 0.15
        pontine_input_strength = max(0.0, min(1.0, pontine_input_strength))

        self.state["pontine_input_strength"] = round(pontine_input_strength, 4)

        # --- Motor cortex relay ---
        # The M1 → pontine → MCP channel for motor efference copy
        motor_relay = (
            motor_cortical_input * 0.6
            + somatosensory_input * 0.25
            + (1.0 - pontine_input_strength) * 0.15  # Inverse: low pontine → motor noise
        )
        motor_relay = max(0.0, min(1.0, motor_relay))

        # Prediction error modulates the motor relay
        prediction_error = prediction_data.get("prediction_error", 0.0)
        if abs(prediction_error) > 0.2:
            # Motor error → pontocerebellar signal gets stronger (error correction)
            motor_relay = min(1.0, motor_relay + abs(prediction_error) * 0.2)

        self.state["motor_cortex_relay"] = round(motor_relay, 4)

        # --- Granule cell activation ---
        # Granule cells fire sparsely; each activated unit requires sufficient
        # mossy fiber input. The activation ratio models the sparse coding
        # constraint (most granule cells are inactive at any moment).
        granule_raw = pontine_input_strength * self.GRANULE_EXPANSION_RATIO * 15.0
        granule_raw = max(0.0, min(1.0, granule_raw))

        # Context richness amplifies granule activation
        # Diverse inputs across motor/prefrontal/somatosensory channels
        # drive higher granule activation (richer combinatorial context)
        input_diversity = 1.0 - abs(motor_cortical_input - prefrontal_input) * 0.5
        granule_raw *= 0.7 + input_diversity * 0.3

        # Decay + slow update (granule cells maintain stable representation)
        current_granule = self.state["granule_cell_activation"]
        new_granule = current_granule * (1.0 - self.GRANULE_DECAY) + granule_raw * 0.3
        new_granule = max(0.0, min(1.0, new_granule))
        self.state["granule_cell_activation"] = round(new_granule, 4)

        # --- State tracking ---
        self.state["last_cortical_input"] = motor_cortical_input
        self.state["cognitive_input_strength"] = prefrontal_input
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pontine_input_strength": round(pontine_input_strength, 4),
            "motor_cortex_relay": round(motor_relay, 4),
            "granule_cell_activation": round(new_granule, 4),
        }
