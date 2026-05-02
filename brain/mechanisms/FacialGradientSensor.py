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
  - [Bushdid 2014, Science 343:1370]
  - [Yarbus 1967, Eye Movements and Vision]
  - [Eckstein 2017, Trends Cogn Sci 21:601]
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

    def __init__(self, name: str = "FacialGradientSensor_FacialGradientSensor",
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


