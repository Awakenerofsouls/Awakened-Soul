"""
Build 21: Foundational021DefensiveThermoLink — Anterior Hypothalamic Cooling Detector
===================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — anterior preoptic area)
  Filename: brain/foundational/Foundational021DefensiveThermoLink.py
  Instance name: DefensiveThermoLink

NEURAL SUBSTRATE:
  Anterior hypothalamic preoptic area (POA) — the primary thermosensory
  integration site. POA neurons are temperature-sensitive: warm-sensitive
  neurons fire faster when local temperature rises (e.g., during fever,
  environmental warmth); cold-sensitive neurons respond to cooling.
  POA receives input from skin thermoreceptors via the spinal cord and
  brainstem, and projects to the dorsomedial hypothalamus (DMH) and
  rostral raphe pallidus (rRPa) to drive autonomic thermoregulatory
  responses (vasodilation, panting, sweating vs. vasoconstriction, shivering).

  KEY POINT: POA cooling signals sleep onset. Experimental cooling of the
  POA in cats and rodents produces NREM sleep within minutes — this is
  the thermoregulatory sleep gate. Fever (POA heating) disrupts sleep.
  This mechanism models the "defensive" cooling link: when POA temperature
  is elevated, defensive thermoregulatory responses are engaged.

  Human analog: fever, sweating, behavioral thermoregulation.

Refs:
  - McEwen 2001 (PMC4471069) — stress-body temperature relationship
  - Szymusiak 1995 (PMID 7623110) — sleep-active neurons in preoptic area
  - Kumar 2017 (PMC5389146) — anterior hypothalamic warming → sleep
  - Boulant 2000 (PMC4471069) — hypothalamic thermosensitive neurons

Output keys:
  defensive_cooling_signal: float [0.0–1.0] — POA temperature elevation drive
  thermal_pain_suppression: float [0.0–1.0] — reduced pain during fever
  autonomic_cooling_effort: float [0.0–1.0] — vasodilation/sweating drive
  fever_threshold_proximity: float [0.0–1.0] — proximity to fever threshold
  sleep_permissiveness: float [0.0–1.0] — sleep likelihood from thermal state


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class DefensiveThermoLink(BrainMechanism):
    """
    Anterior hypothalamic POA cooling/thermal defense mechanism.

    Integrates core temperature and skin temperature signals to determine
    whether the organism is in a thermally stressful state that requires
    defensive responses. Cooling of POA signals sleep permissiveness;
    heating signals fever/defensive thermoregulation.
    """

    # Internal state fields
    STATE_FIELDS = [
        "defensive_cooling_signal",     # POA temperature elevation level
        "thermal_pain_suppression",      # endogenous antipyretic effect
        "autonomic_cooling_effort",     # vasodilation/sweating drive
        "fever_threshold_proximity",     # proximity to fever threshold
        "sleep_permissiveness",           # sleep gate thermal signal
        "tick_count",
    ]

    # Parameters
    FEVER_THRESHOLD = 0.78           # normalized core temp where fever begins
    FEVER_MAX = 0.95                # normalized core temp for severe fever
    ACCUMULATION_RATE = 0.20        # rate of temperature rise during stress
    DECAY_RATE = 0.10               # rate of temperature normalization
    PAIN_SUPPRESSION_GAIN = 0.35   # fever suppresses pain
    AUTONOMIC_COST_GAIN = 0.40     # thermoregulatory effort metabolic cost

    def __init__(self, name: str = "DefensiveThermoLink",
                 human_analog: str = "POA — anterior hypothalamic thermal integration",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        # Initial state: normal core temperature
        self.state["defensive_cooling_signal"] = 0.35
        self.state["thermal_pain_suppression"] = 0.05
        self.state["autonomic_cooling_effort"] = 0.0
        self.state["fever_threshold_proximity"] = 0.0
        self.state["sleep_permissiveness"] = 0.35
        self.state["tick_count"] = 0

    # ── tick ─────────────────────────────────────────────────────────────────
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Temperature inputs ---
        core_temp_signal = prior.get("CoreTemperatureMonitor", {}).get(
            "core_temperature", 0.50
        )
        skin_temp_signal = prior.get("PeripheralTemperature", {}).get(
            "skin_temperature", 0.50
        )
        # CRH/stress elevates core temperature (psychogenic fever)
        stress_fever = prior.get("CRHStressDispatcher", {}).get(
            "crh_level", 0.0
        )
        # Ambient warmth (skin cooling drives POA cooling → sleep signal)
        ambient_warmth = prior.get("AmbientTemperatureRelay", {}).get(
            "ambient_temperature", 0.50
        )

        # --- Current state ---
        current_signal = self.state["defensive_cooling_signal"]

        # --- Compute effective temperature signal ---
        # Core temp is primary; skin temp is secondary
        # Stress fever adds to core temperature
        effective_temp = core_temp_signal + (stress_fever * 0.15)
        # Skin cooling (ambient_warmth low) → POA signals cooling → sleep permissiveness
        thermal_input = (effective_temp * 0.70) + (skin_temp_signal * 0.30)

        # --- Defensive cooling signal (POA temperature elevation) ---
        # Rises when core temperature exceeds normal range
        # Falls when skin is cool (ambient cooling → POA cooling → sleep)
        if thermal_input > current_signal:
            delta = (thermal_input - current_signal) * self.ACCUMULATION_RATE
            new_signal = current_signal + delta
        else:
            delta = (current_signal - thermal_input) * self.DECAY_RATE
            new_signal = current_signal - delta
        new_signal = max(0.0, min(1.0, new_signal))

        # --- Fever threshold proximity ---
        fever_proximity = (new_signal - (self.FEVER_THRESHOLD - 0.15)) / 0.15
        fever_proximity = max(0.0, min(1.0, fever_proximity))

        # --- Thermal pain suppression (fever suppresses pain) ---
        # Endogenous antipyretics reduce pain during fever
        pain_suppression = fever_proximity * self.PAIN_SUPPRESSION_GAIN
        pain_suppression = min(1.0, pain_suppression)

        # --- Autonomic cooling effort ---
        # When fever is approaching, autonomic cooling mechanisms (vasodilation, sweating)
        # are engaged. The "cost" is proportional to fever proximity.
        if fever_proximity > 0.3:
            cooling_effort = (fever_proximity - 0.3) * self.AUTONOMIC_COST_GAIN
        else:
            cooling_effort = 0.0
        cooling_effort = min(1.0, cooling_effort)

        # --- Sleep permissiveness ---
        # POA cooling (low signal) → sleep permissive. High fever → sleep disrupted.
        # Ambient cooling (low ambient_warmth) directly raises permissiveness
        ambient_sleep_effect = (1.0 - ambient_warmth) * 0.40
        if new_signal < 0.50:
            # Normal or cool: thermal state is sleep-permissive
            thermal_sleep = 0.50 - new_signal
        else:
            # Elevated core temp: sleep suppressed
            thermal_sleep = max(0.0, 0.30 - fever_proximity * 0.50)
        sleep_permissiveness = thermal_sleep + ambient_sleep_effect
        sleep_permissiveness = max(0.0, min(1.0, sleep_permissiveness))

        # --- Round ---
        new_signal = round(new_signal, 4)
        fever_proximity = round(fever_proximity, 4)
        pain_suppression = round(pain_suppression, 4)
        cooling_effort = round(cooling_effort, 4)
        sleep_permissiveness = round(sleep_permissiveness, 4)

        # --- Persist ---
        self.state["defensive_cooling_signal"] = new_signal
        self.state["thermal_pain_suppression"] = pain_suppression
        self.state["autonomic_cooling_effort"] = cooling_effort
        self.state["fever_threshold_proximity"] = fever_proximity
        self.state["sleep_permissiveness"] = sleep_permissiveness
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "defensive_cooling_signal": new_signal,
            "thermal_pain_suppression": pain_suppression,
            "autonomic_cooling_effort": cooling_effort,
            "fever_threshold_proximity": fever_proximity,
            "sleep_permissiveness": sleep_permissiveness,
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

