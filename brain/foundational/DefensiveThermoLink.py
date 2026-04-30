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
  - [DiMicco 2002, Pharmacol Biochem Behav 71:469]
  - [Nakamura 2011, J Neurosci 31:11954, doi:10.1523/JNEUROSCI.2370-11.2011]
  - [Morrison 2014, Compr Physiol 4:1677]
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

    def __init__(self, name: str = "DefensiveThermoLink_DefensiveThermoLink",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


