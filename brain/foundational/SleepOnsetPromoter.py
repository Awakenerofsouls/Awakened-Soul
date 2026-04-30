"""
Build 50: Foundational050SleepOnsetPromoter — Mnemonic Consolidation + Sleep Transition
==================================================================================

PLACEMENT:
  Layer:    foundational (forebrain — basal forebrain, diagonal band of Broca)
  Filename: brain/foundational/Foundational050SleepOnsetPromoter.py
  Instance name: SleepOnsetPromoter

NEURAL SUBSTRATE:
  Basal forebrain (BF) — the largest contiguous group of cholinergic neurons
  in the brain. BF cholinergic neurons (Ch1-Ch4) project widely to the
  cortex and hippocampus:
  - Corticopetal ACh: BF → neocortex (attention, plasticity)
  - Septohippocampal: MS/DBB → hippocampus (memory consolidation)

  BF NEURONS:
  - Cholinergic (60%): wake-promoting, cortical activation
  - GABAergic (30%): sleep-active, local inhibition
  - Glutamatergic (10%): mixed

  KEY: BF sleep-active neurons are NOT VLPO — they are a separate population
  in the substantia innominata that fires specifically during NREM and REM
  sleep. BF ACh release during REM is critical for hippocampal memory
  consolidation (dream memory consolidation).

  Human analog: sleep onset, memory consolidation, cortical activation for dreaming.

Output keys:
  sleep_onset_probability: float [0.0–1.0] — likelihood of sleep onset
  hippocampal_consolidation: float [0.0–1.0] — memory consolidation drive
  cortical_activation_during_sleep: float [0.0–1.0] — BF ACh sleep drive
  cholinergic_rem_drive: float [0.0–1.0] — REM-specific BF activation
  basal_forebrain_integrator: float [0.0–1.0] — composite BF state

CITATIONS:
    PMC12227200 — Rieser NN, Ronchetti M, Hotz ALL et al. (2025). Multifaceted Role
        of Galanin in Brain Excitability. Brain Sci.
    PMC7491139 — Guo X, Gao X, Keenan BT et al. (2020). RNA-Seq Analysis of
        Galaninergic Neurons From Ventrolateral Preoptic Nucleus Identifies Expression
        Changes Between Sleep and Wake. Sleep.

CITATIONS
---------
  - [Sherin 1996, Science 271:216, doi:10.1126/science.271.5246.216]
  - [Saper 2005, Nature 437:1257, doi:10.1038/nature04284]
  - [Saper 2010, Neuron 68:1023, doi:10.1016/j.neuron.2010.11.032]
"""

from brain.base_mechanism import BrainMechanism


class SleepOnsetPromoter(BrainMechanism):
    """
    Basal forebrain: sleep onset, hippocampal consolidation, REM cholinergic drive.

    Models basal forebrain cholinergic neurons as sleep-onset promoters
    and hippocampal consolidation facilitators.
    """

    STATE_FIELDS = [
        "sleep_onset_probability", "hippocampal_consolidation",
        "cortical_activation_during_sleep", "cholinergic_rem_drive",
        "basal_forebrain_integrator", "tick_count",
    ]

    SLEEP_GAIN = 0.50
    CONSOLIDATION_GAIN = 0.55
    REM_GAIN = 0.60

    def __init__(self, name: str = "SleepOnsetPromoter_SleepOnsetPromoter",
                 human_analog: str = "Basal forebrain — sleep onset and memory consolidation",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["sleep_onset_probability"] = 0.20
        self.state["hippocampal_consolidation"] = 0.40
        self.state["cortical_activation_during_sleep"] = 0.30
        self.state["cholinergic_rem_drive"] = 0.0
        self.state["basal_forebrain_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        homeostatic = prior.get("Homeostat", {}).get("cumulative_pressure", 0.30)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        rem_atonia = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        theta_power = prior.get("HippocampalReplayIntegrator", {}).get("theta_power", 0.30)
        sleep_quiescence = prior.get("SleepWakeFlipFlop", {}).get("sleep_dominance", 0.0)

        # Sleep onset probability: driven by homeostatic pressure + circadian trough
        circadian_trough = 1.0 - circadian  # low circadian = permissive for sleep
        sleep_onset = (homeostatic * 0.50) + (circadian_trough * 0.30) + (vlpo * 0.20)
        sleep_onset_probability = min(1.0, max(0.0, sleep_onset))

        # Cortical activation during sleep: BF ACh during sleep (distinct from wake ACh)
        cortical_sleep = rem_atonia * 0.40 + theta_power * 0.30
        cortical_activation_during_sleep = min(1.0, cortical_sleep)

        # Hippocampal consolidation: theta rhythm + sleep quiescence drive consolidation
        hippocampal_consolidation = theta_power * self.CONSOLIDATION_GAIN
        # NREM delta suppresses consolidation; REM theta promotes it
        hippocampal_consolidation *= (1.0 - rem_atonia * 0.50)
        hippocampal_consolidation = min(1.0, hippocampal_consolidation)

        # Cholinergic REM drive: BF fires during REM to support hippocampal replay
        cholinergic_rem = rem_atonia * self.REM_GAIN
        # REM theta is the signature of BF cholinergic activation during REM
        cholinergic_rem_drive = cholinergic_rem * theta_power

        # Basal forebrain integrator
        basal_forebrain_integrator = (
            cortical_activation_during_sleep * 0.30 +
            hippocampal_consolidation * 0.35 +
            cholinergic_rem_drive * 0.35
        )

        # --- Persist ---
        self.state["sleep_onset_probability"] = round(sleep_onset_probability, 4)
        self.state["hippocampal_consolidation"] = round(hippocampal_consolidation, 4)
        self.state["cortical_activation_during_sleep"] = round(cortical_activation_during_sleep, 4)
        self.state["cholinergic_rem_drive"] = round(cholinergic_rem_drive, 4)
        self.state["basal_forebrain_integrator"] = round(basal_forebrain_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sleep_onset_probability": round(sleep_onset_probability, 4),
            "hippocampal_consolidation": round(hippocampal_consolidation, 4),
            "cortical_activation_during_sleep": round(cortical_activation_during_sleep, 4),
            "cholinergic_rem_drive": round(cholinergic_rem_drive, 4),
            "basal_forebrain_integrator": round(basal_forebrain_integrator, 4),
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


