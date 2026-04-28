"""
Build 47: Foundational047TactileProprioRelay — Spinal Somatosensory Relay
======================================================================

PLACEMENT:
  Layer:    foundational (spinal cord — dorsal horn, Rexed laminae III-VI)
  Filename: brain/foundational/Foundational047TactileProprioRelay.py
  Instance name: TactileProprioRelay

NEURAL SUBSTRATE:
  Spinal dorsal horn — the somatosensory relay station for tactile and
  proprioceptive information entering the spinal cord:

  LAMINAR ORGANIZATION:
  - Lamina I (marginal zone): nociceptive (pain) specific neurons
  - Lamina II (substantia gelatinosa): nociceptive projection, gate control
  - Lamina III-IV (nucleus proprius): low-threshold mechanoreceptors (LTMR)
  - Lamina V-VI: wide dynamic range (WDR) neurons, viscerotopic input

  AFFERENT FIBER TYPES:
  - Aδ (fast pain): → Lamina I
  - Aβ (touch, vibration): → Lamina III-IV
  - C (slow pain): → Lamina II
  - Ia (muscle spindle): → Clarke's column (cerebellar input)
  - II (Golgi tendon): → inhibitory interneurons

  Human analog: tactile sensation, proprioception, spinothalamic tract.

Output keys:
  tactile_discrimination: float [0.0–1.0] — fine touch discrimination
  proprioceptive_accuracy: float [0.0–1.0] — body position accuracy
  dorsal_horn_gate: float [0.0–1.0] — substantia gelatinosa gate state
  pain_signal_transmission: float [0.0–1.0] — nociceptive relay level
  somatosensory_integration: float [0.0–1.0] — multi-modal somatosensory fusion

CITATIONS:
    PMC6330897 — Delhaye BP, Long KH, Bensmaia SJ (2018). Neural Basis of Touch and
        Proprioception in Primate Cortex. Compr Physiol.
    PMC11502235 — Rubio-Teves M, Martín-Correa P, Alonso-Martínez C et al. (2024).
        Beyond Barrels: Diverse Thalamocortical Projection Motifs in the Mouse Ventral
        Posterior Complex. J Comp Neurol.
"""

from brain.base_mechanism import BrainMechanism


class TactileProprioRelay(BrainMechanism):
    """
    Spinal dorsal horn: tactile and proprioceptive relay.

    Models the dorsal horn as a gate-controlled somatosensory relay
    with tactile discrimination and proprioceptive accuracy.
    """

    STATE_FIELDS = [
        "tactile_discrimination", "proprioceptive_accuracy", "dorsal_horn_gate",
        "pain_signal_transmission", "somatosensory_integration", "tick_count",
    ]

    TACTILE_GAIN = 0.60
    PROPRIOCEPTIVE_GAIN = 0.55
    GATE_GAIN = 0.50

    def __init__(self, name: str = "TactileProprioRelay",
                 human_analog: str = "Spinal dorsal horn — tactile and proprioceptive relay",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["tactile_discrimination"] = 0.60
        self.state["proprioceptive_accuracy"] = 0.60
        self.state["dorsal_horn_gate"] = 0.50
        self.state["pain_signal_transmission"] = 0.20
        self.state["somatosensory_integration"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        gate = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        tactile_input = prior.get("PeripheralTouch", {}).get("touch_intensity", 0.50)
        proprioceptive_input = prior.get("VestibularIntegrator", {}).get(
            "proprioceptive_signal", 0.50
        )
        pain_signal = prior.get("SpinalNociceptiveRelay", {}).get("nociceptive_output", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)

        # Dorsal horn gate: descending pain gate controls transmission
        # gate=1 means open (pain allowed); gate=0 means closed (pain blocked)
        dorsal_gate = gate * self.GATE_GAIN

        # Tactile discrimination: Aβ input × gate × arousal
        tactile = tactile_input * dorsal_gate * (0.60 + arousal * 0.40)
        tactile_discrimination = min(1.0, tactile)

        # Proprioceptive accuracy: maintained even with gate closed
        proprioceptive_accuracy = proprioceptive_input * 0.70
        proprioceptive_accuracy = min(1.0, proprioceptive_accuracy)

        # Pain signal transmission: nociceptive relay
        pain_transmission = pain_signal * (1.0 - gate) * 0.80
        pain_signal_transmission = min(1.0, pain_transmission)

        # Somatosensory integration: combine tactile + proprioceptive + pain
        integration = (tactile_discrimination * 0.35 +
                       proprioceptive_accuracy * 0.35 +
                       (1.0 - pain_signal_transmission) * 0.30)
        somatosensory_integration = min(1.0, integration)

        # --- Persist ---
        self.state["tactile_discrimination"] = round(tactile_discrimination, 4)
        self.state["proprioceptive_accuracy"] = round(proprioceptive_accuracy, 4)
        self.state["dorsal_horn_gate"] = round(dorsal_gate, 4)
        self.state["pain_signal_transmission"] = round(pain_transmission, 4)
        self.state["somatosensory_integration"] = round(somatosensory_integration, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tactile_discrimination": round(tactile_discrimination, 4),
            "proprioceptive_accuracy": round(proprioceptive_accuracy, 4),
            "dorsal_horn_gate": round(dorsal_gate, 4),
            "pain_signal_transmission": round(pain_transmission, 4),
            "somatosensory_integration": round(somatosensory_integration, 4),
        }
