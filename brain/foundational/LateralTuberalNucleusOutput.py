"""
Build 60: Foundational060LateralTuberalNucleusOutput — Lateral Tuberal Nucleus Integration
================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral tuberal nucleus)
  Filename: brain/foundational/Foundational060LateralTuberalNucleusOutput.py
  Instance name: LateralTuberalNucleusOutput

NEURAL SUBSTRATE:
  Lateral tuberal nucleus (LTN) — a hypothalamic nucleus adjacent to
  the lateral hypothalamus, poorly understood but implicated in:
  - Integration of metabolic and autonomic signals
  - Projects to the bed nucleus of the stria terminalis (BNST)
  - Connected to lateral hypothalamus and zona incerta
  - Contains neurotensin and NPY neurons

  The LTN is part of the extended lateral hypothalamic area and
  integrates multiple drives: hunger, thirst, sexual motivation,
  and defensive behaviors.

  Human analog: general drive integration, hypothalamic motivation.

Output keys:
  ltn_integrator: float [0.0–1.0] — composite drive integrator output
  motivational_weight: float [0.0–1.0] — motivational salience weighting
  drive_coordination: float [0.0–1.0] — coordination of multiple drives
  ltn_threat_response: float [0.0–1.0] — threat-driven activation
  lateral_tuberal_composite: float [0.0–1.0] — total LTN output

CITATIONS:
    PMC10135972 — Vraka K, Mytilinaios D, Katsenos AP et al. (2023). Cellular
        Localization of Orexin 1 Receptor in Human Hypothalamus. Neuropeptides.
    PMC12293592 — Chen X, Wang Y, Fu S et al. (2025). The Integrated Function of
        the Lateral Hypothalamus in Energy Homeostasis. Nat Commun.

CITATIONS
---------
  - [Saper 1976, J Comp Neurol 169:409]
  - [Swanson 1987, Annu Rev Neurosci 10:285]
  - [Williams 2001, Neuroscience 105:495]
"""

from brain.base_mechanism import BrainMechanism


class LateralTuberalNucleusOutput(BrainMechanism):
    """
    Lateral tuberal nucleus: general drive integration.

    Models the LTN as a general-purpose drive integrator.
    """

    STATE_FIELDS = [
        "ltn_integrator", "motivational_weight", "drive_coordination",
        "ltn_threat_response", "lateral_tuberal_composite", "tick_count",
    ]

    INTEGRATOR_GAIN = 0.50
    THREAT_GAIN = 0.45

    def __init__(self, name: str = "LateralTuberalNucleusOutput_LateralTuberalNucleusOutput",
                 human_analog: str = "Lateral tuberal nucleus — drive integrator",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["ltn_integrator"] = 0.40
        self.state["motivational_weight"] = 0.30
        self.state["drive_coordination"] = 0.40
        self.state["ltn_threat_response"] = 0.0
        self.state["lateral_tuberal_composite"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        feeding = prior.get("FeedingStressIntegrator", {}).get("feeding_drive", 0.30)
        thirst = prior.get("FacialGradientSensor", {}).get("thirst_drive", 0.20)
        sexual = prior.get("ThermoSexualBalancer", {}).get("sexual_motivation", 0.30)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)

        # LTN integrator: sums all drives
        drive_sum = feeding + thirst + sexual + arousal
        ltn_integrator = min(1.0, drive_sum * self.INTEGRATOR_GAIN * 0.25)

        # Motivational weight: highest drive dominates
        drives = [feeding, thirst, sexual, arousal]
        max_drive = max(drives)
        motivational_weight = max_drive

        # Drive coordination: how well competing drives are coordinated
        # Low variance = well-coordinated; high variance = conflict
        drive_mean = sum(drives) / len(drives)
        drive_variance = sum((d - drive_mean) ** 2 for d in drives) / len(drives)
        drive_coordination = max(0.0, 1.0 - drive_variance * 2.0)

        # LTN threat response: stress and amygdala activate LTN
        ltn_threat = stress * self.THREAT_GAIN + amygdala * 0.30
        ltn_threat_response = min(1.0, ltn_threat)

        # Lateral tuberal composite
        lateral_tuberal_composite = (ltn_integrator + motivational_weight + ltn_threat_response) / 3.0

        # --- Persist ---
        self.state["ltn_integrator"] = round(ltn_integrator, 4)
        self.state["motivational_weight"] = round(motivational_weight, 4)
        self.state["drive_coordination"] = round(drive_coordination, 4)
        self.state["ltn_threat_response"] = round(ltn_threat_response, 4)
        self.state["lateral_tuberal_composite"] = round(lateral_tuberal_composite, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ltn_integrator": round(ltn_integrator, 4),
            "motivational_weight": round(motivational_weight, 4),
            "drive_coordination": round(drive_coordination, 4),
            "ltn_threat_response": round(ltn_threat_response, 4),
            "lateral_tuberal_composite": round(lateral_tuberal_composite, 4),
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


