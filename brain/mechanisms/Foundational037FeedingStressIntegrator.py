"""
Build 37: Foundational037FeedingStressIntegrator — Lateral Hypothalamus Feeding + Stress
=====================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral hypothalamus, LHA)
  Filename: brain/foundational/Foundational037FeedingStressIntegrator.py
  Instance name: FeedingStressIntegrator

NEURAL SUBSTRATE:
  Lateral hypothalamus (LHA) — the "hunger center." Contains:
  - Orexin/hypocretin neurons: wake-promoting, also drive food-seeking
  - MCH (melanin-concentrating hormone) neurons: orexigenic, promote feeding
  - NPY/AgRP terminals from arcuate: orexigenic, directly innervate LHA
  - GABAergic "feeding neurons": stimulation → eating; lesion → starvation

  LHA projects to:
  - Ventral tegmental area (VTA): reward for food
  - Paraventricular nucleus (PVN): stress response integration
  - Lateral habenula: aversion signals

  STRESS-FEEDING INTERACTION: Acute stress suppresses feeding via CRH.
  Chronic stress can drive "comfort eating" via NPY from arcuate.
  Leptin signals energy sufficiency → suppresses LHA feeding drive.

  Human analog: hunger, food-seeking, stress eating, leptin suppression.

Output keys:
  feeding_drive: float [0.0–1.0] — hunger motivation intensity
  food_seeking_arousal: float [0.0–1.0] — orexin-driven food search motivation
  leptin_suppression: float [0.0–1.0] — satiety-mediated feeding suppression
  stress_anorexia: float [0.0–1.0] — acute stress suppression of feeding
  lha_integrator: float [0.0–1.0] — composite LHA output

CITATIONS:
    PMC11164563 — DiFazio LE, Fanselow M, Sharpe MJ (2022). The Effect of Stress and
        Reward on Encoding Future Fear Memories. Learn Mem.
    PMC9436700 — Meisner OC, Nair A, Chang SWC (2022). Amygdala Connectivity and
        Implications for Social Cognition and Disorders. Front Neurosci.


CITATIONS
---------
  - [McEwen 1998, N Engl J Med 338:171, allostatic load]
  - [Sapolsky 2000, Endocr Rev 21:55, glucocorticoids]
  - [Joels 2009, Nat Rev Neurosci 10:459, stress]
"""

from brain.base_mechanism import BrainMechanism


class FeedingStressIntegrator(BrainMechanism):
    """
    Lateral hypothalamus: feeding drive, stress-feeding interactions.

    Models the hunger center, integrating metabolic signals (leptin, ghrelin)
    and stress signals to drive feeding behavior.
    """

    STATE_FIELDS = [
        "feeding_drive", "food_seeking_arousal", "leptin_suppression",
        "stress_anorexia", "lha_integrator", "tick_count",
    ]

    FEEDING_GAIN = 0.55
    SEEKING_GAIN = 0.50
    LEPTIN_GAIN = 0.45
    STRESS_ANOREXIA_GAIN = 0.60

    def __init__(self, name: str = "FeedingStressIntegrator",
                 human_analog: str = "Lateral hypothalamus — feeding drive and stress",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["feeding_drive"] = 0.40
        self.state["food_seeking_arousal"] = 0.30
        self.state["leptin_suppression"] = 0.20
        self.state["stress_anorexia"] = 0.0
        self.state["lha_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        npy = prior.get("AppetiteNPYBalancer", {}).get("npy_level", 0.30)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        glucagon = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)

        # Leptin suppression: high leptin = energy sufficiency = stop eating
        leptin_suppression = leptin * self.LEPTIN_GAIN

        # Stress anorexia: CRH acutely suppresses feeding
        stress_anorexia = stress * self.STRESS_ANOREXIA_GAIN

        # Feeding drive: ghrelin + NPY - leptin suppression - stress anorexia
        feeding_raw = (ghrelin * 0.35) + (npy * 0.35) - leptin_suppression - stress_anorexia
        feeding_drive = max(0.0, min(1.0, feeding_raw))

        # Food seeking arousal: orexin drives exploration/food-seeking
        food_seeking = orexin * self.SEEKING_GAIN
        # Low glucose drives food seeking
        food_seeking += (1.0 - glucagon) * 0.25
        food_seeking = min(1.0, food_seeking)

        # LHA integrator: composite output
        lha_integrator = (feeding_drive + food_seeking) / 2.0

        # --- Persist ---
        self.state["feeding_drive"] = round(feeding_drive, 4)
        self.state["food_seeking_arousal"] = round(food_seeking, 4)
        self.state["leptin_suppression"] = round(leptin_suppression, 4)
        self.state["stress_anorexia"] = round(stress_anorexia, 4)
        self.state["lha_integrator"] = round(lha_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "feeding_drive": round(feeding_drive, 4),
            "food_seeking_arousal": round(food_seeking, 4),
            "leptin_suppression": round(leptin_suppression, 4),
            "stress_anorexia": round(stress_anorexia, 4),
            "lha_integrator": round(lha_integrator, 4),
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

