"""
Build 51: Foundational051AnteriorHypothalamicCooling — Preoptic Area Cooling Signal
=================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — anterior preoptic area)
  Filename: brain/foundational/Foundational051AnteriorHypothalamicCooling.py
  Instance name: AnteriorHypothalamicCooling

NEURAL SUBSTRATE:
  Anterior hypothalamic preoptic area (POA) — the primary thermosensory
  integration site for behavioral thermoregulation. Contains temperature-
  sensitive neurons:
  - Warm-sensitive neurons: fire faster when local temperature rises
    (POA = "defensive against overheating")
  - Cold-sensitive neurons: fire when POA cools (trigger heat production)

  COOLING SIGNAL: Experimental cooling of the POA in vivo produces
  NREM sleep within minutes. This is the "sleep gate" signal — POA cooling
  disinhibits VLPO → sleep onset. Fever (POA heating) disrupts sleep.

  Projections: POA → DMH → rRPa (autonomic thermoregulation) and
  POA → VLPO (sleep switch modulation).

  Human analog: feeling of drowsiness in cool environments, sleep onset.

Output keys:
  cooling_signal: float [0.0–1.0] — POA cooling level (sleep-permissive)
  warm_exposure_flag: float [0.0–1.0] — POA warming (sleep-suppressive)
  behavioral_thermoregulation: float [0.0–1.0] — behavioral temperature seeking
  preoptic_sleep_gate: float [0.0–1.0] — VLPO permissiveness for sleep
  poa_temperature_index: float [0.0–1.0] — POA thermal state

CITATIONS:
    PMC2278963 — Griffin JD, Saper CB, Boulant JA (2001). Synaptic and Morphological
        Characteristics of Temperature-Sensitive and -Insensitive Rat Hypothalamic
        Neurones. J Physiol.
    PMC1180151 — Curras MC, Kelso SR, Boulant JA (1991). Intracellular Analysis of
        Inherent and Synaptic Activity in Hypothalamic Thermosensitive Neurones in
        the Rat. J Physiol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorHypothalamicCooling(BrainMechanism):
    """
    Anterior POA: cooling signal, sleep gate, behavioral thermoregulation.

    Models the preoptic area as the sleep-permissive thermal detector.
    """

    STATE_FIELDS = [
        "cooling_signal", "warm_exposure_flag", "behavioral_thermoregulation",
        "preoptic_sleep_gate", "poa_temperature_index", "tick_count",
    ]

    COOLING_GAIN = 0.50
    WARMING_GAIN = 0.45
    SLEEP_GATE_GAIN = 0.55

    def __init__(self, name: str = "AnteriorHypothalamicCooling",
                 human_analog: str = "POA — anterior hypothalamic cooling signal",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["cooling_signal"] = 0.30
        self.state["warm_exposure_flag"] = 0.20
        self.state["behavioral_thermoregulation"] = 0.20
        self.state["preoptic_sleep_gate"] = 0.35
        self.state["poa_temperature_index"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        core_temp = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)
        ambient = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        skin_temp = prior.get("PeripheralTemperature", {}).get("skin_temperature", 0.50)
        sleep_pressure = prior.get("PassiveQuiescenceMode", {}).get("sleep_pressure", 0.0)

        # POA temperature: weighted average of core and skin
        poa_temperature = (core_temp * 0.60) + (skin_temp * 0.40)
        poa_temperature_index = poa_temperature

        # Cooling signal: low POA temperature = sleep-permissive
        # As POA temperature drops below threshold, cooling signal rises
        if poa_temperature < 0.55:
            cooling_signal = (0.55 - poa_temperature) * self.COOLING_GAIN
        else:
            cooling_signal = 0.0

        # Warming flag: elevated POA temperature suppresses sleep
        if poa_temperature > 0.60:
            warm_exposure_flag = (poa_temperature - 0.60) * self.WARMING_GAIN
        else:
            warm_exposure_flag = 0.0

        # Preoptic sleep gate: VLPO permissiveness
        # Cooling signal raises the gate; warm exposure closes it
        base_gate = 0.50
        sleep_gate = base_gate + (cooling_signal * self.SLEEP_GATE_GAIN) - (warm_exposure_flag * 0.30)
        preoptic_sleep_gate = min(1.0, max(0.0, sleep_gate))

        # Behavioral thermoregulation: seek warmth when cold, cool when hot
        if poa_temperature < 0.50:
            behavioral_thermoreg = (0.50 - poa_temperature) * 0.50  # seek warmth
        else:
            behavioral_thermoreg = (poa_temperature - 0.50) * 0.30  # seek cool
        behavioral_thermoregulation = min(1.0, max(0.0, behavioral_thermoreg))

        # --- Persist ---
        self.state["cooling_signal"] = round(cooling_signal, 4)
        self.state["warm_exposure_flag"] = round(warm_exposure_flag, 4)
        self.state["behavioral_thermoregulation"] = round(behavioral_thermoregulation, 4)
        self.state["preoptic_sleep_gate"] = round(preoptic_sleep_gate, 4)
        self.state["poa_temperature_index"] = round(poa_temperature_index, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cooling_signal": round(cooling_signal, 4),
            "warm_exposure_flag": round(warm_exposure_flag, 4),
            "behavioral_thermoregulation": round(behavioral_thermoregulation, 4),
            "preoptic_sleep_gate": round(preoptic_sleep_gate, 4),
            "poa_temperature_index": round(poa_temperature_index, 4),
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

