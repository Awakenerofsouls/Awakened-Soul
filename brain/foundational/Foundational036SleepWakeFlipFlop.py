"""
Build 36: Foundational036SleepWakeFlipFlop — Sleep-Wake Switch (Saper Model)
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus + brainstem — VLPO/subcoeruleus vs orexin/LC)
  Filename: brain/foundational/Foundational036SleepWakeFlipFlop.py
  Instance name: SleepWakeFlipFlop

NEURAL SUBSTRATE:
  The flip-flop switch model (Saper et al. 2001): mutually inhibitory populations
  form a bistable switch:
  - SLEEP SIDE: VLPO + subcoeruleus (sleep-promoting, GABAergic, galaninergic)
  - WAKE SIDE: orexin/hypocretin neurons (LH) + LC (norepinephrine) +
    tuberomammillary (histamine) + dorsal raphe (serotonin)

  The orexin neurons are the "finger on the switch" — they stabilize waking.
  Loss of orexin (narcolepsy) causes REM intrusion because the wake side
  cannot be stably maintained: the flip-flop becomes unstable.

  Homeostatic sleep pressure (adenosine) shifts the balance toward sleep.
  Circadian arousal (SCN) shifts toward wake.

  Human analog: sleep-wake transitions, narcolepsy, insomnia.

Output keys:
  flipflop_state: float [0.0–1.0] — 0=all-sleep, 1=all-wake
  sleep_dominance: float [0.0–1.0] — VLPO/SubC drive (sleep-promoting)
  wake_dominance: float [0.0–1.0] — orexin/LC drive (wake-promoting)
  switch_stability: float [0.0–1.0] — stability of current state
  narcoleptic_collapse: float [0.0–1.0] — REM intrusion probability

CITATIONS:
    PMC8954377 — Arrigoni E, Fuller PM (2022). The Sleep-Promoting Ventrolateral
        Preoptic Nucleus: What Have We Learned Over the Past 25 Years? Int J Mol Sci.
    PMC3996219 — Williams RH, Chee MJ, Kroeger D et al. (2014). Optogenetic-Mediated
        Release of Histamine Reveals Distal and Autoregulatory Mechanisms for
        Controlling Arousal. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class SleepWakeFlipFlop(BrainMechanism):
    """
    Sleep-wake flip-flop switch: VLPO/SubC vs orexin/LC.

    Implements the mutually inhibitory switch with orexin as the
    wake-stabilizing element. Models narcoleptic collapse when
    orexin is deficient.
    """

    STATE_FIELDS = [
        "flipflop_state", "sleep_dominance", "wake_dominance",
        "switch_stability", "narcoleptic_collapse", "tick_count",
    ]

    SLEEP_GAIN = 0.40
    WAKE_GAIN = 0.45
    STABILITY_THRESHOLD = 0.15

    def __init__(self, name: str = "SleepWakeFlipFlop",
                 human_analog: str = "VLPO/SubC ↔ orexin/LC flip-flop switch",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["flipflop_state"] = 0.50  # start balanced
        self.state["sleep_dominance"] = 0.40
        self.state["wake_dominance"] = 0.40
        self.state["switch_stability"] = 0.80
        self.state["narcoleptic_collapse"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        subc = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        lc = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        histamine = prior.get("HistamineArousalBooster", {}).get("histamine_level", 0.30)
        homeostatic = prior.get("Homeostat", {}).get("cumulative_pressure", 0.30)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)

        # Sleep dominance: VLPO + SubC (combined)
        sleep_dominance = (vlpo * 0.60) + (subc * 0.40)
        # Homeostatic pressure shifts sleep dominance up
        sleep_dominance += homeostatic * 0.30

        # Wake dominance: orexin + LC + histamine (combined)
        wake_dominance = (orexin * 0.40) + (lc * 0.30) + (histamine * 0.30)
        # Circadian adds to wake
        wake_dominance += circadian * 0.20

        # Mutual inhibition: each side suppresses the other
        sleep_inhibits_wake = sleep_dominance * 0.20
        wake_inhibits_sleep = wake_dominance * 0.20
        net_sleep = max(0.0, sleep_dominance - wake_inhibits_sleep)
        net_wake = max(0.0, wake_dominance - sleep_inhibits_wake)

        # Flip-flop state: net balance
        total = net_sleep + net_wake
        if total > 0:
            flipflop_state = net_wake / total
        else:
            flipflop_state = 0.5

        # Switch stability: how far from midpoint (higher = more stable)
        stability = abs(flipflop_state - 0.5) * 2.0

        # Narcoleptic collapse: when orexin is low AND sleep pressure is high
        # The flip-flop becomes unstable — REM can intrude into wake
        narcoleptic_risk = (1.0 - orexin) * homeostatic * 0.60
        narcoleptic_collapse = min(1.0, narcoleptic_risk)

        # --- Persist ---
        self.state["flipflop_state"] = round(flipflop_state, 4)
        self.state["sleep_dominance"] = round(net_sleep, 4)
        self.state["wake_dominance"] = round(net_wake, 4)
        self.state["switch_stability"] = round(stability, 4)
        self.state["narcoleptic_collapse"] = round(narcoleptic_collapse, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "flipflop_state": round(flipflop_state, 4),
            "sleep_dominance": round(net_sleep, 4),
            "wake_dominance": round(net_wake, 4),
            "switch_stability": round(stability, 4),
            "narcoleptic_collapse": round(narcoleptic_collapse, 4),
        }
