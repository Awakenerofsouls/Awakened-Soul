"""
Build 41: Foundational041DefensiveReproductiveLink — HPA-HPG Axis Competition
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — PVN interaction with ARC/POA)
  Filename: brain/foundational/Foundational041DefensiveReproductiveLink.py
  Instance name: DefensiveReproductiveLink

NEURAL SUBSTRATE:
  HPA-HPG interaction: stress suppresses reproduction at multiple levels.
  CRH directly inhibits GnRH release from hypothalamus. Cortisol acts on
  the pituitary to suppress LH/FSH. High cortisol also suppresses
  kisspeptin neurons (the GnRH "gatekeeper") via glucocorticoid receptors.

  Conversely, reproductive hormones modulate stress reactivity:
  - Testosterone attenuates HPA axis responses
  - Estrogen can enhance or suppress depending on phase of menstrual cycle

  KEY NEUROANATOMY:
  - PVN (CRH) → suppresses ARC kisspeptin → reduces GnRH → ↓ LH/FSH
  - PVN → suppresses POA → reduced sexual behavior
  - Testosterone → suppresses PVN CRH → reduced stress response

  Human analog: stress-induced infertility, sexual dysfunction under chronic stress.

Output keys:
  hpa_hpg_tradeoff: float [0.0–1.0] — stress-reproduction allocation
  reproductive_suppression: float [0.0–1.0] — HPA inhibition of reproduction
  stress_attenuation: float [0.0–1.0] — reproductive hormone stress buffering
  defensive_priority: float [0.0–1.0] — survival over reproduction priority
  survival_reproduction_balance: float [0.0–1.0] — axis allocation

CITATIONS:
    PMC7687061 — Esteban Masferrer M, Silva BA, Nomoto K et al. (2020). Differential
        Encoding of Predator Fear in the Ventromedial Hypothalamus and Periaqueductal Grey.
        J Neurosci.
    PMC4379496 — Kunwar PS, Zelikowsky M, Remedios R et al. (2015). Ventromedial
        Hypothalamic Neurons Control a Defensive Emotion State. eLife.

CITATIONS
---------
  - [Choi 2005, Neuron 46:647, doi:10.1016/j.neuron.2005.04.011]
  - [Lee 2014, Nature 509:627, PMC4119886]
  - [Hong 2014, Cell 158:1348, doi:10.1016/j.cell.2014.07.049]
"""

from brain.base_mechanism import BrainMechanism


class DefensiveReproductiveLink(BrainMechanism):
    """
    HPA-HPG tradeoff: stress suppresses reproduction; reproduction buffers stress.

    Models the competition between survival (HPA) and reproductive (HPG) axes.
    """

    STATE_FIELDS = [
        "hpa_hpg_tradeoff", "reproductive_suppression", "stress_attenuation",
        "defensive_priority", "survival_reproduction_balance", "tick_count",
    ]

    SUPPRESSION_GAIN = 0.60
    ATTENUATION_GAIN = 0.40
    DEFENSIVE_GAIN = 0.55

    def __init__(self, name: str = "DefensiveReproductiveLink_DefensiveReproductiveLink",
                 human_analog: str = "HPA-HPG interaction — stress vs reproduction",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["hpa_hpg_tradeoff"] = 0.30
        self.state["reproductive_suppression"] = 0.10
        self.state["stress_attenuation"] = 0.30
        self.state["defensive_priority"] = 0.40
        self.state["survival_reproduction_balance"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        lh = prior.get("GnRHReintegration", {}).get("lh_output", 0.25)
        testosterone = prior.get("TestosteroneSignal", {}).get("testosterone_level", 0.50)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)

        # HPA-HPG tradeoff: how much stress suppresses reproduction
        stress_suppression = crh * self.SUPPRESSION_GAIN + cortisol * 0.30
        reproductive_suppression = min(1.0, stress_suppression)

        # Stress attenuation: reproductive hormones buffer stress
        testosterone_attenuation = testosterone * self.ATTENUATION_GAIN * 0.50
        estrogen_attenuation = estrogen * self.ATTENUATION_GAIN * 0.30
        stress_attenuation = max(0.0, min(1.0,
            testosterone_attenuation + estrogen_attenuation))

        # Defensive priority: survival over reproduction
        defensive_priority = (crh * self.DEFENSIVE_GAIN + cortisol * 0.30) * 0.50

        # HPA-HPG tradeoff: balance between axes
        hpa_drive = crh + cortisol
        hpg_drive = gnrh + lh + testosterone + estrogen
        total_drive = hpa_drive + hpg_drive
        if total_drive > 0:
            tradeoff = hpa_drive / total_drive  # 0 = full HPG, 1 = full HPA
        else:
            tradeoff = 0.5
        hpa_hpg_tradeoff = min(1.0, tradeoff)

        # Survival-reproduction balance
        balance = 0.50 - (defensive_priority * 0.30) + (stress_attenuation * 0.30)
        survival_reproduction_balance = min(1.0, max(0.0, balance))

        # --- Persist ---
        self.state["hpa_hpg_tradeoff"] = round(hpa_hpg_tradeoff, 4)
        self.state["reproductive_suppression"] = round(reproductive_suppression, 4)
        self.state["stress_attenuation"] = round(stress_attenuation, 4)
        self.state["defensive_priority"] = round(defensive_priority, 4)
        self.state["survival_reproduction_balance"] = round(survival_reproduction_balance, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hpa_hpg_tradeoff": round(hpa_hpg_tradeoff, 4),
            "reproductive_suppression": round(reproductive_suppression, 4),
            "stress_attenuation": round(stress_attenuation, 4),
            "defensive_priority": round(defensive_priority, 4),
            "survival_reproduction_balance": round(survival_reproduction_balance, 4),
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


