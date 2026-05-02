"""
Build 38: Foundational038EnergySeekingDriver — Dorsomedial Hypothalamus (DMH) Drive
==============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — dorsomedial hypothalamus, DMH)
  Filename: brain/foundational/Foundational038EnergySeekingDriver.py
  Instance name: EnergySeekingDriver

NEURAL SUBSTRATE:
  Dorsomedial hypothalamus (DMH) — the "arousal and behavioral activation"
  center. DMH receives input from:
  - Suprachiasmatic nucleus (SCN): circadian drive → DMH → sympathetic output
  - Arcuate nucleus (NPY/AgRP, POMC): metabolic signals
  - Paraventricular nucleus (PVN): stress input

  DMH projects to:
  - Rostral raphe pallidus (rRPa): sympathetic thermoregulation
  - Locus coeruleus (LC): arousal
  - Lateral hypothalamus (LHA): behavioral activation

  KEY FUNCTION: DMH drives sympathetic output (thermogenesis, cardiovascular)
  and arousal in response to circadian signals and metabolic needs. Lesion of
  DMH eliminates circadian rise in sympathetic activity at dark onset.

  Human analog: circadian arousal, behavioral activation, energy mobilization.

Output keys:
  dmh_sympathetic_drive: float [0.0–1.0] — DMH → rRPa sympathetic output
  circadian_arousal_amplifier: float [0.0–1.0] — SCN → DMH → arousal
  energy_mobilization: float [0.0–1.0] — metabolic energy mobilization
  behavioral_activation: float [0.0–1.0] — general behavioral drive
  dmh_integrator: float [0.0–1.0] — composite DMH output

CITATIONS:
    PMC5108896 — Bonnavion P, Mickelsen LE, Fujita A et al. (2016). Hubs and Spokes
        of the Lateral Hypothalamus: Cell Types, Circuits and Behaviour. Nat Rev Neurosci.
    PMC12078644 — Shrivastava K, Athreya V, Lu Y et al. (2025). Energy State Guides
        Reward Seeking via an Extended Amygdala to Lateral Hypothalamus Pathway.
        Neuron.

CITATIONS
---------
  - [Berridge 2007, Psychopharmacology 191:391]
  - [Salamone 2007, Psychopharmacology 191:461]
  - [Wise 2004, Nat Rev Neurosci 5:483]
"""

from brain.base_mechanism import BrainMechanism


class EnergySeekingDriver(BrainMechanism):
    """
    Dorsomedial hypothalamus: circadian arousal and energy mobilization.

    DMH amplifies circadian signals and metabolic needs into sympathetic
    and behavioral activation output.
    """

    STATE_FIELDS = [
        "dmh_sympathetic_drive", "circadian_arousal_amplifier",
        "energy_mobilization", "behavioral_activation", "dmh_integrator", "tick_count",
    ]

    SYMPATHETIC_GAIN = 0.55
    CIRCADIAN_GAIN = 0.50
    ENERGY_GAIN = 0.45
    ACTIVATION_GAIN = 0.40

    def __init__(self, name: str = "EnergySeekingDriver_EnergySeekingDriver",
                 human_analog: str = "Dorsomedial hypothalamus — circadian arousal and drive",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["dmh_sympathetic_drive"] = 0.40
        self.state["circadian_arousal_amplifier"] = 0.50
        self.state["energy_mobilization"] = 0.30
        self.state["behavioral_activation"] = 0.40
        self.state["dmh_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        arcuate = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        sleep_drive = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Circadian arousal amplifier: DMH amplifies SCN signal
        circadian_amplifier = (circadian * self.CIRCADIAN_GAIN) + 0.30

        # Sympathetic drive: DMH → rRPa → sympathetic tone
        dmh_sympathetic = circadian_amplifier * self.SYMPATHETIC_GAIN
        # Stress adds sympathetic drive
        dmh_sympathetic += stress * 0.25
        # Sleep suppresses DMH
        dmh_sympathetic -= sleep_drive * 0.30

        # Energy mobilization: metabolic need → sympathetic mobilization
        energy_mobilization = (1.0 - arcuate) * self.ENERGY_GAIN
        # Low energy reserves → mobilize glucose/fat
        energy_mobilization += (1.0 - arcuate) * 0.30

        # Behavioral activation: orexin + circadian + stress
        behavioral_activation = (orexin * 0.35) + (circadian * 0.30) + (stress * 0.20)

        # DMH integrator: composite
        dmh_integrator = (dmh_sympathetic + behavioral_activation) / 2.0

        # --- Persist ---
        self.state["dmh_sympathetic_drive"] = round(dmh_sympathetic, 4)
        self.state["circadian_arousal_amplifier"] = round(circadian_amplifier, 4)
        self.state["energy_mobilization"] = round(energy_mobilization, 4)
        self.state["behavioral_activation"] = round(behavioral_activation, 4)
        self.state["dmh_integrator"] = round(dmh_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dmh_sympathetic_drive": round(dmh_sympathetic, 4),
            "circadian_arousal_amplifier": round(circadian_amplifier, 4),
            "energy_mobilization": round(energy_mobilization, 4),
            "behavioral_activation": round(behavioral_activation, 4),
            "dmh_integrator": round(dmh_integrator, 4),
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


