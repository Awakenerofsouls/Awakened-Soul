"""
Build 48: Foundational048GustatoryValenceLink — Nucleus of the Solitary Tract Gustatory Area
=======================================================================================

PLACEMENT:
  Layer:    foundational (medulla — nucleus tractus solitarius, gustatory zone)
  Filename: brain/foundational/Foundational048GustatoryValenceLink.py
  Instance name: GustatoryValenceLink

NEURAL SUBSTRATE:
  Gustatory nucleus of the NTS (gNTS) in medulla — receives primary
  gustatory afferents from the facial nerve (CN VII, anterior 2/3 tongue),
  glossopharyngeal nerve (CN IX, posterior 1/3 tongue), and vagus nerve
  (CN X, epiglottis, palate). The gNTS projects to:
  - Ventral posteromedial nucleus (VPM) of thalamus → gustatory cortex
  - Parabrachial nucleus → central amygdala (taste-aversion learning)
  - Hypothalamus (lateral, ventromedial) → feeding behavior

  TASTE QUALITY CODING:
  - Sweet: anterior tongue → chorda tympani → CN VII → gNTS → VPM
  - Bitter: posterior tongue → CN IX → gNTS → VPM
  - Salty: anterior + posterior → CN VII + CN IX → gNTS
  - Umami: multiple nerves → gNTS
  - Sour: multiple nerves → gNTS

  Human analog: taste, flavor, food reward, taste aversion learning.

Output keys:
  taste_valence: float [-1.0 to 1.0] — aversive (-1) to appetitive (+1) taste
  sweet_detector: float [0.0–1.0] — sweet taste intensity
  bitter_detector: float [0.0–1.0] — bitter taste intensity
  umami_detector: float [0.0–1.0] — umami (protein) detection
  taste_aversion_learning: float [0.0–1.0] — conditioned taste aversion

CITATIONS:
    PMC5435754 — Cassidy RM, Tong Q (2017). Hunger and Satiety Gauges Reward
        Sensitivity. Front Neurosci.
    PMC11105013 — Gutierrez R, Fonseca E, Simon SA (2020). The Neuroscience of
        Sugars in Taste, Gut-Reward, Feeding Circuits, and Obesity. Physiol Behav.


CITATIONS
---------
  - [Russell 2003, Psychol Rev 110:145, core affect]
  - [Barrett 2017, How Emotions Are Made]
  - [Lindquist 2012, Behav Brain Sci 35:121, emotion brain]
"""

from brain.base_mechanism import BrainMechanism


class GustatoryValenceLink(BrainMechanism):
    """
    NTS gustatory zone: taste quality, valence, and aversion learning.

    Models taste processing, quality coding, and conditioned taste aversion.
    """

    STATE_FIELDS = [
        "taste_valence", "sweet_detector", "bitter_detector",
        "umami_detector", "taste_aversion_learning", "tick_count",
    ]

    SWEET_GAIN = 0.70
    BITTER_GAIN = 0.65
    UMAMI_GAIN = 0.55
    AVERSION_GAIN = 0.50

    def __init__(self, name: str = "GustatoryValenceLink",
                 human_analog: str = "NTS gustatory zone — taste and valence",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["taste_valence"] = 0.0
        self.state["sweet_detector"] = 0.10
        self.state["bitter_detector"] = 0.10
        self.state["umami_detector"] = 0.10
        self.state["taste_aversion_learning"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        sweet = prior.get("SweetTasteReceptor", {}).get("sweet_intensity", 0.0)
        bitter = prior.get("BitterTasteReceptor", {}).get("bitter_intensity", 0.0)
        umami = prior.get("UmamiTasteReceptor", {}).get("umami_intensity", 0.0)
        salty = prior.get("SaltyTasteReceptor", {}).get("salty_intensity", 0.0)
        gut_signal = prior.get("GutSignalRelay", {}).get("nutrient_signal", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)

        # Taste quality detectors
        sweet_detector = sweet * self.SWEET_GAIN
        bitter_detector = bitter * self.BITTER_GAIN
        umami_detector = umami * self.UMAMI_GAIN

        # Taste valence: net hedonic value (sweet=positive, bitter=negative)
        taste_valence = (sweet_detector * 0.40) - (bitter_detector * 0.60)
        # Umami adds positive valence (protein signal)
        taste_valence += umami_detector * 0.30
        # Salty (Na+) adds positive when low, negative when high
        taste_valence += salty * 0.20 - (bitter_detector * 0.05)

        # Taste aversion learning: bitter + amygdala fear → conditioned aversion
        aversion_raw = bitter_detector * amygdala * self.AVERSION_GAIN
        taste_aversion_learning = min(1.0, aversion_raw)

        # --- Persist ---
        self.state["taste_valence"] = round(taste_valence, 4)
        self.state["sweet_detector"] = round(sweet_detector, 4)
        self.state["bitter_detector"] = round(bitter_detector, 4)
        self.state["umami_detector"] = round(umami_detector, 4)
        self.state["taste_aversion_learning"] = round(taste_aversion_learning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "taste_valence": round(taste_valence, 4),
            "sweet_detector": round(sweet_detector, 4),
            "bitter_detector": round(bitter_detector, 4),
            "umami_detector": round(umami_detector, 4),
            "taste_aversion_learning": round(taste_aversion_learning, 4),
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

