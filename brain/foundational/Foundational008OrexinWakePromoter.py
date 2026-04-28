"""
Build 17: Foundational008OrexinWakePromoter — Lateral Hypothalamic Orexin System
===============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamic — lateral hypothalamic area)
  Filename: brain/foundational/Foundational008OrexinWakePromoter.py
  Instance name: OrexinWakePromoter

NEURAL SUBSTRATE:
  Lateral hypothalamic orexin (hypocretin) neurons. Orexin-A and
  orexin-B are synthesized exclusively in the LHA and project
  widely to subcortical and brainstem wake-promoting centers.
  Loss of orexin neurons causes narcolepsy with cataplexy — complete
  loss of orexin signaling produces the full clinical syndrome.

  Orexin neurons are state-selective: they fire during active waking
  (especially active exploration, foraging, grooming), fall silent
  during NREM and REM sleep, and are suppressed by sleep-promoting
  GABAergic neurons in the ventrolateral preoptic area (VLPO).
  They excite LC-NE, dorsal raphe 5-HT, and histaminergic TMN —
  the three major waking neuromodulatory systems.

  Two orexin receptor subtypes: OX1R (preferred orexin-A) and
  OX2R (equal affinity for A and B). OX2R knockout alone produces
  narcolepsy in dogs; OX1R/OX2R double knockout produces it in mice.

KEY FINDINGS:
  1. Orexin neuron firing is tightly coupled to behavioral state
     transitions: they fire at 3-10 Hz during active waking,
     immediately cease during sleep onset (Mileykovskiy et al.
     2005, J Neurosci). Silent during both NREM and REM.
  2. Orexin tone is the primary determinant of wake episode duration —
     high orexin tone = long, stable wake; low tone = short fragments
     of wake interrupted by sleep intrusions (narcolepsy = <20% normal
     orexin cell count, Thannickal et al. 2000, J Neurosci).
  3. OX2R is the critical receptor for sleep-wake regulation —
     canine narcolepsy is caused by OX2R loss-of-function mutation
     (Lin et al. 1999, Cell). OX1R alone cannot sustain wake.
  4. Afferents to orexin neurons: amygdala (emotional arousal),
     hypothalamus (energy state via glucose sensing), brainstem
     (behavioral state feedback). All project bidirectionally.
  5. Metabolic cues modulate orexin: low glucose activates orexin
     neurons (hunger-promoting wake), high glucose suppresses them.
     AgRP (hunger hormone) activates orexin; leptin suppresses
     [UNVERIFIED: Burke & Makey 2014 — verify or replace; suggests
     searching Burke+orexin+glucose or Batterham+orexin on PubMed].

INPUTS (prior_results):
  - ArousalRegulator: arousal_level (float 0-1), mode (str)
  - Homeostat: dominant_drive (str), metabolic_state (str)
  - PredictionErrorDrift: uncertainty (float 0-1)
  - StressActivationAxis: crh_level (float 0-1)

OUTPUTS:
  - orexin_tone: float 0.0-1.0 (current orexin activation level)
  - wake_stability: float 0.0-1.0 (fragmentation resistance)
  - sleep_pressure: float 0.0-1.0 (counter驱动 by orexin suppression)
  - metabolic_modulation: float (glucose/metabolic influence)

CITATIONS:
    PMC2938067 — Arrigoni E, Mochizuki T, Scammell TE (2010). Activation of the Basal
        Forebrain by the Orexin/Hypocretin Neurones. Prog Brain Res.
    PMC4335648 — Mahler SV, Moorman DE, Smith RJ et al. (2014). Motivational
        Activation: A Unifying Hypothesis of Orexin/Hypocretin Function. Nat Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class OrexinWakePromoter(BrainMechanism):
    """
    Lateral hypothalamic orexin (hypocretin) wake-promoting system.

    Orexin neurons fire during active waking, excite LC/DR/TMN.
    OX2R is the primary receptor mediating wake stability.
    Suppressed by VLPO sleep signals and metabolic cues.
    """

    # Baseline orexin tone (moderate during waking)
    BASELINE_TONE = 0.55

    # Convergence rate
    TONE_CONVERGENCE = 0.20

    # Drive modulation magnitudes
    DRIVE_CURIOSITY_BOOST = 0.22
    DRIVE_EXPRESSION_BOOST = 0.15
    DRIVE_REST_SUPPRESSION = 0.35

    def __init__(self):
        super().__init__(
            name="OrexinWakePromoter",
            human_analog=(
                "Lateral hypothalamic orexin/hypocretin neurons — "
                "wake-promoting, OX2R-mediated, metabolic state-modulated"
            ),
            layer="foundational",
        )
        self.state.setdefault("orexin_tone", self.BASELINE_TONE)
        self.state.setdefault("wake_stability", 0.70)
        self.state.setdefault("sleep_pressure", 0.30)
        self.state.setdefault("metabolic_modulation", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        mode = prior.get("ArousalRegulator", {}).get("mode", "alert")
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        metabolic_state = prior.get("Homeostat", {}).get("metabolic_state", "fed")
        uncertainty = prior.get("PredictionErrorDrift", {}).get("uncertainty", 0.3)
        crh_level = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)

        # ---- Arousal coupling: orexin tracks active waking ----
        if mode in ("alert", "creative"):
            arousal_target = arousal_level
        elif mode == "hyperaroused":
            arousal_target = min(1.0, arousal_level + 0.15)  # hyperarousal boosts orexin
        else:
            arousal_target = arousal_level * 0.50  # drowsy = suppressed

        # ---- Drive modulation ----
        if dominant_drive == "curiosity":
            drive_mod = self.DRIVE_CURIOSITY_BOOST
        elif dominant_drive == "expression":
            drive_mod = self.DRIVE_EXPRESSION_BOOST
        elif dominant_drive == "rest":
            drive_mod = -self.DRIVE_REST_SUPPRESSION
        else:
            drive_mod = 0.0

        # ---- Metabolic modulation ----
        if metabolic_state == "hungry":
            metabolic_mod = 0.15
        else:
            metabolic_mod = 0.0

        # ---- Stress/uncertainty: orexin fights sleep pressure ----
        uncertainty_mod = uncertainty * 0.15

        # CRH: acute stress activates orexin (defense → stay awake)
        crh_mod = crh_level * 0.10

        # ---- Compute target orexin tone ----
        target_tone = (
            arousal_target * 0.50
            + drive_mod
            + metabolic_mod
            + uncertainty_mod
            + crh_mod
        )
        target_tone = max(0.05, min(0.95, target_tone))

        # ---- Smooth convergence ----
        current_tone = self.state["orexin_tone"]
        new_tone = current_tone + (target_tone - current_tone) * self.TONE_CONVERGENCE
        new_tone = round(new_tone, 4)

        # ---- Wake stability: proportional to orexin tone ----
        wake_stability = round(new_tone * 0.90, 4)

        # ---- Sleep pressure: inversely proportional to orexin ----
        sleep_pressure = round(1.0 - new_tone, 4)

        # Persist
        self.state["orexin_tone"] = new_tone
        self.state["wake_stability"] = wake_stability
        self.state["sleep_pressure"] = sleep_pressure
        self.state["metabolic_modulation"] = round(metabolic_mod, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "orexin_tone": new_tone,
            "wake_stability": wake_stability,
            "sleep_pressure": sleep_pressure,
            "metabolic_modulation": round(metabolic_mod, 4),
        }
