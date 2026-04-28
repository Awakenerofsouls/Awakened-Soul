"""
Build 43: Foundational043BehavioralStateIntegrator — Reticular Activating System
===============================================================================

PLACEMENT:
  Layer:    foundational (brainstem — ascending reticular activating system, ARAS)
  Filename: brain/foundational/Foundational043BehavioralStateIntegrator.py
  Instance name: BehavioralStateIntegrator

NEURAL SUBSTRATE:
  Ascending reticular activating system (ARAS) — the diffuse network
  of neurons that maintains consciousness and behavioral state. The ARAS
  has two main branches:
  - BRAINSTEM ARAS: cholinergic (PPT/LDT in pons) + serotonergic (raphe) +
    noradrenergic (LC) + histaminergic (TMN) ascending projections
    to thalamus → cortex
  - FOREBRAIN ARAS: basal forebrain (BF) cholinergic neurons projecting
    to cortex; regulated by amygdala, hypothalamus, brainstem arousal

  The ARAS controls the cortical EEG state:
  - Gamma (40 Hz): wake, attention, consciousness
  - Theta (4-8 Hz): REM sleep, spatial memory
  - Delta (0.5-4 Hz): deep NREM sleep
  - Alpha (8-13 Hz): relaxed wakefulness, closed eyes

  Human analog: state of consciousness, cortical arousal, EEG patterns.

Output keys:
  cortical_arousal_level: float [0.0–1.0] — cortical activation state
  eeg_state: float [0.0–1.0] — EEG pattern indicator (0=delta, 0.5=theta, 1.0=gamma)
  behavioral_state: str — categorical state ("wake", "nrem", "rem", "anesthesia")
  consciousness_index: float [0.0–1.0] — subjective awareness level
  attention_modulation: float [0.0–1.0] — attention/gain control signal

CITATIONS:
    PMC1365560 — Szerb JC (1967). Cortical Acetylcholine Release and
        Electroencephalographic Arousal. Can J Physiol Pharmacol.
    PMC3119596 — Fuller PM, Sherman D, Pedersen NP et al. (2011). Reassessment of
        the Structural Basis of the Ascending Arousal System. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class BehavioralStateIntegrator(BrainMechanism):
    """
    ARAS: cortical arousal, EEG state, behavioral state integration.

    Integrates brainstem arousal nuclei to produce the global
    cortical arousal level and EEG state.
    """

    STATE_FIELDS = [
        "cortical_arousal_level", "eeg_state", "behavioral_state",
        "consciousness_index", "attention_modulation", "tick_count",
    ]

    ARAS_CHOLINERGIC_GAIN = 0.40
    ARAS_NORADRENERGIC_GAIN = 0.30
    ARAS_SEROTONERGIC_GAIN = 0.20
    ARAS_HISTAMINERGIC_GAIN = 0.25

    def __init__(self, name: str = "BehavioralStateIntegrator",
                 human_analog: str = "ARAS — ascending reticular activating system",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["cortical_arousal_level"] = 0.50
        self.state["eeg_state"] = 0.50  # 0.5 = theta (mid)
        self.state["behavioral_state"] = "wake"
        self.state["consciousness_index"] = 0.80
        self.state["attention_modulation"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cholinergic = prior.get("CholinergicREMOn", {}).get("rem_drive", 0.0)
        lc_noradrenaline = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        raphe_serotonin = prior.get("DorsalRapheSerotonin", {}).get("serotonin_level", 0.30)
        histamine = prior.get("HistamineArousalBooster", {}).get("histamine_level", 0.30)
        rem_atonia = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        sleep_quiescence = prior.get("PassiveQuiescenceMode", {}).get(
            "passive_quiescence_level", 0.0
        )

        # Cortical arousal: weighted sum of ascending neuromodulators
        cortical_arousal = (
            lc_noradrenaline * self.ARAS_NORADRENERGIC_GAIN +
            raphe_serotonin * self.ARAS_SEROTONERGIC_GAIN +
            histamine * self.ARAS_HISTAMINERGIC_GAIN
        )
        # REM-active cholinergic adds to cortical arousal during REM
        cortical_arousal += cholinergic * self.ARAS_CHOLINERGIC_GAIN * 0.50
        cortical_arousal = min(1.0, max(0.0, cortical_arousal))

        # EEG state: maps arousal to canonical frequency bands
        # High arousal → gamma; moderate → alpha; low → theta; very low → delta
        if cortical_arousal > 0.75:
            eeg_state = 0.90  # gamma
        elif cortical_arousal > 0.55:
            eeg_state = 0.65  # alpha
        elif cortical_arousal > 0.35:
            eeg_state = 0.40  # theta (REM)
        else:
            eeg_state = 0.10  # delta (deep NREM)

        # Behavioral state: determine from cortical arousal and sleep signals
        if rem_atonia > 0.35:
            behavioral_state = "rem"
            consciousness_index = 0.50  # dreaming awareness
        elif sleep_quiescence > 0.40 and cortical_arousal < 0.40:
            behavioral_state = "nrem"
            consciousness_index = 0.10  # unconscious
        elif cortical_arousal > 0.60:
            behavioral_state = "wake"
            consciousness_index = 0.85  # full awareness
        else:
            behavioral_state = "drowsy"
            consciousness_index = 0.40  # reduced awareness

        # Attention modulation: LC NE gain control (Aston-Jones)
        attention_modulation = lc_noradrenaline * 0.60 + raphe_serotonin * 0.20
        attention_modulation = min(1.0, max(0.0, attention_modulation))

        # --- Persist ---
        self.state["cortical_arousal_level"] = round(cortical_arousal, 4)
        self.state["eeg_state"] = round(eeg_state, 4)
        self.state["behavioral_state"] = behavioral_state
        self.state["consciousness_index"] = round(consciousness_index, 4)
        self.state["attention_modulation"] = round(attention_modulation, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cortical_arousal_level": round(cortical_arousal, 4),
            "eeg_state": round(eeg_state, 4),
            "behavioral_state": behavioral_state,
            "consciousness_index": round(consciousness_index, 4),
            "attention_modulation": round(attention_modulation, 4),
        }
