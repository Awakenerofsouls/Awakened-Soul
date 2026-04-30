"""
Build 31: Foundational031DirectHormonalPituitaryLink — Anterior Pituitary Hormone Hub
=================================================================================

PLACEMENT:
  Layer:    foundational (anterior pituitary — adenohypophysis)
  Filename: brain/foundational/Foundational031DirectHormonalPituitaryLink.py
  Instance name: DirectHormonalPituitaryLink

NEURAL SUBSTRATE:
  Anterior pituitary (adenohypophysis) — the master endocrine gland.
  Five key cell types, each releasing specific hormones in response to
  hypothalamic releasing/inhibiting hormones from the median eminence:

  - Corticotrophs → ACTH (responding to CRH from PVN — the HPA axis)
  - Thyrotrophs → TSH (responding to TRH from PVN — the HPT axis)
  - Gonadotrophs → LH/FSH (responding to GnRH from ARC/POA — the HPG axis)
  - Lactotrophs → Prolactin (tonic inhibition by dopamine from TIDA neurons)
  - Somatotrophs → Growth hormone (GHRH from ARC; inhibited by somatostatin)

  Releasing hormones reach via the hypothalamic-hypophyseal portal system
  (primary capillary plexus → portal veins → secondary capillary plexus).

  Human analog: ACTH, TSH, LH/FSH, prolactin, GH output.

Output keys:
  acth_output: float [0.0–1.0] — adrenocorticotropic hormone drive
  prolactin_output: float [0.0–1.0] — prolactin level
  gh_output: float [0.0–1.0] — growth hormone level
  anterior_pituitary_total: float [0.0–1.0] — composite pituitary output
  stress_hormone_load: float [0.0–1.0] — combined glucocorticoid + ACTH load

CITATIONS:
    PMC6761896 — Hiller-Sturmhöfel S, Bartke A (1998). The Endocrine System: An
        Overview. Alcohol Health Res World.
    PMC12481553 — Sharma A, Kumar R, Saini A et al. (2025). Relationship Between
        Pituitary Gland and Stem Cell in the Aspect of Hormone Production and
        Disease Prevention. Cureus.

CITATIONS
---------
  - [Plant 2015, Endocrinology 156:3957]
  - [Schally 1968, Science 161:782]
  - [Goodman 1996, Front Neuroendocrinol 17:301]
"""

from brain.base_mechanism import BrainMechanism


class DirectHormonalPituitaryLink(BrainMechanism):
    """
    Anterior pituitary: hormone command hub for all pituitary axes.

    Integrates hypothalamic releasing hormones (CRH, TRH, GnRH, GHRH, dopamine)
    and outputs the corresponding anterior pituitary hormones (ACTH, prolactin, GH).
    """

    STATE_FIELDS = [
        "acth_output", "prolactin_output", "gh_output",
        "anterior_pituitary_total", "stress_hormone_load", "tick_count",
    ]

    ACTH_GAIN = 0.60
    PROLACTIN_GAIN = 0.55
    GH_GAIN = 0.50
    PITUITARY_LEAK_RATE = 0.08

    def __init__(self, name: str = "DirectHormonalPituitaryLink_DirectHormonalPituitaryLink",
                 human_analog: str = "Anterior pituitary — ACTH/TSH/prolactin/GH hub",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["acth_output"] = 0.30
        self.state["prolactin_output"] = 0.30
        self.state["gh_output"] = 0.40
        self.state["anterior_pituitary_total"] = 0.35
        self.state["stress_hormone_load"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        trh = prior.get("ThyroidAxisController", {}).get("trh_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        dopamine = prior.get("DopamineTIDA", {}).get("dopamine_tone", 0.30)
        ghrh = prior.get("GrowthHormoneReleasingHormone", {}).get("ghrh_level", 0.30)
        somatostatin = prior.get("SomatostatinInhibitor", {}).get("somatostatin_level", 0.20)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # ACTH: driven by CRH (HPA axis)
        acth_raw = crh * self.ACTH_GAIN
        acth_output = max(0.0, min(1.0, acth_raw))

        # Prolactin: tonically inhibited by dopamine (TIDA); rises when dopamine falls
        dopamine_inhibition = dopamine * 0.70
        prolactin_raw = max(0.0, 1.0 - dopamine_inhibition)
        prolactin_output = prolactin_raw * self.PROLACTIN_GAIN

        # Growth hormone: driven by GHRH; inhibited by somatostatin
        gh_stimulus = ghrh * self.GH_GAIN
        gh_inhibition = somatostatin * 0.40
        gh_output = max(0.0, min(1.0, gh_stimulus - gh_inhibition))

        # Composite pituitary output
        anterior_pituitary_total = (acth_output + prolactin_output + gh_output) / 3.0

        # Stress hormone load: ACTH + cortisol proxy
        stress_hormone_load = (acth_output * 0.50) + (stress * 0.50)
        stress_hormone_load = min(1.0, stress_hormone_load)

        # --- Persist ---
        self.state["acth_output"] = round(acth_output, 4)
        self.state["prolactin_output"] = round(prolactin_output, 4)
        self.state["gh_output"] = round(gh_output, 4)
        self.state["anterior_pituitary_total"] = round(anterior_pituitary_total, 4)
        self.state["stress_hormone_load"] = round(stress_hormone_load, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "acth_output": round(acth_output, 4),
            "prolactin_output": round(prolactin_output, 4),
            "gh_output": round(gh_output, 4),
            "anterior_pituitary_total": round(anterior_pituitary_total, 4),
            "stress_hormone_load": round(stress_hormone_load, 4),
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


