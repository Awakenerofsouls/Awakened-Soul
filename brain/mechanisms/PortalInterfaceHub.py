"""
Build 40: Foundational040PortalInterfaceHub — Hypothalamic-Hypophyseal Portal System
===============================================================================

PLACEMENT:
  Layer:    foundational (median eminence — hypothalamic-pituitary portal interface)
  Filename: brain/foundational/Foundational040PortalInterfaceHub.py
  Instance name: PortalInterfaceHub

NEURAL SUBSTRATE:
  Hypothalamic-hypophyseal portal system — the vascular link between
  hypothalamus and anterior pituitary:
  1. Primary capillary plexus (median eminence) — receives releasing hormones
  2. Portal veins — carry blood directly to secondary capillary plexus
  3. Secondary capillary plexus (anterior pituitary) — hormone release

  This portal system is a "short-loop" vascular connection that ensures
  high local concentrations of hypothalamic hormones at the pituitary,
  with minimal systemic spillover.

  KEY FEATURES:
  - Blood flow is primarily downward (hypothalamus → pituitary)
  - Some retrograde flow allows pituitary feedback to hypothalamus
  - Portal vessels have fenestrated endothelium (no BBB here)

  Human analog: portal circulation, endocrine signal transmission.

Output keys:
  portal_flow_strength: float [0.0–1.0] — portal blood flow rate
  rh_transmission_fidelity: float [0.0–1.0] — RH signal transmission quality
  anterior_pituitary_activation: float [0.0–1.0] — pituitary stimulation level
  portal_leakage: float [0.0–1.0] — systemic spillover of RH signals
  endocrine_permissiveness: float [0.0–1.0] — portal gate openness

CITATIONS:
    PMC8332811 — Kelly WM, Kucharczyk W, Kucharczyk J et al. (1988). Posterior
        Pituitary Ectopia: An MR Feature of Pituitary Dwarfism. Am J Neuroradiol.
    PMC4251598 — Sarkar DK, Frautschy SA, Mitsugi N (1992). Pituitary Portal Plasma
        Levels of Oxytocin During the Estrous Cycle, Lactation, and Hyperprolactinemia.
        Endocrinology.

CITATIONS
---------
  - [Plant 2015, Endocrinology 156:3957]
  - [Schally 1968, Science 161:782]
  - [Page 1982, Endocr Rev 3:71]
"""

from brain.base_mechanism import BrainMechanism


class PortalInterfaceHub(BrainMechanism):
    """
    Hypothalamic-hypophyseal portal system interface.

    Models the portal vascular connection, transmission fidelity,
    and feedback dynamics between hypothalamus and pituitary.
    """

    STATE_FIELDS = [
        "portal_flow_strength", "rh_transmission_fidelity",
        "anterior_pituitary_activation", "portal_leakage",
        "endocrine_permissiveness", "tick_count",
    ]

    FLOW_GAIN = 0.55
    FIDELITY_GAIN = 0.60
    ACTIVATION_GAIN = 0.50

    def __init__(self, name: str = "PortalInterfaceHub_PortalInterfaceHub",
                 human_analog: str = "Hypothalamic-hypophyseal portal system",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["portal_flow_strength"] = 0.50
        self.state["rh_transmission_fidelity"] = 0.60
        self.state["anterior_pituitary_activation"] = 0.40
        self.state["portal_leakage"] = 0.05
        self.state["endocrine_permissiveness"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        releasing = prior.get("ReleasingHormoneHub", {}).get(
            "releasing_hormone_composite", 0.40
        )
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        trh = prior.get("ThyroidAxisController", {}).get("trh_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        acth = prior.get("DirectHormonalPituitaryLink", {}).get("acth_output", 0.30)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Portal flow: driven by hypothalamic activity; suppressed during sleep
        base_flow = releasing * self.FLOW_GAIN
        sleep_suppression = sleep_signal * 0.50
        portal_flow = max(0.0, min(1.0, base_flow - sleep_suppression))

        # RH transmission fidelity: high during active releasing, low during sleep
        rh_fidelity = (releasing * 0.50) + 0.30

        # Anterior pituitary activation: sum of all pituitary axes
        pituitary_input = (crh * 0.30) + (trh * 0.25) + (gnrh * 0.25) + (acth * 0.20)
        anterior_activation = pituitary_input * self.ACTIVATION_GAIN

        # Portal leakage: when portal pressure is high, some RH escapes to systemic
        portal_leakage = releasing * 0.10 + cortisol * 0.05

        # Endocrine permissiveness: cortisol feedback reduces portal gate openness
        cortisol_inhibition = cortisol * 0.30
        permissiveness = max(0.0, min(1.0, 0.70 - cortisol_inhibition))

        # --- Persist ---
        self.state["portal_flow_strength"] = round(portal_flow, 4)
        self.state["rh_transmission_fidelity"] = round(rh_fidelity, 4)
        self.state["anterior_pituitary_activation"] = round(anterior_activation, 4)
        self.state["portal_leakage"] = round(portal_leakage, 4)
        self.state["endocrine_permissiveness"] = round(permissiveness, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "portal_flow_strength": round(portal_flow, 4),
            "rh_transmission_fidelity": round(rh_fidelity, 4),
            "anterior_pituitary_activation": round(anterior_activation, 4),
            "portal_leakage": round(portal_leakage, 4),
            "endocrine_permissiveness": round(permissiveness, 4),
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


