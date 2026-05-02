"""
Build 62: Foundational062PosteriorHypothalamicOutput — Posterior Hypothalamic Integration
===================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — posterior hypothalamus)
  Filename: brain/foundational/Foundational062PosteriorHypothalamicOutput.py
  Instance name: PosteriorHypothalamicOutput

NEURAL SUBSTRATE:
  Posterior hypothalamus (PH) — the "heat defense" center, complementing
  the anterior hypothalamus ("cold defense"). PH is the site of:
  - Orexin neurons (partially): wake-promoting, energy expenditure
  - Histaminergic TMN neurons: wake-promoting histamine
  - Descending projections to raphe pallidus (rRPa) → sympathetic output
  - Integration with circadian (SCN) and metabolic signals

  KEY FUNCTION: PH drives:
  1. Thermogenesis: PH → rRPa → intermediolateral cell column → sympathetic → BAT
  2. Vasoconstriction: sympathetic vasoconstrictor tone
  3. Arousal: PH wake-promoting output

  PH LESION: causes poikilothermia — inability to defend body temperature.
  PH ACTIVATION: hyperthermia, increased metabolic rate.

  Human analog: posterior hypothalamic integration, thermoregulation, arousal.

Output keys:
  posterior_hyp_output: float [0.0–1.0] — composite PH output
  thermogenic_sympathetic: float [0.0–1.0] — brown adipose tissue thermogenesis
  posterior_arousal: float [0.0–1.0] — PH wake-promoting drive
  poikilothermia_risk: float [0.0–1.0] — vulnerability to temperature loss
  posterior_integrator: float [0.0–1.0] — total PH state

CITATIONS:
    PMC8227286 — Mota-Rojas D, Titto CG, Orihuela A et al. (2021). Physiological
        and Behavioral Mechanisms of Thermoregulation in Mammals. Animals.
    PMC3253759 — Carvalho-Netto EF, Litvin Y, Nunes-de-Souza RL et al. (2007).
        Effects of Intra-PAG Infusion of Ovine CRF on Defensive Behaviors in
        Swiss-Webster Mice. Horm Behav.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorHypothalamicOutput(BrainMechanism):
    """
    Posterior hypothalamus: heat defense, thermogenesis, posterior arousal.

    Models PH as the posterior hypothalamic heat-defense and arousal integrator.
    """

    STATE_FIELDS = [
        "posterior_hyp_output", "thermogenic_sympathetic",
        "posterior_arousal", "poikilothermia_risk", "posterior_integrator", "tick_count",
    ]

    THERMOGENIC_GAIN = 0.55
    AROUSAL_GAIN = 0.50

    def __init__(self, name: str = "PosteriorHypothalamicOutput",
                 human_analog: str = "Posterior hypothalamus — heat defense",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["posterior_hyp_output"] = 0.40
        self.state["thermogenic_sympathetic"] = 0.30
        self.state["posterior_arousal"] = 0.40
        self.state["poikilothermia_risk"] = 0.0
        self.state["posterior_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        histamine = prior.get("TuberomammillaryOutput", {}).get("histamine_output", 0.30)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        cold_exposure = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        sympathetic_tone = prior.get("SympatheticVasomotorController", {}).get("sympathetic_tone", 0.40)
        sleep = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Posterior arousal: orexin + histamine + circadian
        posterior_arousal = (orexin * 0.35) + (histamine * 0.30) + (circadian * 0.35)

        # Thermogenic sympathetic: cold → PH → rRPa → sympathetic → BAT
        cold_stimulus = (1.0 - cold_exposure) * self.THERMOGENIC_GAIN
        thermogenic_sympathetic = cold_stimulus + (sympathetic_tone * 0.30)
        # Sleep suppresses thermogenesis
        thermogenic_sympathetic -= sleep * 0.30
        thermogenic_sympathetic = max(0.0, min(1.0, thermogenic_sympathetic))

        # Posterior hypothalamic output
        posterior_hyp_output = (posterior_arousal * 0.50) + (thermogenic_sympathetic * 0.50)
        posterior_hyp_output = min(1.0, posterior_hyp_output)

        # Poikilothermia risk: low PH output = vulnerability to temperature loss
        if posterior_hyp_output < 0.30:
            poikilothermia_risk = (0.30 - posterior_hyp_output) / 0.30
        else:
            poikilothermia_risk = 0.0

        # Posterior integrator
        posterior_integrator = (posterior_hyp_output + posterior_arousal + thermogenic_sympathetic) / 3.0

        # --- Persist ---
        self.state["posterior_hyp_output"] = round(posterior_hyp_output, 4)
        self.state["thermogenic_sympathetic"] = round(thermogenic_sympathetic, 4)
        self.state["posterior_arousal"] = round(posterior_arousal, 4)
        self.state["poikilothermia_risk"] = round(poikilothermia_risk, 4)
        self.state["posterior_integrator"] = round(posterior_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_hyp_output": round(posterior_hyp_output, 4),
            "thermogenic_sympathetic": round(thermogenic_sympathetic, 4),
            "posterior_arousal": round(posterior_arousal, 4),
            "poikilothermia_risk": round(poikilothermia_risk, 4),
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

