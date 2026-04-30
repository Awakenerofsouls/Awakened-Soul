"""
Build 46: Foundational046VocalAutonomicLink — Periaqueductal Gray Vocalization Control
================================================================================

PLACEMENT:
  Layer:    foundational (midbrain — periaqueductal gray, PAG)
  Filename: brain/foundational/Foundational046VocalAutonomicLink.py
  Instance name: VocalAutonomicLink

NEURAL SUBSTRATE:
  Periaqueductal gray (PAG) in midbrain — the emotional motor control
  center. The PAG coordinates vocalization, autonomic responses, and
  defensive behaviors. Contains columnar organization:
  - Lateral/ventrolateral PAG: defensive responses (flight, fight, freeze)
  - Dorsomedial PAG: active coping (vocalization, aggression)
  - The PAG receives input from amygdala, hypothalamus, and cortex,
    and projects to the parabrachial nucleus, nucleus ambiguus, and
    reticular formation.

  VOCALIZATION CIRCUIT:
  PAG (laryngeal CPG) → nucleus ambiguus → laryngeal motor neurons
  (in nucleus ambiguus) → vagus nerve (CN X) → laryngeal muscles

  The PAG coordinates laryngeal tension (vocal pitch), respiratory
  patterning (phonation timing), and autonomic accompaniment (heart
  rate changes during vocalization).

  Human analog: crying, laughing, screaming, vocal autonomic responses.

Output keys:
  laryngeal_tension: float [0.0–1.0] — vocal fold tension
  vocal_autonomic_accompany: float [0.0–1.0] — autonomic accompaniment
  emotional_vocal_drive: float [0.0–1.0] — amygdala-PAG emotional drive
  respiratory_vocal_pattern: float [0.0–1.0] — respiratory patterning for vocalization
  vocal_defensive_response: float [0.0–1.0] — defensive vocal (alarm calls)

CITATIONS:
    PMC2376830 — Ambalavanar R, Tanaka Y, Selbie WS et al. (2004). Neuronal
        Activation in the Medulla Oblongata During Selective Elicitation of the
        Laryngeal Adductor Response. J Appl Physiol.
    PMC3162241 — Pascual-Font A, Hernández-Morato I, McHanwell S et al. (2011).
        The Central Projections of the Laryngeal Nerves in the Rat. J Anat.

CITATIONS
---------
  - [Holstege 2014, Curr Opin Neurobiol 24:139]
  - [Jurgens 2009, Neurosci Biobehav Rev 33:1273]
  - [Newman 1999, Ann N Y Acad Sci 877:242]
"""

from brain.base_mechanism import BrainMechanism


class VocalAutonomicLink(BrainMechanism):
    """
    PAG: vocalization, emotional motor control, laryngeal autonomic.

    Coordinates vocal output with autonomic state, driven by limbic input.
    """

    STATE_FIELDS = [
        "laryngeal_tension", "vocal_autonomic_accompany", "emotional_vocal_drive",
        "respiratory_vocal_pattern", "vocal_defensive_response", "tick_count",
    ]

    LARYNGEAL_GAIN = 0.55
    AUTONOMIC_GAIN = 0.50
    EMOTIONAL_GAIN = 0.60
    DEFENSIVE_GAIN = 0.55

    def __init__(self, name: str = "VocalAutonomicLink_VocalAutonomicLink",
                 human_analog: str = "PAG — periaqueductal gray vocalization control",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["laryngeal_tension"] = 0.10
        self.state["vocal_autonomic_accompany"] = 0.20
        self.state["emotional_vocal_drive"] = 0.10
        self.state["respiratory_vocal_pattern"] = 0.0
        self.state["vocal_defensive_response"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        vocal_motor = prior.get("VocalMotorCortex", {}).get("vocal_command", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vagal_tone = prior.get("VagalRestPromoter", {}).get("cardiac_vagal_tone", 0.40)

        # Emotional vocal drive: amygdala input to PAG → crying/laughing
        emotional_drive = amygdala * self.EMOTIONAL_GAIN
        emotional_drive += stress * 0.30

        # Laryngeal tension: rises with emotional arousal; suppressed by vagal tone
        laryngeal = emotional_drive * self.LARYNGEAL_GAIN
        laryngeal += vocal_motor * 0.30
        vagal_suppression = (1.0 - vagal_tone) * 0.15
        laryngeal = max(0.0, min(1.0, laryngeal + vagal_suppression))

        # Vocal autonomic accompaniment: heart rate, blood pressure changes with vocalization
        autonomic_accompany = emotional_drive * self.AUTONOMIC_GAIN
        autonomic_accompany += stress * 0.25
        autonomic_accompany = min(1.0, autonomic_accompany)

        # Respiratory vocal pattern: vocalization requires respiratory coordination
        respiratory_pattern = (laryngeal * 0.40) + (emotional_drive * 0.30)
        respiratory_pattern = min(1.0, max(0.0, respiratory_pattern))

        # Defensive vocal: alarm call / scream driven by fear + stress
        fear_vocal = amygdala * self.DEFENSIVE_GAIN + stress * 0.30
        # Sympathetic arousal elevates laryngeal tension for alarm
        fear_vocal += (1.0 - vagal_tone) * 0.20
        vocal_defensive = min(1.0, fear_vocal)

        # --- Persist ---
        self.state["laryngeal_tension"] = round(laryngeal, 4)
        self.state["vocal_autonomic_accompany"] = round(autonomic_accompany, 4)
        self.state["emotional_vocal_drive"] = round(emotional_drive, 4)
        self.state["respiratory_vocal_pattern"] = round(respiratory_pattern, 4)
        self.state["vocal_defensive_response"] = round(vocal_defensive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "laryngeal_tension": round(laryngeal, 4),
            "vocal_autonomic_accompany": round(autonomic_accompany, 4),
            "emotional_vocal_drive": round(emotional_drive, 4),
            "respiratory_vocal_pattern": round(respiratory_pattern, 4),
            "vocal_defensive_response": round(vocal_defensive, 4),
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


