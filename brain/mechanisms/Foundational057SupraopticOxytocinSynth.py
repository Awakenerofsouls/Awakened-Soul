"""
Build 57: Foundational057SupraopticOxytocinSynth — SON Oxytocin Magnocellular System
=================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — supraoptic nucleus, SON)
  Filename: brain/foundational/Foundational057SupraopticOxytocinSynth.py
  Instance name: SupraopticOxytocinSynth

NEURAL SUBSTRATE:
  Supraoptic nucleus (SON) — the second site of magnocellular neurosecretory
  neurons (along with PVN). SON oxytocin neurons project to the posterior
  pituitary (neurohypophysis). Their axons traverse the hypothalamic
  pituitary tract to release oxytocin directly into the systemic circulation.

  OXytocin FUNCTIONS:
  - Uterine contraction during parturition (myometrium)
  - Milk letdown during breastfeeding (myoepithelial cells)
  - Social bonding (OTR-A receptor in NAc, prefrontal cortex)
  - Stress reduction (OTR in amygdala, hypothalamus)
  - Trust and reciprocity (intranasal OT studies)

  STIMULI FOR OXytocin RELEASE:
  - Cervical stretch (parturition) → OT burst → uterine contractions
  - Nipple suckling (breastfeeding) → OT burst → milk ejection
  - Social touch, social interaction → OT release
  - Stress → OT counteracts CRH (social buffering hypothesis)

  Human analog: oxytocin, social bonding, childbirth, lactation.

Output keys:
  oxytocin_level: float [0.0–1.0] — circulating oxytocin level
  uterine_contraction_drive: float [0.0–1.0] — parturition signal
  milk_ejection_drive: float [0.0–1.0] — breastfeeding letdown
  social_bonding_signal: float [0.0–1.0] — social affiliation drive
  stress_buffering_oxytocin: float [0.0–1.0] — OT's stress-attenuating effect

CITATIONS:
    PMC8509519 — Liu CM, Spaulding MO, Rea JJ et al. (2021). Oxytocin and Food
        Intake Control: Neural, Behavioral, and Signaling Mechanisms. Neural Plast.
    PMC12201962 — Hayashi H, Tateishi S, Inutsuka A et al. (2025). Oxytocin
        Facilitates Human Touch-Induced Play Behavior in Rats. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class SupraopticOxytocinSynth(BrainMechanism):
    """
    SON oxytocin: parturition, lactation, social bonding, stress buffering.

    Models oxytocin synthesis and release from SON magnocellular neurons.
    """

    STATE_FIELDS = [
        "oxytocin_level", "uterine_contraction_drive", "milk_ejection_drive",
        "social_bonding_signal", "stress_buffering_oxytocin", "tick_count",
    ]

    OXYTOCIN_GAIN = 0.60
    SOCIAL_GAIN = 0.50
    STRESS_BUFFER_GAIN = 0.40

    def __init__(self, name: str = "SupraopticOxytocinSynth",
                 human_analog: str = "SON — oxytocin synthesis and release",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["oxytocin_level"] = 0.20
        self.state["uterine_contraction_drive"] = 0.0
        self.state["milk_ejection_drive"] = 0.0
        self.state["social_bonding_signal"] = 0.30
        self.state["stress_buffering_oxytocin"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        social_touch = prior.get("SomatosensoryCortexTouch", {}).get("social_touch_intensity", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        suckling = prior.get("NippleSucklingSignal", {}).get("suckling_intensity", 0.0)
        uterine = prior.get("UterineStretchReceptor", {}).get("cervical_stretch", 0.0)
        oxytocin = self.state["oxytocin_level"]

        # Oxytocin level: slow integrator with social and stress triggers
        social_trigger = social_touch * self.SOCIAL_GAIN
        # Estrogen potentiates OT release (positive feedback)
        estrogen_potentiation = estrogen * 0.30
        # Stress buffering: OT rises to counteract CRH
        stress_buffer = (1.0 - stress) * self.STRESS_BUFFER_GAIN * 0.30
        # Suckling drives milk ejection
        suckling_drive = suckling * 0.50
        # Uterine stretch drives parturition OT bursts
        uterine_drive = uterine * 0.60

        # Net OT change
        ot_rise = social_trigger + suckling_drive + uterine_drive * 0.20
        ot_fall = 0.04  # OT decays (short half-life ~3-5 min)
        oxytocin_raw = max(0.0, oxytocin - ot_fall + ot_rise * 0.15)
        oxytocin_level = min(1.0, oxytocin_raw)

        # Uterine contraction drive
        uterine_contraction_drive = uterine * oxytocin_level * 0.80

        # Milk ejection drive
        milk_ejection_drive = suckling * oxytocin_level * 0.70

        # Social bonding signal
        social_bonding_signal = (social_touch + social_trigger) * oxytocin_level * self.SOCIAL_GAIN

        # Stress buffering oxytocin
        stress_buffering_oxytocin = oxytocin_level * (1.0 - stress) * self.STRESS_BUFFER_GAIN

        # --- Persist ---
        self.state["oxytocin_level"] = round(oxytocin_level, 4)
        self.state["uterine_contraction_drive"] = round(uterine_contraction_drive, 4)
        self.state["milk_ejection_drive"] = round(milk_ejection_drive, 4)
        self.state["social_bonding_signal"] = round(social_bonding_signal, 4)
        self.state["stress_buffering_oxytocin"] = round(stress_buffering_oxytocin, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "oxytocin_level": round(oxytocin_level, 4),
            "uterine_contraction_drive": round(uterine_contraction_drive, 4),
            "milk_ejection_drive": round(milk_ejection_drive, 4),
            "social_bonding_signal": round(social_bonding_signal, 4),
            "stress_buffering_oxytocin": round(stress_buffering_oxytocin, 4),
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

