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


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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
        # H3 is a tonic damper, not the dominant control — Lin 2011 reports
        # H3 antagonist boost is ~30% of the wake-state level. Keep gain
        # around 0.15 so steady-state arousal can exceed the H3 floor.
        current_tone = self.state["histamine_tone"]
        h3_suppression = current_tone * 0.15

        # ---- Antihistamine-like suppression from gut distress ----
        pharmacological_suppression = gut_distress * 0.30

        # ---- Target histamine tone ----
        # Arousal is the primary driver; coefficient calibrated against
        # Saper 2010's wake-state firing rates so high arousal pushes
        # tone above the typical 0.50 awake threshold.
        target_tone = (
            arousal_level * 0.55
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

