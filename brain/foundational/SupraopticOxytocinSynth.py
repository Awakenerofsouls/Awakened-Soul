"""
Build 57: Foundational057SupraopticOxytocinSynth — SON Oxytocin Magnocellular System
=================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — supraoptic nucleus, SON)
  Filename: brain/foundational/Foundational057SupraopticOxytocinSynth.py
  Instance name: SupraopticOxytocinSynth

NEURAL SUBSTRATE:
  Supraoptic nucleus (SON) — the second site of magnocellular neurosecretory
  neurons (along with PVN). SON oxytocin neurons project to the posterior
  pituitary (neurohypophysis). Their axons traverse the hypothalamic
  pituitary tract to release oxytocin directly into the systemic circulation.

  OXytocin FUNCTIONS:
  - Uterine contraction during parturition (myometrium)
  - Milk letdown during breastfeeding (myoepithelial cells)
  - Social bonding (OTR-A receptor in NAc, prefrontal cortex)
  - Stress reduction (OTR in amygdala, hypothalamus)
  - Trust and reciprocity (intranasal OT studies)

  STIMULI FOR OXytocin RELEASE:
  - Cervical stretch (parturition) → OT burst → uterine contractions
  - Nipple suckling (breastfeeding) → OT burst → milk ejection
  - Social touch, social interaction → OT release
  - Stress → OT counteracts CRH (social buffering hypothesis)

  Human analog: oxytocin, social bonding, childbirth, lactation.

Output keys:
  oxytocin_level: float [0.0–1.0] — circulating oxytocin level
  uterine_contraction_drive: float [0.0–1.0] — parturition signal
  milk_ejection_drive: float [0.0–1.0] — breastfeeding letdown
  social_bonding_signal: float [0.0–1.0] — social affiliation drive
  stress_buffering_oxytocin: float [0.0–1.0] — OT's stress-attenuating effect

CITATIONS:
    PMC8509519 — Liu CM, Spaulding MO, Rea JJ et al. (2021). Oxytocin and Food
        Intake Control: Neural, Behavioral, and Signaling Mechanisms. Neural Plast.
    PMC12201962 — Hayashi H, Tateishi S, Inutsuka A et al. (2025). Oxytocin
        Facilitates Human Touch-Induced Play Behavior in Rats. J Neurosci.

CITATIONS
---------
  - [Brownstein 1980, Science 207:373]
  - [Burbach 2001, Endocr Rev 22:155]
  - [Sofroniew 1983, J Comp Neurol 213:165]
"""

from brain.base_mechanism import BrainMechanism


class SupraopticOxytocinSynth(BrainMechanism):
    """
    SON oxytocin: parturition, lactation, social bonding, stress buffering.

    Models oxytocin synthesis and release from SON magnocellular neurons.
    """

    STATE_FIELDS = [
        "oxytocin_level", "uterine_contraction_drive", "milk_ejection_drive",
        "social_bonding_signal", "stress_buffering_oxytocin", "tick_count",
    ]

    OXYTOCIN_GAIN = 0.60
    SOCIAL_GAIN = 0.50
    STRESS_BUFFER_GAIN = 0.40

    def __init__(self, name: str = "SupraopticOxytocinSynth_SupraopticOxytocinSynth",
                 human_analog: str = "SON — oxytocin synthesis and release",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["oxytocin_level"] = 0.20
        self.state["uterine_contraction_drive"] = 0.0
        self.state["milk_ejection_drive"] = 0.0
        self.state["social_bonding_signal"] = 0.30
        self.state["stress_buffering_oxytocin"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        social_touch = prior.get("SomatosensoryCortexTouch", {}).get("social_touch_intensity", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        suckling = prior.get("NippleSucklingSignal", {}).get("suckling_intensity", 0.0)
        uterine = prior.get("UterineStretchReceptor", {}).get("cervical_stretch", 0.0)
        oxytocin = self.state["oxytocin_level"]

        # Oxytocin level: slow integrator with social and stress triggers
        social_trigger = social_touch * self.SOCIAL_GAIN
        # Estrogen potentiates OT release (positive feedback)
        estrogen_potentiation = estrogen * 0.30
        # Stress buffering: OT rises to counteract CRH
        stress_buffer = (1.0 - stress) * self.STRESS_BUFFER_GAIN * 0.30
        # Suckling drives milk ejection
        suckling_drive = suckling * 0.50
        # Uterine stretch drives parturition OT bursts
        uterine_drive = uterine * 0.60

        # Net OT change
        ot_rise = social_trigger + suckling_drive + uterine_drive * 0.20
        ot_fall = 0.04  # OT decays (short half-life ~3-5 min)
        oxytocin_raw = max(0.0, oxytocin - ot_fall + ot_rise * 0.15)
        oxytocin_level = min(1.0, oxytocin_raw)

        # Uterine contraction drive
        uterine_contraction_drive = uterine * oxytocin_level * 0.80

        # Milk ejection drive
        milk_ejection_drive = suckling * oxytocin_level * 0.70

        # Social bonding signal
        social_bonding_signal = (social_touch + social_trigger) * oxytocin_level * self.SOCIAL_GAIN

        # Stress buffering oxytocin
        stress_buffering_oxytocin = oxytocin_level * (1.0 - stress) * self.STRESS_BUFFER_GAIN

        # --- Persist ---
        self.state["oxytocin_level"] = round(oxytocin_level, 4)
        self.state["uterine_contraction_drive"] = round(uterine_contraction_drive, 4)
        self.state["milk_ejection_drive"] = round(milk_ejection_drive, 4)
        self.state["social_bonding_signal"] = round(social_bonding_signal, 4)
        self.state["stress_buffering_oxytocin"] = round(stress_buffering_oxytocin, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "oxytocin_level": round(oxytocin_level, 4),
            "uterine_contraction_drive": round(uterine_contraction_drive, 4),
            "milk_ejection_drive": round(milk_ejection_drive, 4),
            "social_bonding_signal": round(social_bonding_signal, 4),
            "stress_buffering_oxytocin": round(stress_buffering_oxytocin, 4),
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


