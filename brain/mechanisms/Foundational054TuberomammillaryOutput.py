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


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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

