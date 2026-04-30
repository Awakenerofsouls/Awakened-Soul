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
  - [Saper 2002, Nature 418:935, doi:10.1038/nature00965]
  - [Loewy 1990, Annu Rev Physiol 52:691]
  - [Sterling 2012, Physiol Behav 106:5, doi:10.1016/j.physbeh.2011.06.004]
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

    def __init__(self, name: str = "PosteriorHomeostaticOutput_PosteriorHomeostaticOutput",
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


