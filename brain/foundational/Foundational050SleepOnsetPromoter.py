"""
Build 50: Foundational050SleepOnsetPromoter — Mnemonic Consolidation + Sleep Transition
==================================================================================

PLACEMENT:
  Layer:    foundational (forebrain — basal forebrain, diagonal band of Broca)
  Filename: brain/foundational/Foundational050SleepOnsetPromoter.py
  Instance name: SleepOnsetPromoter

NEURAL SUBSTRATE:
  Basal forebrain (BF) — the largest contiguous group of cholinergic neurons
  in the brain. BF cholinergic neurons (Ch1-Ch4) project widely to the
  cortex and hippocampus:
  - Corticopetal ACh: BF → neocortex (attention, plasticity)
  - Septohippocampal: MS/DBB → hippocampus (memory consolidation)

  BF NEURONS:
  - Cholinergic (60%): wake-promoting, cortical activation
  - GABAergic (30%): sleep-active, local inhibition
  - Glutamatergic (10%): mixed

  KEY: BF sleep-active neurons are NOT VLPO — they are a separate population
  in the substantia innominata that fires specifically during NREM and REM
  sleep. BF ACh release during REM is critical for hippocampal memory
  consolidation (dream memory consolidation).

  Human analog: sleep onset, memory consolidation, cortical activation for dreaming.

Output keys:
  sleep_onset_probability: float [0.0–1.0] — likelihood of sleep onset
  hippocampal_consolidation: float [0.0–1.0] — memory consolidation drive
  cortical_activation_during_sleep: float [0.0–1.0] — BF ACh sleep drive
  cholinergic_rem_drive: float [0.0–1.0] — REM-specific BF activation
  basal_forebrain_integrator: float [0.0–1.0] — composite BF state

CITATIONS:
    PMC12227200 — Rieser NN, Ronchetti M, Hotz ALL et al. (2025). Multifaceted Role
        of Galanin in Brain Excitability. Brain Sci.
    PMC7491139 — Guo X, Gao X, Keenan BT et al. (2020). RNA-Seq Analysis of
        Galaninergic Neurons From Ventrolateral Preoptic Nucleus Identifies Expression
        Changes Between Sleep and Wake. Sleep.
"""

from brain.base_mechanism import BrainMechanism


class SleepOnsetPromoter(BrainMechanism):
    """
    Basal forebrain: sleep onset, hippocampal consolidation, REM cholinergic drive.

    Models basal forebrain cholinergic neurons as sleep-onset promoters
    and hippocampal consolidation facilitators.
    """

    STATE_FIELDS = [
        "sleep_onset_probability", "hippocampal_consolidation",
        "cortical_activation_during_sleep", "cholinergic_rem_drive",
        "basal_forebrain_integrator", "tick_count",
    ]

    SLEEP_GAIN = 0.50
    CONSOLIDATION_GAIN = 0.55
    REM_GAIN = 0.60

    def __init__(self, name: str = "SleepOnsetPromoter",
                 human_analog: str = "Basal forebrain — sleep onset and memory consolidation",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["sleep_onset_probability"] = 0.20
        self.state["hippocampal_consolidation"] = 0.40
        self.state["cortical_activation_during_sleep"] = 0.30
        self.state["cholinergic_rem_drive"] = 0.0
        self.state["basal_forebrain_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        homeostatic = prior.get("Homeostat", {}).get("cumulative_pressure", 0.30)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        rem_atonia = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        theta_power = prior.get("HippocampalReplayIntegrator", {}).get("theta_power", 0.30)
        sleep_quiescence = prior.get("SleepWakeFlipFlop", {}).get("sleep_dominance", 0.0)

        # Sleep onset probability: driven by homeostatic pressure + circadian trough
        circadian_trough = 1.0 - circadian  # low circadian = permissive for sleep
        sleep_onset = (homeostatic * 0.50) + (circadian_trough * 0.30) + (vlpo * 0.20)
        sleep_onset_probability = min(1.0, max(0.0, sleep_onset))

        # Cortical activation during sleep: BF ACh during sleep (distinct from wake ACh)
        cortical_sleep = rem_atonia * 0.40 + theta_power * 0.30
        cortical_activation_during_sleep = min(1.0, cortical_sleep)

        # Hippocampal consolidation: theta rhythm + sleep quiescence drive consolidation
        hippocampal_consolidation = theta_power * self.CONSOLIDATION_GAIN
        # NREM delta suppresses consolidation; REM theta promotes it
        hippocampal_consolidation *= (1.0 - rem_atonia * 0.50)
        hippocampal_consolidation = min(1.0, hippocampal_consolidation)

        # Cholinergic REM drive: BF fires during REM to support hippocampal replay
        cholinergic_rem = rem_atonia * self.REM_GAIN
        # REM theta is the signature of BF cholinergic activation during REM
        cholinergic_rem_drive = cholinergic_rem * theta_power

        # Basal forebrain integrator
        basal_forebrain_integrator = (
            cortical_activation_during_sleep * 0.30 +
            hippocampal_consolidation * 0.35 +
            cholinergic_rem_drive * 0.35
        )

        # --- Persist ---
        self.state["sleep_onset_probability"] = round(sleep_onset_probability, 4)
        self.state["hippocampal_consolidation"] = round(hippocampal_consolidation, 4)
        self.state["cortical_activation_during_sleep"] = round(cortical_activation_during_sleep, 4)
        self.state["cholinergic_rem_drive"] = round(cholinergic_rem_drive, 4)
        self.state["basal_forebrain_integrator"] = round(basal_forebrain_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sleep_onset_probability": round(sleep_onset_probability, 4),
            "hippocampal_consolidation": round(hippocampal_consolidation, 4),
            "cortical_activation_during_sleep": round(cortical_activation_during_sleep, 4),
            "cholinergic_rem_drive": round(cholinergic_rem_drive, 4),
            "basal_forebrain_integrator": round(basal_forebrain_integrator, 4),
        }
