"""
Build 47: Foundational047TactileProprioRelay — Spinal Somatosensory Relay
======================================================================

PLACEMENT:
  Layer:    foundational (spinal cord — dorsal horn, Rexed laminae III-VI)
  Filename: brain/foundational/Foundational047TactileProprioRelay.py
  Instance name: TactileProprioRelay

NEURAL SUBSTRATE:
  Spinal dorsal horn — the somatosensory relay station for tactile and
  proprioceptive information entering the spinal cord:

  LAMINAR ORGANIZATION:
  - Lamina I (marginal zone): nociceptive (pain) specific neurons
  - Lamina II (substantia gelatinosa): nociceptive projection, gate control
  - Lamina III-IV (nucleus proprius): low-threshold mechanoreceptors (LTMR)
  - Lamina V-VI: wide dynamic range (WDR) neurons, viscerotopic input

  AFFERENT FIBER TYPES:
  - Aδ (fast pain): → Lamina I
  - Aβ (touch, vibration): → Lamina III-IV
  - C (slow pain): → Lamina II
  - Ia (muscle spindle): → Clarke's column (cerebellar input)
  - II (Golgi tendon): → inhibitory interneurons

  Human analog: tactile sensation, proprioception, spinothalamic tract.

Output keys:
  tactile_discrimination: float [0.0–1.0] — fine touch discrimination
  proprioceptive_accuracy: float [0.0–1.0] — body position accuracy
  dorsal_horn_gate: float [0.0–1.0] — substantia gelatinosa gate state
  pain_signal_transmission: float [0.0–1.0] — nociceptive relay level
  somatosensory_integration: float [0.0–1.0] — multi-modal somatosensory fusion

CITATIONS:
    PMC6330897 — Delhaye BP, Long KH, Bensmaia SJ (2018). Neural Basis of Touch and
        Proprioception in Primate Cortex. Compr Physiol.
    PMC11502235 — Rubio-Teves M, Martín-Correa P, Alonso-Martínez C et al. (2024).
        Beyond Barrels: Diverse Thalamocortical Projection Motifs in the Mouse Ventral
        Posterior Complex. J Comp Neurol.

CITATIONS
---------
  - [Mountcastle 1957, J Neurophysiol 20:408]
  - [Kaas 1983, Physiol Rev 63:206]
  - [Proske 2012, Physiol Rev 92:1651]
"""

from brain.base_mechanism import BrainMechanism


class TactileProprioRelay(BrainMechanism):
    """
    Spinal dorsal horn: tactile and proprioceptive relay.

    Models the dorsal horn as a gate-controlled somatosensory relay
    with tactile discrimination and proprioceptive accuracy.
    """

    STATE_FIELDS = [
        "tactile_discrimination", "proprioceptive_accuracy", "dorsal_horn_gate",
        "pain_signal_transmission", "somatosensory_integration", "tick_count",
    ]

    TACTILE_GAIN = 0.60
    PROPRIOCEPTIVE_GAIN = 0.55
    GATE_GAIN = 0.50

    def __init__(self, name: str = "TactileProprioRelay_TactileProprioRelay",
                 human_analog: str = "Spinal dorsal horn — tactile and proprioceptive relay",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["tactile_discrimination"] = 0.60
        self.state["proprioceptive_accuracy"] = 0.60
        self.state["dorsal_horn_gate"] = 0.50
        self.state["pain_signal_transmission"] = 0.20
        self.state["somatosensory_integration"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        gate = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        tactile_input = prior.get("PeripheralTouch", {}).get("touch_intensity", 0.50)
        proprioceptive_input = prior.get("VestibularIntegrator", {}).get(
            "proprioceptive_signal", 0.50
        )
        pain_signal = prior.get("SpinalNociceptiveRelay", {}).get("nociceptive_output", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)

        # Dorsal horn gate: descending pain gate controls transmission
        # gate=1 means open (pain allowed); gate=0 means closed (pain blocked)
        dorsal_gate = gate * self.GATE_GAIN

        # Tactile discrimination: Aβ input × gate × arousal
        tactile = tactile_input * dorsal_gate * (0.60 + arousal * 0.40)
        tactile_discrimination = min(1.0, tactile)

        # Proprioceptive accuracy: maintained even with gate closed
        proprioceptive_accuracy = proprioceptive_input * 0.70
        proprioceptive_accuracy = min(1.0, proprioceptive_accuracy)

        # Pain signal transmission: nociceptive relay
        pain_transmission = pain_signal * (1.0 - gate) * 0.80
        pain_signal_transmission = min(1.0, pain_transmission)

        # Somatosensory integration: combine tactile + proprioceptive + pain
        integration = (tactile_discrimination * 0.35 +
                       proprioceptive_accuracy * 0.35 +
                       (1.0 - pain_signal_transmission) * 0.30)
        somatosensory_integration = min(1.0, integration)

        # --- Persist ---
        self.state["tactile_discrimination"] = round(tactile_discrimination, 4)
        self.state["proprioceptive_accuracy"] = round(proprioceptive_accuracy, 4)
        self.state["dorsal_horn_gate"] = round(dorsal_gate, 4)
        self.state["pain_signal_transmission"] = round(pain_transmission, 4)
        self.state["somatosensory_integration"] = round(somatosensory_integration, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tactile_discrimination": round(tactile_discrimination, 4),
            "proprioceptive_accuracy": round(proprioceptive_accuracy, 4),
            "dorsal_horn_gate": round(dorsal_gate, 4),
            "pain_signal_transmission": round(pain_transmission, 4),
            "somatosensory_integration": round(somatosensory_integration, 4),
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


