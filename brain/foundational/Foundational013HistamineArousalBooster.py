"""
Build 22: Foundational013HistamineArousalBooster — Tuberomammillary Histamine System
==================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamic — tuberomammillary nucleus)
  Filename: brain/foundational/Foundational013HistamineArousalBooster.py
  Instance name: HistamineArousalBooster

NEURAL SUBSTRATE:
  Tuberomammillary nucleus (TMN) in the posterior hypothalamus
  is the sole source of histamine to the entire cerebral cortex.
  Histaminergic neurons fire at 2-5 Hz during wakefulness, are
  silent during NREM and REM sleep, and provide a third major
  wake-promoting signal alongside LC-NE and orexin.

  TMN histamine has distinct arousal effects from NE and orexin:
  - Promotes cortical activation and wakefulness (H1 receptor)
  - Suppresses NREM sleep onset (H1 receptor in VLPO)
  - Enhances attention via H2 receptors in prefrontal cortex
  - Antihistamines (H1 blockers) cause drowsiness — direct
    confirmation of the histaminergic wake-promoting system

  TMN is suppressed by:
  - GABAergic inputs from VLPO during sleep
  - Orexin input (bidirectional: orexin activates TMN; TMN
    inhibits orexin via H3 autoreceptors)
  - Alcohol and sedating antihistamines (H1 antagonists)

KEY FINDINGS:
  1. TMN histaminergic neurons fire at 2-5 Hz during active waking
     and are completely silent during both NREM and REM sleep —
     unlike LC neurons which fire during REM (Vanni-Mercier et al.
     2003, Arch Ital Biol).
  2. H1 receptor activation in the posterior hypothalamus is
     required for active waking: H1 knockout mice show fragmented
     wake episodes and increased NREM sleep (Yanai et al. 2018,
     Behav Brain Res).
  3. Antihistamines (H1 antagonists) produce drowsiness by
     blocking TMN cortical projections — this is why first-generation
     antihistamines are sedating (Tasaka 2004, Clin Exp Pharmacol Physiol).
  4. Histamine release in the prefrontal cortex enhances attention
     and working memory: H2 receptors modulate prefrontal pyramidal
     neuron firing (Haas et al. 2008, Nat Rev Neurosci).
  5. H3 autoreceptors on TMN cell bodies inhibit further histamine
     release — this negative feedback loop allows rapid shutdown
     of histamine signaling when antagonists are present
     (Hill et al. 1997, Inflamm Res).

INPUTS (prior_results):
  - ArousalRegulator: arousal_level (float 0-1), mode (str)
  - OrexinWakePromoter: orexin_tone (float 0-1)
  - Homeostat: dominant_drive (str)
  - ThermoSleepGate: sleep_gate_open (bool)
  - GutSignalRelay: gut_distress (float 0-1)

OUTPUTS:
  - histamine_tone: float 0.0-1.0 (histaminergic arousal level)
  - cortical_activation: float 0.0-1.0 (H1 receptor cortical activation)
  - attention_enhancement: float 0.0-1.0 (prefrontal H2-mediated attention)
  - h3_autoreceptor_suppression: float 0.0-1.0 (H3-mediated feedback)

CITATIONS:
    PMC6674640 — Takahashi K, Lin JS, Sakai K (2006). Neuronal Activity of Histaminergic
        Tuberomammillary Neurons During Wake-Sleep States in the Mouse. J Neurosci.
    PMC5790777 — Yu X, Franks NP, Wisden W (2018). Sleep and Sedative States Induced by
        Targeting the Histamine and Noradrenergic Systems. Front Neurol.
"""

from brain.base_mechanism import BrainMechanism


class HistamineArousalBooster(BrainMechanism):
    """
    Tuberomammillary nucleus — histaminergic arousal system.

    TMN histaminergic neurons promote wake via H1/H2 receptors.
    Third arm of the wake-promoting triad (LC-NE, orexin, histamine).
    """

    BASELINE_TONE = 0.45
    CONVERGENCE_RATE = 0.15

    def __init__(self):
        super().__init__(
            name="HistamineArousalBooster",
            human_analog=(
                "Tuberomammillary nucleus (TMN) — histaminergic "
                "wake-promotion, H1/H2 receptor-mediated cortical activation"
            ),
            layer="foundational",
        )
        self.state.setdefault("histamine_tone", self.BASELINE_TONE)
        self.state.setdefault("cortical_activation", 0.0)
        self.state.setdefault("attention_enhancement", 0.0)
        self.state.setdefault("h3_autoreceptor_suppression", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        mode = prior.get("ArousalRegulator", {}).get("mode", "alert")
        orexin_tone = prior.get("OrexinWakePromoter", {}).get("orexin_tone", 0.5)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        sleep_gate_open = prior.get("ThermoSleepGate", {}).get("sleep_gate_open", False)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)

        # ---- Orexin co-activation ----
        orexin_activation = orexin_tone * 0.30

        # ---- Sleep gate closes histamine ----
        sleep_suppression = 0.40 if sleep_gate_open else 0.0

        # ---- H3 autoreceptor suppression (proportional to histamine level) ----
        current_tone = self.state["histamine_tone"]
        h3_suppression = current_tone * 0.25

        # ---- Antihistamine-like suppression from gut distress ----
        pharmacological_suppression = gut_distress * 0.30

        # ---- Target histamine tone ----
        target_tone = (
            arousal_level * 0.45
            + orexin_activation
            - sleep_suppression
            - h3_suppression
            - pharmacological_suppression
        )
        target_tone = max(0.0, min(0.95, target_tone))

        # ---- Smooth convergence ----
        new_tone = current_tone + (target_tone - current_tone) * self.CONVERGENCE_RATE
        new_tone = round(new_tone, 4)

        # ---- H1-mediated cortical activation ----
        cortical_activation = round(new_tone * 0.85, 4)

        # ---- H2-mediated prefrontal attention enhancement ----
        if mode in ("alert", "creative"):
            attention_enhancement = new_tone * 0.75
        else:
            attention_enhancement = new_tone * 0.30
        attention_enhancement = round(attention_enhancement, 4)

        # ---- H3 autoreceptor signal ----
        h3_autoreceptor_suppression = round(min(0.60, new_tone * 0.30), 4)

        # Persist
        self.state["histamine_tone"] = new_tone
        self.state["cortical_activation"] = cortical_activation
        self.state["attention_enhancement"] = attention_enhancement
        self.state["h3_autoreceptor_suppression"] = h3_autoreceptor_suppression
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "histamine_tone": new_tone,
            "cortical_activation": cortical_activation,
            "attention_enhancement": attention_enhancement,
            "h3_autoreceptor_suppression": h3_autoreceptor_suppression,
        }
