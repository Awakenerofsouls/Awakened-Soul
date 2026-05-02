"""
Build 55: Foundational055TuberomammillaryInhibitor — VLPO → TMN Inhibition
====================================================================

PLACEMENT:
  Layer:    foundational (pons — VLPO → TMN synaptic interface)
  Filename: brain/foundational/Foundational055TuberomammillaryInhibitor.py
  Instance name: TuberomammillaryInhibitor

NEURAL SUBSTRATE:
  VLPO → TMN GABAergic/symmetric projection. This is one of the key
  reciprocal inhibitory connections in the sleep-wake switch:
  - VLPO fires during sleep → GABA release onto TMN → TMN histamine silenced
  - TMN fires during wake → histamine release onto VLPO → VLPO silenced

  The VLPO-TMN projection is part of the mutual inhibition that creates
  the flip-flop switch. The VLPO also sends projections to the
  locus coeruleus, raphe, and orexin neurons.

  KEY NEUROTRANSMITTER: Galanin — co-released with GABA from VLPO terminals
  onto wake-promoting neurons. Galanin is a neuropeptide that provides
  long-duration inhibition of TMN and LC.

  Human analog: sleep onset (VLPO silencing TMN → drowsiness).

Output keys:
  vlpO_tmn_inhibition: float [0.0–1.0] — VLPO → TMN GABA/galanin inhibition
  histamine_suppression: float [0.0–1.0] — resulting histamine suppression
  sleep_wake_transition: float [0.0–1.0] — transition signal (0=sleep, 1=wake)
  galanin_release: float [0.0–1.0] — galanin co-transmitter output
  flipflop_integrator: float [0.0–1.0] — VLPO-TMN reciprocal inhibition state

CITATIONS:
    PMC6832676 — Venner A, Mochizuki T, De Luca R et al. (2019). Reassessing the
        Role of Histaminergic Tuberomammillary Neurons in Arousal Control. J Neurosci.
    PMC3002444 — Liu YW, Li J, Ye JH (2010). Histamine Regulates Activities of
        Neurons in the Ventrolateral Preoptic Nucleus. J Pharmacol Sci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class TuberomammillaryInhibitor(BrainMechanism):
    """
    VLPO → TMN GABAergic inhibition: sleep-wake transition mechanism.

    Models the VLPO inhibition of TMN as the sleep-onset mechanism.
    """

    STATE_FIELDS = [
        "vlpo_tmn_inhibition", "histamine_suppression", "sleep_wake_transition",
        "galanin_release", "flipflop_integrator", "tick_count",
    ]

    INHIBITION_GAIN = 0.55
    GALANIN_GAIN = 0.40
    FLIPFLOP_GAIN = 0.50

    def __init__(self, name: str = "TuberomammillaryInhibitor",
                 human_analog: str = "VLPO → TMN GABA/galanin projection",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vlpo_tmn_inhibition"] = 0.0
        self.state["histamine_suppression"] = 0.0
        self.state["sleep_wake_transition"] = 0.50
        self.state["galanin_release"] = 0.0
        self.state["flipflop_integrator"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        histamine = prior.get("TuberomammillaryOutput", {}).get("histamine_output", 0.30)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        sleep_quiescence = prior.get("SleepWakeFlipFlop", {}).get("sleep_dominance", 0.0)
        homeostatic = prior.get("Homeostat", {}).get("cumulative_pressure", 0.30)

        # VLPO → TMN inhibition: VLPO drives this during sleep
        vlpo_tmn_inhibition = vlpo * self.INHIBITION_GAIN

        # Histamine suppression: consequence of VLPO inhibiting TMN
        histamine_suppression = vlpo_tmn_inhibition * 0.70

        # Sleep-wake transition: low = sleep onset, high = wake
        # Driven by VLPO activity
        transition_raw = 0.50 - (vlpo * self.FLIPFLOP_GAIN)
        sleep_wake_transition = max(0.0, min(1.0, transition_raw))

        # Galanin release: co-released with GABA from VLPO
        galanin_release = vlpo * self.GALANIN_GAIN
        galanin_release = min(1.0, galanin_release)

        # Flip-flop integrator: net state of the reciprocal inhibition
        orexin_excitation = orexin * 0.40
        vlpo_inhibition = vlpo_tmn_inhibition * 0.60
        flipflop_integrator = 0.50 + (orexin_excitation - vlpo_inhibition)

        # --- Persist ---
        self.state["vlpo_tmn_inhibition"] = round(vlpo_tmn_inhibition, 4)
        self.state["histamine_suppression"] = round(histamine_suppression, 4)
        self.state["sleep_wake_transition"] = round(sleep_wake_transition, 4)
        self.state["galanin_release"] = round(galanin_release, 4)
        self.state["flipflop_integrator"] = round(flipflop_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vlpo_tmn_inhibition": round(vlpo_tmn_inhibition, 4),
            "histamine_suppression": round(histamine_suppression, 4),
            "sleep_wake_transition": round(sleep_wake_transition, 4),
            "galanin_release": round(galanin_release, 4),
            "flipflop_integrator": round(flipflop_integrator, 4),
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

