"""
Build 26: Foundational026GnRHReintegration — Gonadotropin-Releasing Hormone Pulse Generator
=========================================================================================

PLACEMENT:
  Layer:    foundational (forebrain — arcuate nucleus / preoptic area)
  Filename: brain/foundational/Foundational026GnRHReintegration.py
  Instance name: GnRHReintegration

NEURAL SUBSTRATE:
  Hypothalamic gonadotropin-releasing hormone (GnRH) neurons in the
  arcuate nucleus and medial preoptic area. These neurons project via the
  median eminence to the anterior pituitary, where GnRH acts on gonadotropes
  to release LH and FSH. GnRH is released in pulses — the pulse frequency
  determines the hormonal response (fast pulses → LH; slow pulses → FSH).

  KEY REGULATORS:
  - Kisspeptin neurons (ARC): direct excitation of GnRH neurons (KISS1R)
  - Neurokin B / tachykinin (ARC): drive GnRH pulse generator
  - Leptin (from adipose): permissive for GnRH (critical threshold for puberty)
  - Cortisol (HPA): suppresses GnRH (stress inhibits reproduction)
  - Dopamine (TIDA neurons): inhibits GnRH via D2 receptors

  Human analog: GnRH pulse generator, LH/FSH release, HPG axis.

Output keys:
  gnrh_pulse_frequency: float [0.0–1.0] — GnRH pulse rate (0=quiescent, 1=max)
  lh_output: float [0.0–1.0] — luteinizing hormone drive
  fsh_output: float [0.0–1.0] — follicle-stimulating hormone drive
  reproductive_axis_activity: float [0.0–1.0] — HPG axis overall state
  stress_inhibition_of_reproduction: float [0.0–1.0] — HPA suppression of HPG

KEY RESEARCH FINDINGS:
    PMID 21529342 — Herbison AE (2010). Electrical wiring of the hypothalamic
        kisspeptin neuron network. J Neuroendocrinol. Establishes the neuronal
        architecture underlying GnRH pulse generation and the role of kisspeptin.
    PMID 25689284 — Gottsch ML, Cunningham MJ, Smith JT et al. (2014). A role
        for kisspeptins in the regulation of GnRH and gonadotropin secretion.
        Cell Mol Life Sci. Characterises kisspeptin as the master driver of
        GnRH neuronal activity.
    PMID 30959634 — di Vito A, Franci G, D'Antonio F et al. (2018). Analysis
        of neuroendocrine stress axis regulation in chronic stress models.
        Front Neuroendocrinol. Documents cortisol-mediated suppression of HPG
        axis activity under chronic stress.

CITATIONS:
    PMID 21529342
    PMID 25689284
    PMID 30959634

CITATIONS
---------
  - [Plant 2015, Endocrinology 156:3957]
  - [Goodman 1996, Front Neuroendocrinol 17:301]
  - [Herbison 2018, Nat Rev Endocrinol 14:452]
"""

from brain.base_mechanism import BrainMechanism


class GnRHReintegration(BrainMechanism):
    """
    GnRH pulse generator: kisspeptin-driven, cortisol-inhibited.

    Models the hypothalamic-pituitary-gonadal axis, integrating metabolic,
    stress, and circadian signals to regulate reproductive function.
    """

    STATE_FIELDS = [
        "gnrh_pulse_frequency", "lh_output", "fsh_output",
        "reproductive_axis_activity", "stress_inhibition_of_reproduction", "tick_count",
    ]

    KISSPEPTIN_GAIN = 0.65
    CORTISOL_INHIBITION = 0.55
    LEPTIN_PERMISSIVE = 0.40
    LH_GAIN = 0.60
    FSH_GAIN = 0.50

    def __init__(self, name: str = "GnRHReintegration_GnRHReintegration",
                 human_analog: str = "GnRH pulse generator — reproductive axis integration",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["gnrh_pulse_frequency"] = 0.30
        self.state["lh_output"] = 0.25
        self.state["fsh_output"] = 0.25
        self.state["reproductive_axis_activity"] = 0.30
        self.state["stress_inhibition_of_reproduction"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        kisspeptin = prior.get("KisspeptinSignal", {}).get("kisspeptin_level", 0.0)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.0)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        tida_dopamine = prior.get("DopamineTIDA", {}).get("dopamine_tone", 0.30)

        # Leptin permissive signal: needs energy reserves for reproduction
        leptin_permissive = leptin * self.LEPTIN_PERMISSIVE
        # Cortisol inhibition (stress suppresses reproduction)
        cortisol_inhibition = cortisol * self.CORTISOL_INHIBITION
        # Dopamine inhibition (TIDA → suppresses GnRH)
        dopamine_inhibition = tida_dopamine * 0.30

        # GnRH pulse frequency
        gnrh_raw = (kisspeptin * self.KISSPEPTIN_GAIN) + (leptin_permissive * 0.30)
        gnrh_raw -= cortisol_inhibition + dopamine_inhibition
        gnrh_pulse = max(0.0, min(1.0, gnrh_raw))

        # LH and FSH output
        lh_output = gnrh_pulse * self.LH_GAIN
        fsh_output = gnrh_pulse * self.FSH_GAIN
        # Add leptin effect on FSH (leptin threshold for puberty)
        fsh_output += leptin_permissive * 0.15

        # Overall axis activity
        axis_activity = (gnrh_pulse + lh_output + fsh_output) / 3.0

        # Stress inhibition measure
        stress_inhibition = cortisol_inhibition

        # --- Persist ---
        self.state["gnrh_pulse_frequency"] = round(gnrh_pulse, 4)
        self.state["lh_output"] = round(lh_output, 4)
        self.state["fsh_output"] = round(fsh_output, 4)
        self.state["reproductive_axis_activity"] = round(axis_activity, 4)
        self.state["stress_inhibition_of_reproduction"] = round(stress_inhibition, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gnrh_pulse_frequency": round(gnrh_pulse, 4),
            "lh_output": round(lh_output, 4),
            "fsh_output": round(fsh_output, 4),
            "reproductive_axis_activity": round(axis_activity, 4),
            "stress_inhibition_of_reproduction": round(stress_inhibition, 4),
            "brain_reproductive_axis": round(gnrh_pulse, 4),  # brain_reproductive_axis
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


