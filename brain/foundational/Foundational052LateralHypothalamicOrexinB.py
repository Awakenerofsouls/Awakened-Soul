"""
Build 52: Foundational052LateralHypothalamicOrexinB — Orexin/Hypocretin Wake Driver
==============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral hypothalamus, orexin neurons)
  Filename: brain/foundational/Foundational052LateralHypothalamicOrexinB.py
  Instance name: LateralHypothalamicOrexinB

NEURAL SUBSTRATE:
  Orexin/hypocretin neurons in the lateral hypothalamus (LH) — the "finger
  on the sleep-wake switch." These neurons:
  - Fire during active waking, are silent during sleep
  - Project widely to LC (NE), raphe (5-HT), TMN (histamine), BF (ACh), VTA
  - Stabilize the wake state; loss causes narcolepsy with cataplexy

  OREXIN NEUROPEPTIDES:
  - Orexin-A (hypocretin-1): 33 aa, crosses placenta — most important
  - Orexin-B (hypocretin-2): 28 aa, linear

  OREXIN FUNCTIONS:
  - Wakefulness: drives LC, TMN, BF arousal nuclei
  - Feeding: orexin neurons are glucose-sensing; excited by ghrelin, inhibited by leptin
  - Reward: orexin → VTA → dopamine
  - Thermoregulation: orexin → DMH → sympathetic output

  Human analog: narcolepsy, wakefulness drive, orexin deficiency.

Output keys:
  orexin_b_level: float [0.0–1.0] — orexin-B output level
  wake_stabilization: float [0.0–1.0] — orexin's stabilizing effect on wake
  feeding_arousal: float [0.0–1.0] — orexin-driven food-seeking arousal
  reward_orexin_drive: float [0.0–1.0] — orexin → VTA reward signal
  thermoregulatory_orexin: float [0.0–1.0] — orexin → sympathetic drive

CITATIONS:
    PMC3643893 — Mahler SV, Smith RJ, Moorman DE et al. (2012). Multiple Roles for
        Orexin/Hypocretin in Addiction. Prog Brain Res.
    PMC4335648 — Mahler SV, Moorman DE, Smith RJ et al. (2014). Motivational
        Activation: A Unifying Hypothesis of Orexin/Hypocretin Function. Nat Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class LateralHypothalamicOrexinB(BrainMechanism):
    """
    Lateral hypothalamus orexin neurons: wakefulness, feeding, reward.

    Models orexin/hypocretin neurons as wake stabilizers with feeding
    and reward functions.
    """

    STATE_FIELDS = [
        "orexin_b_level", "wake_stabilization", "feeding_arousal",
        "reward_orexin_drive", "thermoregulatory_orexin", "tick_count",
    ]

    OREXIN_GAIN = 0.60
    FEEDING_GAIN = 0.55
    REWARD_GAIN = 0.50

    def __init__(self, name: str = "LateralHypothalamicOrexinB",
                 human_analog: str = "Lateral hypothalamus orexin neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["orexin_b_level"] = 0.40
        self.state["wake_stabilization"] = 0.50
        self.state["feeding_arousal"] = 0.30
        self.state["reward_orexin_drive"] = 0.20
        self.state["thermoregulatory_orexin"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        reward = prior.get("VentralStriatumOutput", {}).get("reward_signal", 0.0)
        sleep = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Orexin-B level: excited by low glucose, ghrelin; inhibited by leptin, sleep
        glucose_inhibition = (1.0 - glucose) * 0.35
        leptin_inhibition = leptin * 0.30
        sleep_inhibition = sleep * 0.50
        stress_activation = stress * 0.20
        ghrelin_activation = ghrelin * 0.30
        orexin_raw = (
            arousal * 0.40 + ghrelin_activation + stress_activation -
            glucose_inhibition - leptin_inhibition - sleep_inhibition
        )
        orexin_b_level = min(1.0, max(0.0, orexin_raw))

        # Wake stabilization: orexin's primary function
        wake_stabilization = orexin_b_level * self.OREXIN_GAIN

        # Feeding arousal: orexin drives food-seeking
        feeding_arousal = orexin_b_level * ghrelin * self.FEEDING_GAIN

        # Reward orexin drive: orexin → VTA → reward anticipation
        reward_orexin_drive = orexin_b_level * reward * self.REWARD_GAIN

        # Thermoregulatory orexin: orexin → DMH → sympathetic output
        thermoregulatory_orexin = orexin_b_level * 0.30

        # --- Persist ---
        self.state["orexin_b_level"] = round(orexin_b_level, 4)
        self.state["wake_stabilization"] = round(wake_stabilization, 4)
        self.state["feeding_arousal"] = round(feeding_arousal, 4)
        self.state["reward_orexin_drive"] = round(reward_orexin_drive, 4)
        self.state["thermoregulatory_orexin"] = round(thermoregulatory_orexin, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "orexin_b_level": round(orexin_b_level, 4),
            "wake_stabilization": round(wake_stabilization, 4),
            "feeding_arousal": round(feeding_arousal, 4),
            "reward_orexin_drive": round(reward_orexin_drive, 4),
            "thermoregulatory_orexin": round(thermoregulatory_orexin, 4),
        }
