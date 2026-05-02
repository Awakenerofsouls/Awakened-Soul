"""
Build 60: Foundational060LateralTuberalNucleusOutput — Lateral Tuberal Nucleus Integration
================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral tuberal nucleus)
  Filename: brain/foundational/Foundational060LateralTuberalNucleusOutput.py
  Instance name: LateralTuberalNucleusOutput

NEURAL SUBSTRATE:
  Lateral tuberal nucleus (LTN) — a hypothalamic nucleus adjacent to
  the lateral hypothalamus, poorly understood but implicated in:
  - Integration of metabolic and autonomic signals
  - Projects to the bed nucleus of the stria terminalis (BNST)
  - Connected to lateral hypothalamus and zona incerta
  - Contains neurotensin and NPY neurons

  The LTN is part of the extended lateral hypothalamic area and
  integrates multiple drives: hunger, thirst, sexual motivation,
  and defensive behaviors.

  Human analog: general drive integration, hypothalamic motivation.

Output keys:
  ltn_integrator: float [0.0–1.0] — composite drive integrator output
  motivational_weight: float [0.0–1.0] — motivational salience weighting
  drive_coordination: float [0.0–1.0] — coordination of multiple drives
  ltn_threat_response: float [0.0–1.0] — threat-driven activation
  lateral_tuberal_composite: float [0.0–1.0] — total LTN output

CITATIONS:
    PMC10135972 — Vraka K, Mytilinaios D, Katsenos AP et al. (2023). Cellular
        Localization of Orexin 1 Receptor in Human Hypothalamus. Neuropeptides.
    PMC12293592 — Chen X, Wang Y, Fu S et al. (2025). The Integrated Function of
        the Lateral Hypothalamus in Energy Homeostasis. Nat Commun.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class LateralTuberalNucleusOutput(BrainMechanism):
    """
    Lateral tuberal nucleus: general drive integration.

    Models the LTN as a general-purpose drive integrator.
    """

    STATE_FIELDS = [
        "ltn_integrator", "motivational_weight", "drive_coordination",
        "ltn_threat_response", "lateral_tuberal_composite", "tick_count",
    ]

    INTEGRATOR_GAIN = 0.50
    THREAT_GAIN = 0.45

    def __init__(self, name: str = "LateralTuberalNucleusOutput",
                 human_analog: str = "Lateral tuberal nucleus — drive integrator",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["ltn_integrator"] = 0.40
        self.state["motivational_weight"] = 0.30
        self.state["drive_coordination"] = 0.40
        self.state["ltn_threat_response"] = 0.0
        self.state["lateral_tuberal_composite"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        feeding = prior.get("FeedingStressIntegrator", {}).get("feeding_drive", 0.30)
        thirst = prior.get("FacialGradientSensor", {}).get("thirst_drive", 0.20)
        sexual = prior.get("ThermoSexualBalancer", {}).get("sexual_motivation", 0.30)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)

        # LTN integrator: sums all drives
        drive_sum = feeding + thirst + sexual + arousal
        ltn_integrator = min(1.0, drive_sum * self.INTEGRATOR_GAIN * 0.25)

        # Motivational weight: highest drive dominates
        drives = [feeding, thirst, sexual, arousal]
        max_drive = max(drives)
        motivational_weight = max_drive

        # Drive coordination: how well competing drives are coordinated
        # Low variance = well-coordinated; high variance = conflict
        drive_mean = sum(drives) / len(drives)
        drive_variance = sum((d - drive_mean) ** 2 for d in drives) / len(drives)
        drive_coordination = max(0.0, 1.0 - drive_variance * 2.0)

        # LTN threat response: stress and amygdala activate LTN
        ltn_threat = stress * self.THREAT_GAIN + amygdala * 0.30
        ltn_threat_response = min(1.0, ltn_threat)

        # Lateral tuberal composite
        lateral_tuberal_composite = (ltn_integrator + motivational_weight + ltn_threat_response) / 3.0

        # --- Persist ---
        self.state["ltn_integrator"] = round(ltn_integrator, 4)
        self.state["motivational_weight"] = round(motivational_weight, 4)
        self.state["drive_coordination"] = round(drive_coordination, 4)
        self.state["ltn_threat_response"] = round(ltn_threat_response, 4)
        self.state["lateral_tuberal_composite"] = round(lateral_tuberal_composite, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ltn_integrator": round(ltn_integrator, 4),
            "motivational_weight": round(motivational_weight, 4),
            "drive_coordination": round(drive_coordination, 4),
            "ltn_threat_response": round(ltn_threat_response, 4),
            "lateral_tuberal_composite": round(lateral_tuberal_composite, 4),
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

