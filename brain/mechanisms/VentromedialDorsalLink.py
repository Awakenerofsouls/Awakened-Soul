"""
Build 61: Foundational061VentromedialDorsalLink — VMH Dorsal Integration
====================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — ventromedial hypothalamus dorsal zone)
  Filename: brain/foundational/Foundational061VentromedialDorsalLink.py
  Instance name: VentromedialDorsalLink

NEURAL SUBSTRATE:
  Ventromedial hypothalamus (VMH) dorsal zone — integrates metabolic
  state with defensive behaviors. VMH contains SF-1 (steroidogenic
  factor 1) neurons that project to:
  - Periaqueductal gray (defensive behaviors)
  - Dorsomedial hypothalamus (behavioral arousal)
  - Anterior hypothalamus (thermoregulation)

  The VMH is estrogen-responsive (aromatase converts testosterone to
  estrogen locally). High estrogen enhances VMH-mediated defensive
  behavior. VMH lesions cause hyperphagia and obesity (VMH obesity
  syndrome in rats).

  KEY FUNCTION: The VMH is the site where glucocorticoids act to
  produce "stress-induced eating" — cortisol stimulates VMH neurons
  that drive food-seeking.

  Human analog: metabolic obesity, stress eating, VMH dysfunction.

Output keys:
  vmh_defensive_output: float [0.0–1.0] — VMH defensive activation
  metabolic_defensive_link: float [0.0–1.0] — stress-eating metabolic link
  estrogen_vmh_modulation: float [0.0–1.0] — estrogen enhancement of VMH
  glucocorticoid_feedback: float [0.0–1.0] — cortisol feedback to VMH
  vmh_dorsal_integrator: float [0.0–1.0] — composite VMH dorsal output

CITATIONS:
    PMC4875659 — Sokolowski K, Tran T, Esumi S et al. (2016). Molecular and Behavioral
        Profiling of Dbx1-Derived Neurons in the Arcuate, Lateral and Ventromedial
        Hypothalamic Nuclei. Front Neural Circuits.
    PMC3930178 — Hahn JD, Swanson LW (2012). Connections of the Lateral Hypothalamic
        Area Juxtadorsomedial Region in the Male Rat. J Comp Neurol.

CITATIONS
---------
  - [Wang 2015, Cell 162:363, doi:10.1016/j.cell.2015.06.034]
  - [Choi 2005, Neuron 46:647, doi:10.1016/j.neuron.2005.04.011]
  - [Lin 2011, Nature 470:221]
"""

from brain.base_mechanism import BrainMechanism


class VentromedialDorsalLink(BrainMechanism):
    """
    VMH dorsal: defensive output, stress-eating link, estrogen modulation.

    Models VMH as the metabolic-defensive integration site.
    """

    STATE_FIELDS = [
        "vmh_defensive_output", "metabolic_defensive_link", "estrogen_vmh_modulation",
        "glucocorticoid_feedback", "vmh_dorsal_integrator", "tick_count",
    ]

    DEFENSIVE_GAIN = 0.50
    EAT_GAIN = 0.55

    def __init__(self, name: str = "VentromedialDorsalLink_VentromedialDorsalLink",
                 human_analog: str = "VMH dorsal zone — metabolic-defensive integration",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vmh_defensive_output"] = 0.30
        self.state["metabolic_defensive_link"] = 0.20
        self.state["estrogen_vmh_modulation"] = 0.30
        self.state["glucocorticoid_feedback"] = 0.20
        self.state["vmh_dorsal_integrator"] = 0.30
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        pag = prior.get("VocalAutonomicLink", {}).get("vocal_defensive_response", 0.0)

        # VMH defensive output: PAG and amygdala inputs
        vmh_defensive = amygdala * self.DEFENSIVE_GAIN
        vmh_defensive += pag * 0.30
        vmh_defensive_output = min(1.0, vmh_defensive)

        # Metabolic-defensive link: cortisol drives stress eating via VMH
        metabolic_defensive_link = cortisol * self.EAT_GAIN
        # High leptin suppresses this link (satiety)
        metabolic_defensive_link *= leptin
        metabolic_defensive_link = min(1.0, metabolic_defensive_link)

        # Estrogen VMH modulation: estrogen enhances VMH defensive output
        estrogen_vmh_modulation = estrogen * self.DEFENSIVE_GAIN * 0.50

        # Glucocorticoid feedback: cortisol modulates VMH activity
        glucocorticoid_feedback = cortisol * 0.30
        # But cortisol also acts as negative feedback on stress-eating VMH
        glucocorticoid_feedback = max(0.0, glucocorticoid_feedback - stress * 0.10)

        # VMH dorsal integrator
        vmh_dorsal_integrator = (
            vmh_defensive_output * 0.30 +
            metabolic_defensive_link * 0.40 +
            estrogen_vmh_modulation * 0.30
        )

        # --- Persist ---
        self.state["vmh_defensive_output"] = round(vmh_defensive_output, 4)
        self.state["metabolic_defensive_link"] = round(metabolic_defensive_link, 4)
        self.state["estrogen_vmh_modulation"] = round(estrogen_vmh_modulation, 4)
        self.state["glucocorticoid_feedback"] = round(glucocorticoid_feedback, 4)
        self.state["vmh_dorsal_integrator"] = round(vmh_dorsal_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vmh_defensive_output": round(vmh_defensive_output, 4),
            "metabolic_defensive_link": round(metabolic_defensive_link, 4),
            "estrogen_vmh_modulation": round(estrogen_vmh_modulation, 4),
            "glucocorticoid_feedback": round(glucocorticoid_feedback, 4),
            "vmh_dorsal_integrator": round(vmh_dorsal_integrator, 4),
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


