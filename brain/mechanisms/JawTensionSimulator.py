"""
Build 24: Foundational024JawTensionSimulator — Trigeminal Motor Nucleus
=====================================================================

PLACEMENT:
  Layer:    foundational (brainstem — trigeminal motor nucleus, mesencephalic nucleus)
  Filename: brain/foundational/Foundational024JawTensionSimulator.py
  Instance name: JawTensionSimulator

NEURAL SUBSTRATE:
  Trigeminal motor nucleus (Vmot) in pons — controls muscles of mastication
  (masseter, temporalis, pterygoids). Receives input from:
  - Sensorimotor cortex (voluntary chewing)
  - Mesencephalic nucleus (Vmes) — proprioceptive feedback from jaw stretch receptors
  - Supratrigeminal nucleus (suppression of masseteric reflex)
  - Reticular formation (aversive reflex circuits)

  KEY CIRCUITS:
  - Jaw-jerk reflex: Ia afferents from periodontal receptors → Vmot → masseter
  - masticatory central pattern generator in reticular formation
  - Tooth-pain modulation: periaqueductal gray → raphe → Vmot (descending inhibition)

  Human analog: chewing, tooth clenching (bruxism), jaw reflex, mastication.

Output keys:
  masseter_tone: float [0.0–1.0] — masseter muscle activation
  molar_bite_force: float [0.0–1.0] — bite force output
  jaw_reflex_suppression: float [0.0–1.0] — suppression of jaw-jerk reflex
  oral_motor_coordination: float [0.0–1.0] — CPG coordination of mastication
  tension_bruxism_index: float [0.0–1.0] — stress-related jaw clenching

CITATIONS:
    PMC1191101 — Dessem D, Iyadurai OD, Taylor A (1988). The Role of Periodontal
        Receptors in the Jaw-Opening Reflex in the Cat. J Physiol.
    PMC1331163 — Cody FW, Lee RW, Taylor A (1972). A Functional Analysis of the
        Components of the Mesencephalic Nucleus of the Fifth Nerve in the Cat.
        J Physiol.

CITATIONS
---------
  - [Sessle 2000, Crit Rev Oral Biol Med 11:57]
  - [Lund 1991, Crit Rev Oral Biol Med 2:33]
  - [Lazarov 2002, Prog Neurobiol 66:19]
"""

from brain.base_mechanism import BrainMechanism


class JawTensionSimulator(BrainMechanism):
    """
    Trigeminal motor nucleus: mastication, bite force, jaw tension.

    Controls masseter tone, molar bite force, and jaw-jerk reflex
    suppression. Elevated during stress (bruxism).
    """

    STATE_FIELDS = [
        "masseter_tone", "molar_bite_force", "jaw_reflex_suppression",
        "oral_motor_coordination", "tension_bruxism_index", "tick_count",
    ]

    MASSETER_GAIN = 0.55
    BITE_FORCE_GAIN = 0.60
    REFLEX_GAIN = 0.40
    CPG_GAIN = 0.50
    STRESS_BRUXISM_GAIN = 0.65

    def __init__(self, name: str = "JawTensionSimulator_JawTensionSimulator",
                 human_analog: str = "Trigeminal motor nucleus — jaw tension and mastication",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["masseter_tone"] = 0.10
        self.state["molar_bite_force"] = 0.05
        self.state["jaw_reflex_suppression"] = 0.30
        self.state["oral_motor_coordination"] = 0.40
        self.state["tension_bruxism_index"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        sensorimotor = prior.get("SensorimotorCortex", {}).get("motor_command_strength", 0.0)

        # Masseter tone: elevated by stress/arousal, reduced by pain modulation
        stress_tone = stress * self.STRESS_BRUXISM_GAIN
        arousal_tone = arousal * 0.15
        pain_inhibition = (1.0 - pain) * 0.10
        new_masseter = max(0.0, min(1.0, stress_tone + arousal_tone - pain_inhibition))

        # Bite force: proportional to masseter tone; sensorimotor command adds
        bite_force = (new_masseter * self.BITE_FORCE_GAIN) + (sensorimotor * 0.20)
        bite_force = max(0.0, min(1.0, bite_force))

        # Jaw reflex suppression: PAG/raphe descending inhibition (pain gate)
        reflex_suppression = (1.0 - pain) * self.REFLEX_GAIN

        # Oral motor coordination: CPG in reticular formation
        coordination = (new_masseter * 0.30) + (sensorimotor * 0.30) + 0.40
        coordination = max(0.0, min(1.0, coordination))

        # Bruxism index: stress drives jaw clenching during sleep/wake
        bruxism = stress * self.STRESS_BRUXISM_GAIN

        # --- Persist ---
        self.state["masseter_tone"] = round(new_masseter, 4)
        self.state["molar_bite_force"] = round(bite_force, 4)
        self.state["jaw_reflex_suppression"] = round(reflex_suppression, 4)
        self.state["oral_motor_coordination"] = round(coordination, 4)
        self.state["tension_bruxism_index"] = round(bruxism, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "masseter_tone": round(new_masseter, 4),
            "molar_bite_force": round(bite_force, 4),
            "jaw_reflex_suppression": round(reflex_suppression, 4),
            "oral_motor_coordination": round(coordination, 4),
            "tension_bruxism_index": round(bruxism, 4),
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


