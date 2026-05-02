"""
Build 23: Foundational023FacialGradientSensor — Circumventricular Organs / SFO & OVLT
==================================================================================

PLACEMENT:
  Layer:    foundational (forebrain — subfornical organ + organum vasculosum)
  Filename: brain/foundational/Foundational023FacialGradientSensor.py
  Instance name: FacialGradientSensor

NEURAL SUBSTRATE:
  Subfornical organ (SFO) and organum vasculosum of the lamina terminalis (OVLT)
  — the two primary circumventricular organs (CVOs) lacking a blood-brain barrier.
  These structures detect circulating hormones and solutes directly:

  SFO:
    - Osmoreceptors: detect plasma osmolality (Na+, mannitol-induced)
    - Angiotensin II (AT1 receptors): thirst and sodium appetite drive
    - Leptin receptors: communicate adipocyte energy stores
    - Natriuretic peptide receptors: oppose ATII thirst

  OVLT:
    - Osmoreceptors: detect plasma osmolality → ADH release from PVN/SON
    - Na+ sensing: central osmoreceptor for sodium appetite
    - Cytokine receptors: IL-1, IL-6 → fever and sickness behavior

  Human analog: thirst drive, sodium appetite, plasma osmolality monitoring.

Refs:
  - McKinley 2003 (PMC4471069) — SFO, OVLT osmoreceptors
  - Johnson 2001 (PMC4471069) — SFO angiotensin and thirst
  - Bourque 2008 (PMC1914446) — central osmoreceptor-Na+ sensing

Output keys:
  osmolality_signal: float [0.0–1.0] — plasma osmolality deviation
  thirst_drive: float [0.0–1.0] — thirst motivation intensity
  sodium_appetite: float [0.0–1.0] — desire for sodium intake
  natriuretic_inhibition: float [0.0–1.0] — opposing signal from ANP/BNP
  circumventricular_alert: float [0.0–1.0] — CVO threat detection


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class FacialGradientSensor(BrainMechanism):
    """
    Subfornical organ + OVLT osmoreceptor and hormone detection.

    Integrates blood-borne signals (osmolality, angiotensin II, sodium,
    natriuretic peptides) to generate thirst, sodium appetite, and
    circumventricular threat signals.
    """

    STATE_FIELDS = [
        "osmolality_signal", "thirst_drive", "sodium_appetite",
        "natriuretic_inhibition", "circumventricular_alert", "tick_count",
    ]

    OSMOLARITY_GAIN = 0.60
    THIRST_GAIN = 0.70
    SODIUM_GAIN = 0.45
    NATRIURETIC_INHIBITION_GAIN = 0.30
    ALERT_GAIN = 0.35

    def __init__(self, name: str = "FacialGradientSensor",
                 human_analog: str = "SFO + OVLT — circumventricular osmoreceptors",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["osmolality_signal"] = 0.40
        self.state["thirst_drive"] = 0.20
        self.state["sodium_appetite"] = 0.10
        self.state["natriuretic_inhibition"] = 0.25
        self.state["circumventricular_alert"] = 0.05
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        ang_ii = prior.get("AngiotensinSignal", {}).get("at_ii_level", 0.0)
        natriuretic = prior.get("NatriureticPeptide", {}).get("anp_level", 0.0)
        osmolality = prior.get("OsmoreceptorSignal", {}).get("plasma_osmolality", 0.50)
        cytokines = prior.get("ImmuneSignalRelay", {}).get("immune_activation", 0.0)

        current_signal = self.state["osmolality_signal"]
        # Leaky integrator: approaches osmolality signal
        new_signal = current_signal + (osmolality - current_signal) * self.OSMOLARITY_GAIN
        new_signal = max(0.0, min(1.0, new_signal))

        # Thirst: driven by osmolality and angiotensin II; opposed by ANP
        thirst = (new_signal * 0.40) + (ang_ii * 0.40) - (natriuretic * 0.20)
        thirst = max(0.0, min(1.0, thirst * self.THIRST_GAIN))

        # Sodium appetite: ATII and high osmolality drive it
        sodium_app = (ang_ii * 0.50) + (new_signal * 0.30) - (natriuretic * 0.25)
        sodium_app = max(0.0, min(1.0, sodium_app * self.SODIUM_GAIN))

        # Natriuretic inhibition (ANP/BNP oppose ATII)
        natriuretic_inhibition = natriuretic * self.NATRIURETIC_INHIBITION_GAIN

        # CVO alert: cytokine activation triggers sickness behavior via OVLT
        cvo_alert = (new_signal * 0.20) + (ang_ii * 0.30) + (cytokines * 0.50)
        cvo_alert = max(0.0, min(1.0, cvo_alert * self.ALERT_GAIN))

        # --- Persist ---
        self.state["osmolality_signal"] = round(new_signal, 4)
        self.state["thirst_drive"] = round(thirst, 4)
        self.state["sodium_appetite"] = round(sodium_app, 4)
        self.state["natriuretic_inhibition"] = round(natriuretic_inhibition, 4)
        self.state["circumventricular_alert"] = round(cvo_alert, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "osmolality_signal": round(new_signal, 4),
            "thirst_drive": round(thirst, 4),
            "sodium_appetite": round(sodium_app, 4),
            "natriuretic_inhibition": round(natriuretic_inhibition, 4),
            "circumventricular_alert": round(cvo_alert, 4),
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

