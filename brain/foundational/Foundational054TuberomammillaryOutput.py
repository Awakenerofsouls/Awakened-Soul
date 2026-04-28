"""
Build 54: Foundational054TuberomammillaryOutput — Histaminergic Arousal System
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — tuberomammillary nucleus, TMN)
  Filename: brain/foundational/Foundational054TuberomammillaryOutput.py
  Instance name: TuberomammillaryOutput

NEURAL SUBSTRATE:
  Tuberomammillary nucleus (TMN) in the posterior hypothalamus — the
  sole source of histamine in the brain. TMN neurons are wake-active,
  receive input from orexin neurons (which excite them), and project
  widely to cortex, basal forebrain, and other arousal centers.

  HISTAMINE EFFECTS:
  - Cortex: promotes wakefulness, attention, cortical activation
  - Basal forebrain: excites BF cholinergic neurons → cortical ACh
  - Arousal centers: synergistic with LC (NE) and raphe (5-HT)
  - Suppresses VLPO/SubC: histamine inhibits sleep-promoting neurons

  TMN is suppressed during sleep (especially NREM); VLPO GABA inhibits TMN.
  Antihistamines (H1 antagonists) cause drowsiness. H3 autoreceptors
  regulate TMN firing (H3 agonism = autoinhibition).

  Human analog: antihistamine drowsiness, histamine-driven wakefulness.

Output keys:
  histamine_output: float [0.0–1.0] — TMN histamine release
  cortical_activator: float [0.0–1.0] — cortical arousal via histamine
  tmn_wake_drive: float [0.0–1.0] — TMN wake-promoting output
  histamine_gate_modulation: float [0.0–1.0] — H3 autoreceptor modulation
  sleep_suppression_by_histamine: float [0.0–1.0] — VLPO/SubC suppression

CITATIONS:
    PMC5172538 — Hoffman GE, Koban M (2016). Hypothalamic L-Histidine Decarboxylase
        Is Up-Regulated During Chronic REM Sleep Deprivation of Rats. Sleep.
    PMC6674640 — Takahashi K, Lin JS, Sakai K (2006). Neuronal Activity of
        Histaminergic Tuberomammillary Neurons During Wake-Sleep States in the Mouse.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class TuberomammillaryOutput(BrainMechanism):
    """
    TMN: histaminergic arousal, cortical activation, sleep suppression.

    Models TMN as the histaminergic wake-promoting system.
    """

    STATE_FIELDS = [
        "histamine_output", "cortical_activator", "tmn_wake_drive",
        "histamine_gate_modulation", "sleep_suppression_by_histamine", "tick_count",
    ]

    HISTAMINE_GAIN = 0.60
    CORTICAL_GAIN = 0.55
    SLEEP_GATE_GAIN = 0.50

    def __init__(self, name: str = "TuberomammillaryOutput",
                 human_analog: str = "TMN — histaminergic wake-promoting system",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["histamine_output"] = 0.40
        self.state["cortical_activator"] = 0.35
        self.state["tmn_wake_drive"] = 0.40
        self.state["histamine_gate_modulation"] = 0.30
        self.state["sleep_suppression_by_histamine"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        h3_agonist = prior.get("H3AutoreceptorSignal", {}).get("h3_activity", 0.20)
        sleep = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Histamine output: driven by orexin, arousal; suppressed by VLPO and H3 agonism
        excitation = orexin * 0.40 + arousal * 0.35
        inhibition = vlpo * 0.35 + h3_agonist * 0.30 + sleep * 0.40
        histamine_raw = max(0.0, excitation - inhibition)
        histamine_output = min(1.0, histamine_raw)

        # TMN wake drive
        tmn_wake_drive = histamine_output * self.HISTAMINE_GAIN

        # Cortical activator: histamine → BF → cortical ACh
        cortical_activator = histamine_output * self.CORTICAL_GAIN

        # Histamine gate modulation: H3 autoreceptor controls release
        histamine_gate_modulation = 1.0 - h3_agonist * 0.80

        # Sleep suppression by histamine: histamine inhibits VLPO
        sleep_suppression = histamine_output * self.SLEEP_GATE_GAIN * 0.30

        # --- Persist ---
        self.state["histamine_output"] = round(histamine_output, 4)
        self.state["cortical_activator"] = round(cortical_activator, 4)
        self.state["tmn_wake_drive"] = round(tmn_wake_drive, 4)
        self.state["histamine_gate_modulation"] = round(histamine_gate_modulation, 4)
        self.state["sleep_suppression_by_histamine"] = round(sleep_suppression, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "histamine_output": round(histamine_output, 4),
            "cortical_activator": round(cortical_activator, 4),
            "tmn_wake_drive": round(tmn_wake_drive, 4),
            "histamine_gate_modulation": round(histamine_gate_modulation, 4),
            "sleep_suppression_by_histamine": round(sleep_suppression, 4),
        }
