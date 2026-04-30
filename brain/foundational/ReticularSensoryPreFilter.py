"""
Build 34: Foundational034ReticularSensoryPreFilter — Reticular Formation Sensory Gate
================================================================================

PLACEMENT:
  Layer:    foundational (brainstem reticular formation)
  Filename: brain/foundational/Foundational034ReticularSensoryPreFilter.py
  Instance name: ReticularSensoryPreFilter

NEURAL SUBSTRATE:
  Reticular formation (RF) in the brainstem core — a diffuse network of
  neurons spanning the medulla, pons, and midbrain. The RF is the
  substrate of the ascending reticular activating system (ARAS), which
  modulates sensory transmission through the thalamus and cortex.

  KEY FUNCTIONS:
  - Sensory gating: RF neurons in the intralaminar nuclei of thalamus
    control sensory relay fidelity (facilitate novel stimuli, suppress
    familiar unattended signals)
  - Thalamic relay modulation: cholinergic RF input to thalamus shifts
    firing mode from burst (sleep) to tonic (wake)
  - Sensory modulation of pain: RF mediates diffuse noxious inhibitory
    controls (DNIC) — one pain suppresses another

  Human analog: sensory filtering, attention, pain modulation.

Output keys:
  sensory_gate_output: float [0.0–1.0] — net sensory transmission level
  thalamic_relay_fidelity: float [0.0–1.0] — thalamic sensory relay quality
  novel_stimulus_flag: float [0.0–1.0] — novelty detection signal
  pain_inhibition_input: float [0.0–1.0] — DNIC analgesic input
  reticular_alert_level: float [0.0–1.0] — overall RF arousal state

CITATIONS:
    PMC2855189 — Zikopoulos B, Barbas H (2007). Circuits for Multisensory Integration
        and Attentional Modulation Through the Prefrontal Cortex and the Thalamic
        Reticular Nucleus. Rev Neurosci.
    PMC3119596 — Fuller PM, Sherman D, Pedersen NP et al. (2011). Reassessment of
        the Structural Basis of the Ascending Arousal System. J Neurosci.

CITATIONS
---------
  - [Magoun 1946, Physiol Rev 26:60]
  - [Steriade 1996, Trends Neurosci 19:265]
  - [Munk 1996, Science 272:271]
"""

from brain.base_mechanism import BrainMechanism


class ReticularSensoryPreFilter(BrainMechanism):
    """
    Reticular formation: sensory gate, thalamic relay, novelty detection.

    Controls sensory throughput and thalamic relay fidelity based on
    arousal state and novelty signals.
    """

    STATE_FIELDS = [
        "sensory_gate_output", "thalamic_relay_fidelity", "novel_stimulus_flag",
        "pain_inhibition_input", "reticular_alert_level", "tick_count",
    ]

    GATE_GAIN = 0.60
    THALAMIC_GAIN = 0.55
    NOVELTY_GAIN = 0.50
    DNIC_GAIN = 0.45

    def __init__(self, name: str = "ReticularSensoryPreFilter_ReticularSensoryPreFilter",
                 human_analog: str = "Reticular formation — sensory gating and ARAS",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["sensory_gate_output"] = 0.50
        self.state["thalamic_relay_fidelity"] = 0.50
        self.state["novel_stimulus_flag"] = 0.0
        self.state["pain_inhibition_input"] = 0.0
        self.state["reticular_alert_level"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        visual_novelty = prior.get("VisualSalienceMap", {}).get("salience_level", 0.0)
        auditory_novelty = prior.get("AuditoryOrienting", {}).get("azimuth_salience", 0.0)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Reticular alert level: rises with arousal, falls during sleep
        alert = (arousal * 0.60) - (sleep_signal * 0.30)

        # Thalamic relay fidelity: high during wake, low during sleep (burst mode)
        # Arousal drives tonic firing (high fidelity); sleep drives burst (low fidelity)
        thalamic_fidelity = alert
        # Inverted pain gate: pain suppresses sensory gating (hypervigilance)
        pain_modulation = (1.0 - pain) * 0.20
        thalamic_fidelity = max(0.0, min(1.0, thalamic_fidelity + pain_modulation))

        # Sensory gate output: what % of sensory input is transmitted
        sensory_gate = alert * self.GATE_GAIN
        sensory_gate = min(1.0, sensory_gate)

        # Novel stimulus flag: any salient novel input triggers flag
        novelty = max(visual_novelty, auditory_novelty)
        novel_stimulus = novelty * self.NOVELTY_GAIN
        # Novelty overrides sleep suppression
        if novel_stimulus > 0.40:
            sensory_gate = max(sensory_gate, novel_stimulus)

        # Pain inhibition (DNIC): one pain inhibits others
        pain_inhibition = (1.0 - pain) * self.DNIC_GAIN

        # --- Persist ---
        self.state["sensory_gate_output"] = round(sensory_gate, 4)
        self.state["thalamic_relay_fidelity"] = round(thalamic_fidelity, 4)
        self.state["novel_stimulus_flag"] = round(novel_stimulus, 4)
        self.state["pain_inhibition_input"] = round(pain_inhibition, 4)
        self.state["reticular_alert_level"] = round(alert, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sensory_gate_output": round(sensory_gate, 4),
            "thalamic_relay_fidelity": round(thalamic_fidelity, 4),
            "novel_stimulus_flag": round(novel_stimulus, 4),
            "pain_inhibition_input": round(pain_inhibition, 4),
            "reticular_alert_level": round(alert, 4),
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


