"""
Build 58: Foundational058ArcuatePOMCOutput — Arcuate POMC/CART Satiety System
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — arcuate nucleus, POMC neurons)
  Filename: brain/foundational/Foundational058ArcuatePOMCOutput.py
  Instance name: ArcuatePOMCOutput

NEURAL SUBSTRATE:
  Arcuate nucleus POMC neurons — the anorexigenic (satiety) population.
  POMC is cleaved into α-MSH (alpha-melanocyte-stimulating hormone),
  which acts on MC4R receptors in the PVN and LHA to suppress feeding.
  CART (cocaine-and-amphetamine-regulated transcript) is co-released
  and is also anorexigenic.

  POMC NEURONS:
  - Activated by: leptin (via leptin receptors on POMC neurons)
  - Inhibited by: ghrelin (via NPY/AgRP interneurons)
  - Project to: PVN (MC4R → CRH suppression), LHA (suppresses orexin),
    VTA (reward modulation)

  LEPTIN-POMC AXIS:
  High leptin (from adipose tissue) → POMC activation → α-MSH release →
  MC4R activation → satiety → reduced food intake

  Human analog: leptin-mediated satiety, α-MSH appetite suppression.

Output keys:
  pomc_activity: float [0.0–1.0] — POMC neuron firing rate
  alpha_msh_output: float [0.0–1.0] — α-MSH satiety signal
  cart_output: float [0.0–1.0] — CART anorexigenic output
  leptin_sensitivity: float [0.0–1.0] — responsiveness to leptin signal
  satiety_integrator: float [0.0–1.0] — composite satiety output

CITATIONS:
    PMC2838656 — Zheng H, Patterson LM, Rhodes CJ et al. (2010). A Potential Role
        for Hypothalamomedullary POMC Projections in Leptin-Induced Suppression of
        Food Intake. Brain Res.
    PMC8037945 — Jang Y, Heo JY, Lee MJ et al. (2021). Angiopoietin-Like Growth
        Factor Involved in Leptin Signaling in the Hypothalamus. Int J Mol Sci.

CITATIONS
---------
  - [Aponte 2011, Nat Neurosci 14:351, PMC3717573]
  - [Cone 2005, Nat Neurosci 8:571, doi:10.1038/nn1455]
  - [Cowley 2001, Nature 411:480, doi:10.1038/35078085]
"""

from brain.base_mechanism import BrainMechanism


class ArcuatePOMCOutput(BrainMechanism):
    """
    ARC POMC: α-MSH satiety, CART, leptin-mediated anorexia.

    Models POMC neurons as the arcuate satiety signal.
    """

    STATE_FIELDS = [
        "pomc_activity", "alpha_msh_output", "cart_output",
        "leptin_sensitivity", "satiety_integrator", "tick_count",
    ]

    POMC_GAIN = 0.55
    ALPHA_MSH_GAIN = 0.60
    CART_GAIN = 0.50

    def __init__(self, name: str = "ArcuatePOMCOutput_ArcuatePOMCOutput",
                 human_analog: str = "Arcuate POMC — α-MSH satiety neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["pomc_activity"] = 0.40
        self.state["alpha_msh_output"] = 0.35
        self.state["cart_output"] = 0.30
        self.state["leptin_sensitivity"] = 0.50
        self.state["satiety_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        insulin = prior.get("InsulinSignal", {}).get("insulin_level", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # Leptin sensitivity: changes with metabolic state
        # Low leptin (leptin resistance) reduces sensitivity
        leptin_sensitivity = leptin * 0.50 + (1.0 - ghrelin) * 0.30

        # POMC activity: activated by leptin + insulin + glucose
        leptin_activates = leptin * leptin_sensitivity
        insulin_activates = insulin * 0.30
        glucose_activates = glucose * 0.20
        # Ghrelin and stress suppress POMC
        ghrelin_suppresses = ghrelin * 0.30
        stress_suppresses = stress * 0.25
        pomc_raw = leptin_activates + insulin_activates + glucose_activates - ghrelin_suppresses - stress_suppresses
        pomc_activity = min(1.0, max(0.0, pomc_raw))

        # α-MSH output: proportional to POMC activity
        alpha_msh_output = pomc_activity * self.ALPHA_MSH_GAIN

        # CART output: co-released with α-MSH
        cart_output = pomc_activity * self.CART_GAIN

        # Satiety integrator
        satiety_integrator = (alpha_msh_output + cart_output) / 2.0

        # --- Persist ---
        self.state["pomc_activity"] = round(pomc_activity, 4)
        self.state["alpha_msh_output"] = round(alpha_msh_output, 4)
        self.state["cart_output"] = round(cart_output, 4)
        self.state["leptin_sensitivity"] = round(leptin_sensitivity, 4)
        self.state["satiety_integrator"] = round(satiety_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pomc_activity": round(pomc_activity, 4),
            "alpha_msh_output": round(alpha_msh_output, 4),
            "cart_output": round(cart_output, 4),
            "leptin_sensitivity": round(leptin_sensitivity, 4),
            "satiety_integrator": round(satiety_integrator, 4),
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


