"""
Build 37: Foundational037FeedingStressIntegrator — Lateral Hypothalamus Feeding + Stress
=====================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral hypothalamus, LHA)
  Filename: brain/foundational/Foundational037FeedingStressIntegrator.py
  Instance name: FeedingStressIntegrator

NEURAL SUBSTRATE:
  Lateral hypothalamus (LHA) — the "hunger center." Contains:
  - Orexin/hypocretin neurons: wake-promoting, also drive food-seeking
  - MCH (melanin-concentrating hormone) neurons: orexigenic, promote feeding
  - NPY/AgRP terminals from arcuate: orexigenic, directly innervate LHA
  - GABAergic "feeding neurons": stimulation → eating; lesion → starvation

  LHA projects to:
  - Ventral tegmental area (VTA): reward for food
  - Paraventricular nucleus (PVN): stress response integration
  - Lateral habenula: aversion signals

  STRESS-FEEDING INTERACTION: Acute stress suppresses feeding via CRH.
  Chronic stress can drive "comfort eating" via NPY from arcuate.
  Leptin signals energy sufficiency → suppresses LHA feeding drive.

  Human analog: hunger, food-seeking, stress eating, leptin suppression.

Output keys:
  feeding_drive: float [0.0–1.0] — hunger motivation intensity
  food_seeking_arousal: float [0.0–1.0] — orexin-driven food search motivation
  leptin_suppression: float [0.0–1.0] — satiety-mediated feeding suppression
  stress_anorexia: float [0.0–1.0] — acute stress suppression of feeding
  lha_integrator: float [0.0–1.0] — composite LHA output

CITATIONS:
    PMC11164563 — DiFazio LE, Fanselow M, Sharpe MJ (2022). The Effect of Stress and
        Reward on Encoding Future Fear Memories. Learn Mem.
    PMC9436700 — Meisner OC, Nair A, Chang SWC (2022). Amygdala Connectivity and
        Implications for Social Cognition and Disorders. Front Neurosci.

CITATIONS
---------
  - [Dallman 2003, Physiol Behav 79:683]
  - [Adam 2007, Physiol Behav 91:449]
  - [Maniam 2012, Front Neuroendocrinol 33:106]
"""

from brain.base_mechanism import BrainMechanism


class FeedingStressIntegrator(BrainMechanism):
    """
    Lateral hypothalamus: feeding drive, stress-feeding interactions.

    Models the hunger center, integrating metabolic signals (leptin, ghrelin)
    and stress signals to drive feeding behavior.
    """

    STATE_FIELDS = [
        "feeding_drive", "food_seeking_arousal", "leptin_suppression",
        "stress_anorexia", "lha_integrator", "tick_count",
    ]

    FEEDING_GAIN = 0.55
    SEEKING_GAIN = 0.50
    LEPTIN_GAIN = 0.45
    STRESS_ANOREXIA_GAIN = 0.60

    def __init__(self, name: str = "FeedingStressIntegrator_FeedingStressIntegrator",
                 human_analog: str = "Lateral hypothalamus — feeding drive and stress",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["feeding_drive"] = 0.40
        self.state["food_seeking_arousal"] = 0.30
        self.state["leptin_suppression"] = 0.20
        self.state["stress_anorexia"] = 0.0
        self.state["lha_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        npy = prior.get("AppetiteNPYBalancer", {}).get("npy_level", 0.30)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        glucagon = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)

        # Leptin suppression: high leptin = energy sufficiency = stop eating
        leptin_suppression = leptin * self.LEPTIN_GAIN

        # Stress anorexia: CRH acutely suppresses feeding
        stress_anorexia = stress * self.STRESS_ANOREXIA_GAIN

        # Feeding drive: ghrelin + NPY - leptin suppression - stress anorexia
        feeding_raw = (ghrelin * 0.35) + (npy * 0.35) - leptin_suppression - stress_anorexia
        feeding_drive = max(0.0, min(1.0, feeding_raw))

        # Food seeking arousal: orexin drives exploration/food-seeking
        food_seeking = orexin * self.SEEKING_GAIN
        # Low glucose drives food seeking
        food_seeking += (1.0 - glucagon) * 0.25
        food_seeking = min(1.0, food_seeking)

        # LHA integrator: composite output
        lha_integrator = (feeding_drive + food_seeking) / 2.0

        # --- Persist ---
        self.state["feeding_drive"] = round(feeding_drive, 4)
        self.state["food_seeking_arousal"] = round(food_seeking, 4)
        self.state["leptin_suppression"] = round(leptin_suppression, 4)
        self.state["stress_anorexia"] = round(stress_anorexia, 4)
        self.state["lha_integrator"] = round(lha_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "feeding_drive": round(feeding_drive, 4),
            "food_seeking_arousal": round(food_seeking, 4),
            "leptin_suppression": round(leptin_suppression, 4),
            "stress_anorexia": round(stress_anorexia, 4),
            "lha_integrator": round(lha_integrator, 4),
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


