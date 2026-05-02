"""
Build 44: Foundational044SatietyMetabolicSeparator — Ventromedial Hypothalamus (VMH)
===============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — ventromedial hypothalamus, VMH)
  Filename: brain/foundational/Foundational044SatietyMetabolicSeparator.py
  Instance name: SatietyMetabolicSeparator

NEURAL SUBSTRATE:
  Ventromedial hypothalamus (VMH) — the "satiety center." Lesions of VMH
  produce hyperphagia and obesity (VMH obesity syndrome). Contains:
  - Steroidogenic neurons (responsive to estrogen, leptin)
  - SF-1 (steroidogenic factor 1) neurons: drive defensive/defensive behaviors
  - Glucocorticoid receptors: respond to cortisol feedback

  VMH OUTPUT:
  - To PVN: integrates stress and metabolic state
  - To arcuate: reciprocally connects with NPY/AgRP and POMC neurons
  - To lateral hypothalamus: VMH抑制LHA → reduces feeding

  KEY: VMH is the site where estrogens act to produce female-typical
  eating patterns (lower food intake during estrus). Aromatase in VMH
  converts testosterone to estrogen locally.

  Human analog: satiety, metabolic set point, ventromedial obesity.

Output keys:
  vmh_satiety_output: float [0.0–1.0] — satiety signal from VMH
  metabolic_setpoint: float [0.0–1.0] — VMH-set body weight target
  estrogen_satiety_modulation: float [0.0–1.0] — estrogen-enhanced satiety
  defensive_metabolic_flag: float [0.0–1.0] — VMH threat response
  energy_storage_index: float [0.0–1.0] — integrated energy storage signal

CITATIONS:
    PMC10216274 — Chu P, Guo W, You H et al. (2023). Regulation of Satiety by
        Bdnf-e2-Expressing Neurons Through TrkB Activation in Ventromedial
        Hypothalamus. J Neurosci.
    PMC9448279 — Ahn W, Latremouille J, Harris RBS (2022). Leptin Receptor-Expressing
        Cells in the Ventromedial Nucleus of the Hypothalamus Contribute to Enhanced
        CCK-Induced Satiety. Am J Physiol Regul Integr Comp Physiol.

CITATIONS
---------
  - [Schwartz 2000, Nature 404:661, doi:10.1038/35007534]
  - [Cone 2005, Nat Neurosci 8:571, doi:10.1038/nn1455]
  - [Williams 2001, Neuroscience 105:495]
"""

from brain.base_mechanism import BrainMechanism


class SatietyMetabolicSeparator(BrainMechanism):
    """
    VMH: satiety signal, metabolic set point, estrogen modulation.

    Models the VMH as the metabolic set-point regulator.
    """

    STATE_FIELDS = [
        "vmh_satiety_output", "metabolic_setpoint", "estrogen_satiety_modulation",
        "defensive_metabolic_flag", "energy_storage_index", "tick_count",
    ]

    SATIETY_GAIN = 0.55
    SETPOINT_GAIN = 0.40
    DEFENSIVE_GAIN = 0.45

    def __init__(self, name: str = "SatietyMetabolicSeparator_SatietyMetabolicSeparator",
                 human_analog: str = "VMH — ventromedial hypothalamic satiety center",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vmh_satiety_output"] = 0.50
        self.state["metabolic_setpoint"] = 0.50
        self.state["estrogen_satiety_modulation"] = 0.40
        self.state["defensive_metabolic_flag"] = 0.0
        self.state["energy_storage_index"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        pomc = prior.get("ArcuatePOMCOutput", {}).get("pOMC_activity", 0.30)

        # Estrogen satiety modulation: estrogen enhances VMH satiety
        estrogen_satiety = estrogen * self.SATIETY_GAIN * 0.50

        # VMH satiety output: leptin + POMC + glucose - NPY/stress
        satiety_raw = (leptin * 0.35) + (pomc * 0.30) + (glucose * 0.20) + estrogen_satiety
        vmh_satiety = min(1.0, max(0.0, satiety_raw))

        # Metabolic setpoint: where VMH thinks body weight should be
        # High leptin → elevated setpoint (adipostat)
        metabolic_setpoint = 0.50 + (leptin - 0.50) * self.SETPOINT_GAIN
        metabolic_setpoint = min(1.0, max(0.0, metabolic_setpoint))

        # Defensive metabolic flag: VMH activates during threat
        cortisol_threat = cortisol * self.DEFENSIVE_GAIN
        stress_threat = stress * self.DEFENSIVE_GAIN * 0.50
        defensive_metabolic = max(cortisol_threat, stress_threat)
        defensive_metabolic = min(1.0, max(0.0, defensive_metabolic))

        # Energy storage index
        energy_storage = (leptin * 0.40) + (glucose * 0.30) + (1.0 - stress) * 0.30

        # --- Persist ---
        self.state["vmh_satiety_output"] = round(vmh_satiety, 4)
        self.state["metabolic_setpoint"] = round(metabolic_setpoint, 4)
        self.state["estrogen_satiety_modulation"] = round(estrogen_satiety, 4)
        self.state["defensive_metabolic_flag"] = round(defensive_metabolic, 4)
        self.state["energy_storage_index"] = round(energy_storage, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vmh_satiety_output": round(vmh_satiety, 4),
            "metabolic_setpoint": round(metabolic_setpoint, 4),
            "estrogen_satiety_modulation": round(estrogen_satiety, 4),
            "defensive_metabolic_flag": round(defensive_metabolic, 4),
            "energy_storage_index": round(energy_storage, 4),
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


