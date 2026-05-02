"""
Build 54: Foundational054TuberomammillaryOutput — Histaminergic Arousal System
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — tuberomammillary nucleus, TMN)
  Filename: brain/foundational/Foundational054TuberomammillaryOutput.py
  Instance name: TuberomammillaryOutput

NEURAL SUBSTRATE:
  Tuberomammillary nucleus (TMN) in the posterior hypothalamus — the
  sole source of histamine in the brain. TMN neurons are wake-active,
  receive input from orexin neurons (which excite them), and project
  widely to cortex, basal forebrain, and other arousal centers.

  HISTAMINE EFFECTS:
  - Cortex: promotes wakefulness, attention, cortical activation
  - Basal forebrain: excites BF cholinergic neurons → cortical ACh
  - Arousal centers: synergistic with LC (NE) and raphe (5-HT)
  - Suppresses VLPO/SubC: histamine inhibits sleep-promoting neurons

  TMN is suppressed during sleep (especially NREM); VLPO GABA inhibits TMN.
  Antihistamines (H1 antagonists) cause drowsiness. H3 autoreceptors
  regulate TMN firing (H3 agonism = autoinhibition).

  Human analog: antihistamine drowsiness, histamine-driven wakefulness.

Output keys:
  histamine_output: float [0.0–1.0] — TMN histamine release
  cortical_activator: float [0.0–1.0] — cortical arousal via histamine
  tmn_wake_drive: float [0.0–1.0] — TMN wake-promoting output
  histamine_gate_modulation: float [0.0–1.0] — H3 autoreceptor modulation
  sleep_suppression_by_histamine: float [0.0–1.0] — VLPO/SubC suppression

CITATIONS:
    PMC5172538 — Hoffman GE, Koban M (2016). Hypothalamic L-Histidine Decarboxylase
        Is Up-Regulated During Chronic REM Sleep Deprivation of Rats. Sleep.
    PMC6674640 — Takahashi K, Lin JS, Sakai K (2006). Neuronal Activity of
        Histaminergic Tuberomammillary Neurons During Wake-Sleep States in the Mouse.
        J Neurosci.

CITATIONS
---------
  - [Haas 2003, Nat Rev Neurosci 4:121, doi:10.1038/nrn1034]
  - [Takahashi 2006, J Neurosci 26:10292, doi:10.1523/JNEUROSCI.2341-06.2006]
  - [Yoshikawa 2021, Br J Pharmacol 178:750, doi:10.1111/bph.15220]
"""

from brain.base_mechanism import BrainMechanism


class TuberomammillaryOutput(BrainMechanism):
    """
    TMN: histaminergic arousal, cortical activation, sleep suppression.

    Models TMN as the histaminergic wake-promoting system.
    """

    STATE_FIELDS = [
        "histamine_output", "cortical_activator", "tmn_wake_drive",
        "histamine_gate_modulation", "sleep_suppression_by_histamine", "tick_count",
    ]

    HISTAMINE_GAIN = 0.60
    CORTICAL_GAIN = 0.55
    SLEEP_GATE_GAIN = 0.50

    def __init__(self, name: str = "TuberomammillaryOutput_TuberomammillaryOutput",
                 human_analog: str = "TMN — histaminergic wake-promoting system",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["histamine_output"] = 0.40
        self.state["cortical_activator"] = 0.35
        self.state["tmn_wake_drive"] = 0.40
        self.state["histamine_gate_modulation"] = 0.30
        self.state["sleep_suppression_by_histamine"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        h3_agonist = prior.get("H3AutoreceptorSignal", {}).get("h3_activity", 0.20)
        sleep = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Histamine output: driven by orexin, arousal; suppressed by VLPO and H3 agonism
        excitation = orexin * 0.40 + arousal * 0.35
        inhibition = vlpo * 0.35 + h3_agonist * 0.30 + sleep * 0.40
        histamine_raw = max(0.0, excitation - inhibition)
        histamine_output = min(1.0, histamine_raw)

        # TMN wake drive
        tmn_wake_drive = histamine_output * self.HISTAMINE_GAIN

        # Cortical activator: histamine → BF → cortical ACh
        cortical_activator = histamine_output * self.CORTICAL_GAIN

        # Histamine gate modulation: H3 autoreceptor controls release
        histamine_gate_modulation = 1.0 - h3_agonist * 0.80

        # Sleep suppression by histamine: histamine inhibits VLPO
        sleep_suppression = histamine_output * self.SLEEP_GATE_GAIN * 0.30

        # --- Persist ---
        self.state["histamine_output"] = round(histamine_output, 4)
        self.state["cortical_activator"] = round(cortical_activator, 4)
        self.state["tmn_wake_drive"] = round(tmn_wake_drive, 4)
        self.state["histamine_gate_modulation"] = round(histamine_gate_modulation, 4)
        self.state["sleep_suppression_by_histamine"] = round(sleep_suppression, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "histamine_output": round(histamine_output, 4),
            "cortical_activator": round(cortical_activator, 4),
            "tmn_wake_drive": round(tmn_wake_drive, 4),
            "histamine_gate_modulation": round(histamine_gate_modulation, 4),
            "sleep_suppression_by_histamine": round(sleep_suppression, 4),
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


