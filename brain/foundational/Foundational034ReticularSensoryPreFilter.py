"""
Build 34: Foundational034ReticularSensoryPreFilter — Reticular Formation Sensory Gate
================================================================================

PLACEMENT:
  Layer:    foundational (brainstem reticular formation)
  Filename: brain/foundational/Foundational034ReticularSensoryPreFilter.py
  Instance name: ReticularSensoryPreFilter

NEURAL SUBSTRATE:
  Reticular formation (RF) in the brainstem core — a diffuse network of
  neurons spanning the medulla, pons, and midbrain. The RF is the
  substrate of the ascending reticular activating system (ARAS), which
  modulates sensory transmission through the thalamus and cortex.

  KEY FUNCTIONS:
  - Sensory gating: RF neurons in the intralaminar nuclei of thalamus
    control sensory relay fidelity (facilitate novel stimuli, suppress
    familiar unattended signals)
  - Thalamic relay modulation: cholinergic RF input to thalamus shifts
    firing mode from burst (sleep) to tonic (wake)
  - Sensory modulation of pain: RF mediates diffuse noxious inhibitory
    controls (DNIC) — one pain suppresses another

  Human analog: sensory filtering, attention, pain modulation.

Output keys:
  sensory_gate_output: float [0.0–1.0] — net sensory transmission level
  thalamic_relay_fidelity: float [0.0–1.0] — thalamic sensory relay quality
  novel_stimulus_flag: float [0.0–1.0] — novelty detection signal
  pain_inhibition_input: float [0.0–1.0] — DNIC analgesic input
  reticular_alert_level: float [0.0–1.0] — overall RF arousal state

CITATIONS:
    PMC2855189 — Zikopoulos B, Barbas H (2007). Circuits for Multisensory Integration
        and Attentional Modulation Through the Prefrontal Cortex and the Thalamic
        Reticular Nucleus. Rev Neurosci.
    PMC3119596 — Fuller PM, Sherman D, Pedersen NP et al. (2011). Reassessment of
        the Structural Basis of the Ascending Arousal System. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ReticularSensoryPreFilter(BrainMechanism):
    """
    Reticular formation: sensory gate, thalamic relay, novelty detection.

    Controls sensory throughput and thalamic relay fidelity based on
    arousal state and novelty signals.
    """

    STATE_FIELDS = [
        "sensory_gate_output", "thalamic_relay_fidelity", "novel_stimulus_flag",
        "pain_inhibition_input", "reticular_alert_level", "tick_count",
    ]

    GATE_GAIN = 0.60
    THALAMIC_GAIN = 0.55
    NOVELTY_GAIN = 0.50
    DNIC_GAIN = 0.45

    def __init__(self, name: str = "ReticularSensoryPreFilter",
                 human_analog: str = "Reticular formation — sensory gating and ARAS",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["sensory_gate_output"] = 0.50
        self.state["thalamic_relay_fidelity"] = 0.50
        self.state["novel_stimulus_flag"] = 0.0
        self.state["pain_inhibition_input"] = 0.0
        self.state["reticular_alert_level"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        visual_novelty = prior.get("VisualSalienceMap", {}).get("salience_level", 0.0)
        auditory_novelty = prior.get("AuditoryOrienting", {}).get("azimuth_salience", 0.0)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Reticular alert level: rises with arousal, falls during sleep
        alert = (arousal * 0.60) - (sleep_signal * 0.30)

        # Thalamic relay fidelity: high during wake, low during sleep (burst mode)
        # Arousal drives tonic firing (high fidelity); sleep drives burst (low fidelity)
        thalamic_fidelity = alert
        # Inverted pain gate: pain suppresses sensory gating (hypervigilance)
        pain_modulation = (1.0 - pain) * 0.20
        thalamic_fidelity = max(0.0, min(1.0, thalamic_fidelity + pain_modulation))

        # Sensory gate output: what % of sensory input is transmitted
        sensory_gate = alert * self.GATE_GAIN
        sensory_gate = min(1.0, sensory_gate)

        # Novel stimulus flag: any salient novel input triggers flag
        novelty = max(visual_novelty, auditory_novelty)
        novel_stimulus = novelty * self.NOVELTY_GAIN
        # Novelty overrides sleep suppression
        if novel_stimulus > 0.40:
            sensory_gate = max(sensory_gate, novel_stimulus)

        # Pain inhibition (DNIC): one pain inhibits others
        pain_inhibition = (1.0 - pain) * self.DNIC_GAIN

        # --- Persist ---
        self.state["sensory_gate_output"] = round(sensory_gate, 4)
        self.state["thalamic_relay_fidelity"] = round(thalamic_fidelity, 4)
        self.state["novel_stimulus_flag"] = round(novel_stimulus, 4)
        self.state["pain_inhibition_input"] = round(pain_inhibition, 4)
        self.state["reticular_alert_level"] = round(alert, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sensory_gate_output": round(sensory_gate, 4),
            "thalamic_relay_fidelity": round(thalamic_fidelity, 4),
            "novel_stimulus_flag": round(novel_stimulus, 4),
            "pain_inhibition_input": round(pain_inhibition, 4),
            "reticular_alert_level": round(alert, 4),
        }
