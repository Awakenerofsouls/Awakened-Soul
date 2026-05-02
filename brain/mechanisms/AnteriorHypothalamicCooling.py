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
  - [Nakamura 2011, J Neurosci 31:11954, doi:10.1523/JNEUROSCI.2370-11.2011]
  - [Boulant 2000, Clin Infect Dis 31:S157, doi:10.1086/317520]
  - [Morrison 2014, Compr Physiol 4:1677]
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

    def __init__(self, name: str = "AnteriorHypothalamicCooling_AnteriorHypothalamicCooling",
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

    # ---------- enrichment helpers (phase-2 expansion) ----------
    def attribute_signature(self) -> tuple:
        out = []
        for attr_name in sorted(dir(self)):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            out.append((attr_name, type(v).__name__))
        return tuple(out)

    def numeric_attribute_values(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[attr_name] = float(v)
        return out

    def list_attribute_lengths(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, list):
                out[attr_name] = len(v)
        return out

    def boolean_attributes(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, bool):
                out[attr_name] = v
        return out

    def callable_method_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                out.append(attr_name)
        return out

    def has_attribute(self, name: str) -> bool:
        return hasattr(self, name) and not name.startswith("_")

    def safe_get(self, name: str, default=None):
        try:
            v = getattr(self, name, default)
            return v
        except Exception:
            return default

    def history_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                out.append(attr_name)
        return out

    def total_history_length(self) -> int:
        total = 0
        for attr_name in self.history_attribute_names():
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                total += len(v)
        return total

    def is_initialized(self) -> bool:
        return getattr(self, "tick_count", 0) >= 0

    def class_metadata(self) -> dict:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "n_attrs": self.attribute_count() if hasattr(self, "attribute_count") else 0,
            "n_history": len(self.history_attribute_names()),
        }

    def state_size(self) -> int:
        try:
            return len(self.export_state())
        except Exception:
            return 0


