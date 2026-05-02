"""
Build 33: Foundational033PosteriorHomeostaticOutput — Posterior Hypothalamic Output
================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — posterior hypothalamus)
  Filename: brain/foundational/Foundational033PosteriorHomeostaticOutput.py
  Instance name: PosteriorHomeostaticOutput

NEURAL SUBSTRATE:
  Posterior hypothalamus (PH) — the "heat defense" center, complementing
  the anterior hypothalamus (POA/MPOA = "cold defense"). PH neurons
  include:
  - Histaminergic tuberomammillary neurons (TMN): wake-promoting histamine
  - Orexin/hypocretin neurons: some extend into posterior hypothalamus
  - Descending projections to raphe pallidus (rRPa) → sympathetic output

  KEY FUNCTION: PH activation → hyperthermia, vasoconstriction, arousal.
  Lesion of PH → poikilothermia (loss of thermoregulation). PH integrates
  somatic (behavioral) and autonomic thermoregulatory responses.

  Human analog: heat defense, hyperthermia response, posterior hypothalamic
  integration of homeostatic state.

Output keys:
  heat_defense_signal: float [0.0–1.0] — posterior hypothalamic heat drive
  sympathetic_heat_output: float [0.0–1.0] — sympathetic vasoconstriction/heat
  arousal_from_homeostasis: float [0.0–1.0] — wake-promoting signal from PH
  body_temperature_drive: float [0.0–1.0] — net temperature regulation output
  posterior_integrator: float [0.0–1.0] — composite PH output

CITATIONS:
    PMC1331604 — Myers RD, Yaksh TL (1971). Thermoregulation Around a New Set-Point
        Established in the Monkey by Altering the Ratio of Sodium to Calcium Ions.
        J Physiol.
    PMC10854546 — Mota-Rojas D, Ghezzi MD, Hernández-Ávalos I et al. (2024).
        Hypothalamic Neuromodulation of Hypothermia in Domestic Animals. Animals.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorHomeostaticOutput(BrainMechanism):
    """
    Posterior hypothalamus: heat defense, sympathetic thermoregulation.

    The posterior hypothalamus drives heat-production and arousal when
    core temperature drops or sympathetic tone is high.
    """

    STATE_FIELDS = [
        "heat_defense_signal", "sympathetic_heat_output",
        "arousal_from_homeostasis", "body_temperature_drive",
        "posterior_integrator", "tick_count",
    ]

    HEAT_DEFENSE_GAIN = 0.50
    SYMPATHETIC_HEAT_GAIN = 0.45
    AROUSAL_GAIN = 0.40

    def __init__(self, name: str = "PosteriorHomeostaticOutput",
                 human_analog: str = "Posterior hypothalamus — heat defense and arousal",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["heat_defense_signal"] = 0.30
        self.state["sympathetic_heat_output"] = 0.20
        self.state["arousal_from_homeostasis"] = 0.40
        self.state["body_temperature_drive"] = 0.50
        self.state["posterior_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        core_temp = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)
        ambient = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        histaminergic = prior.get("HistamineArousalBooster", {}).get("histamine_level", 0.30)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        anterior_signal = prior.get("AnteriorHypothalamicCooling", {}).get("cooling_signal", 0.0)

        # Heat defense: PH fires when core temp is low or ambient is cold
        cold_stimulus = (1.0 - core_temp) * 0.40
        ambient_cold = (1.0 - ambient) * 0.30
        heat_defense = max(0.0, min(1.0, cold_stimulus + ambient_cold))

        # Sympathetic heat output: vasoconstriction, brown fat thermogenesis
        sympathetic_heat = heat_defense * self.SYMPATHETIC_HEAT_GAIN
        # Anterior POA inhibits posterior (flip-flop): anterior cooling suppresses PH
        anterior_inhibition = anterior_signal * 0.30
        sympathetic_heat = max(0.0, sympathetic_heat - anterior_inhibition)

        # Arousal from PH: histaminergic + orexin drive waking
        arousal_from_homeostasis = (histaminergic * 0.40) + (orexin * 0.40) + 0.20
        arousal_from_homeostasis = min(1.0, arousal_from_homeostasis)

        # Body temperature drive: balance of anterior (cooling) vs posterior (heating)
        body_temperature_drive = (heat_defense * 0.50) - (anterior_signal * 0.30)
        body_temperature_drive = max(0.0, min(1.0, 0.50 + body_temperature_drive))

        # Composite posterior integrator
        posterior_integrator = (sympathetic_heat + arousal_from_homeostasis +
                                body_temperature_drive) / 3.0

        # --- Persist ---
        self.state["heat_defense_signal"] = round(heat_defense, 4)
        self.state["sympathetic_heat_output"] = round(sympathetic_heat, 4)
        self.state["arousal_from_homeostasis"] = round(arousal_from_homeostasis, 4)
        self.state["body_temperature_drive"] = round(body_temperature_drive, 4)
        self.state["posterior_integrator"] = round(posterior_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "heat_defense_signal": round(heat_defense, 4),
            "sympathetic_heat_output": round(sympathetic_heat, 4),
            "arousal_from_homeostasis": round(arousal_from_homeostasis, 4),
            "body_temperature_drive": round(body_temperature_drive, 4),
            "posterior_integrator": round(posterior_integrator, 4),
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

