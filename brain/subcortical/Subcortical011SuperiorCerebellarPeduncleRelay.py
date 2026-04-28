"""
Subcortical011SuperiorCerebellarPeduncleRelay.py — Wire 11: SCPThalamicRelay

Superior Cerebellar Peduncle (SCP) thalamic relay mechanism.

Models the SCP as the major cerebellar output tract, computing
output_fidelity of the cerebellar-thalamic relay, thalamic_relay_strength
of the VL/VA projection, and cerebellar_efference which is the
downstream signal entering thalamus en route to cortex.

Neural analog: Superior Cerebellar Peduncle (SCP) — the largest
cerebellar efferent pathway. All DCN output (from all four nuclei)
travels through the SCP after decussating (crossing) in the midbrain:

1. ANATOMY:
   - Origin: Deep Cerebellar Nuclei (dentate, emboliform, globose, fastigial)
   - Course: ascends from cerebellum → decussates in midbrain (ventral decussation)
   - Termination: VL (ventral lateral) and VA (ventral anterior) thalamic nuclei
   - From thalamus: projects to motor cortex (M1, premotor) and prefrontal cortex

2. DECUSSATION:
   - SCP fibers cross at the midbrain level before reaching the thalamus
   - This means the LEFT cerebellum sends output to the RIGHT thalamus
     → RIGHT motor/prefrontal cortex
   - This crossed arrangement underlies the cerebellum's ipsilateral
     coordination (left cerebellum coordinates the left side of the body)

3. FUNCTIONAL RELAY:
   Stoodley & Schmahmann 2009 (Cortex 45:975-991) described the SCP as
   "the main efferent pathway for cerebellar output to the cerebral
   cortex" with two primary targets:
   - VL nucleus → motor cortex (primary and premotor)
   - VA nucleus → prefrontal cortex (cognitive operations)

4. CEREBELLO-THALAMO-CORTICAL LOOP:
   Input: Cerebral cortex (motor planning, premotor, prefrontal) →
   Pontine nuclei → Mossy fibers → Cerebellar cortex →
   Purkinje cells → DCN → SCP → Thalamus (VL/VA) →
   Cerebral cortex (closed loop)

5. RELAY FIDELITY:
   The SCP relay has finite bandwidth. Under high cognitive load,
   cerebellar signals compete with other thalamic inputs. Relay
   fidelity is modulated by attention, arousal, and competing traffic.

6. FIDELITY DISRUPTION:
   - Lesions of SCP produce cerebellar outflow ataxia
   - Disconnection of SCP (superior cerebellar peduncle syndrome) causes
     dysmetria, intention tremor, dysdiadochokinesia
   - These are classic cerebellar motor signs seen when the output
     pathway is disrupted

REFS:
- Stoodley & Schmahmann 2009 Cortex 45:975-991
  "Functional topography of the human cerebellum"
- Ramnani 2006 Nat Rev Neurosci 7:511-522
- Purves et al. Neuroscience 5th ed. 2018 (SCP anatomy)
- Ito 2008 Scholarpedia 3:1410
- Bostan et al. 2013 Front Neural Circuits 7:93 (cerebello-thalamic circuits)

CITATIONS:
    PMC4575696 — Palesi F, Tournier JD, Calamante F et al. (2015). Contralateral
        Cerebello-Thalamo-Cortical Pathways with Prominent Involvement of Associative
        Areas in Humans In Vivo. Neuroimage.
    PMC4537674 — Houck BD, Person AL (2015). Cerebellar Premotor Output Neurons
        Collateralize to Innervate the Cerebellar Cortex. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class SCPThalamicRelay(BrainMechanism):
    """
    Superior Cerebellar Peduncle thalamic relay mechanism.

    Models the SCP as a noisy relay channel between DCN output and
    VL/VA thalamic nuclei. Computes:
    - output_fidelity: relay channel quality (function of noise + competition)
    - thalamic_relay_strength: effective thalamic activation
    - cerebellar_efference: downstream signal entering cortex

    The SCP passes through the decussation (midbrain crossing), so this
    mechanism models both the raw cerebellar output and the post-decussation
    thalamic signal.
    """

    SCP_DECUSSATION_LOSS = 0.12
    THALAMIC_NOISE_FLOOR = 0.05
    FIDELITY_DECAY = 0.04

    def __init__(self):
        super().__init__(
            name="SCPThalamicRelay",
            human_analog="Superior Cerebellar Peduncle → VL/VA thalamic relay",
            layer="subcortical",
        )
        self.state.setdefault("output_fidelity", 0.85)
        self.state.setdefault("thalamic_relay_strength", 0.5)
        self.state.setdefault("cerebellar_efference", 0.5)
        self.state.setdefault("relay_noise", 0.0)
        self.state.setdefault("decussation_crossed_output", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        dcn_data = prior.get("CerebellarOutputGate", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        cerebellar_output = dcn_data.get("cerebellar_output_signal", 0.5)
        motor_command = dcn_data.get("motor_command_strength", 0.5)
        cognitive_command = dcn_data.get("cognitive_command_strength", 0.5)
        thalamic_traffic = input_data.get("thalamic_traffic", 0.3)
        attention_allocation = input_data.get("attention_allocation", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Decussation: crossed output ---
        # SCP fibers cross at midbrain → output to contralateral thalamus
        # A small loss occurs at the decussation (axonal path length + crossing noise)
        decussation_loss = self.SCP_DECUSSATION_LOSS
        raw_crossed_output = cerebellar_output * (1.0 - decussation_loss)
        self.state["decussation_crossed_output"] = round(raw_crossed_output, 4)

        # --- Relay noise ---
        # Noise arises from: thalamic traffic competition, low arousal,
        # spontaneous thalamic firing (thalamic noise floor)
        current_noise = self.state["relay_noise"]
        traffic_noise = thalamic_traffic * 0.15
        arousal_noise = (1.0 - arousal) * 0.1
        new_noise = current_noise * 0.7 + traffic_noise + arousal_noise
        self.state["relay_noise"] = round(new_noise, 4)

        # --- Output fidelity ---
        # Fidelity = clean signal / (signal + noise)
        signal = raw_crossed_output
        noise = new_noise + self.THALAMIC_NOISE_FLOOR
        fidelity = signal / (signal + noise) if (signal + noise) > 0 else 0.0
        fidelity = max(0.0, min(1.0, fidelity))

        # Attention boosts fidelity by reducing thalamic competition
        attention_boost = (attention_allocation - 0.5) * 0.3
        fidelity = max(0.0, min(1.0, fidelity + attention_boost))

        # Slow fidelity decay (prevents sticking at high values)
        fidelity = max(0.0, fidelity - self.FIDELITY_DECAY * (1.0 - fidelity))
        self.state["output_fidelity"] = round(fidelity, 4)

        # --- Thalamic relay strength ---
        # VL gets motor cerebellar output; VA gets cognitive cerebellar output
        # Thalamic relay = weighted combination filtered by fidelity
        thalamic_relay = (
            raw_crossed_output * motor_command * 0.5
            + raw_crossed_output * cognitive_command * 0.5
        ) * fidelity
        thalamic_relay = max(0.0, min(1.0, thalamic_relay))
        self.state["thalamic_relay_strength"] = round(thalamic_relay, 4)

        # --- Cerebellar efference ---
        # This is the signal that enters cortex after the full relay
        cerebellar_efference = (
            thalamic_relay * 0.6
            + raw_crossed_output * fidelity * 0.4
        )
        cerebellar_efference = max(0.0, min(1.0, cerebellar_efference))
        self.state["cerebellar_efference"] = round(cerebellar_efference, 4)

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "output_fidelity": round(fidelity, 4),
            "thalamic_relay_strength": round(thalamic_relay, 4),
            "cerebellar_efference": round(cerebellar_efference, 4),
        }
