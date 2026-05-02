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


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

