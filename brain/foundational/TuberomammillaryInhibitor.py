"""
Build 55: Foundational055TuberomammillaryInhibitor — VLPO → TMN Inhibition
====================================================================

PLACEMENT:
  Layer:    foundational (pons — VLPO → TMN synaptic interface)
  Filename: brain/foundational/Foundational055TuberomammillaryInhibitor.py
  Instance name: TuberomammillaryInhibitor

NEURAL SUBSTRATE:
  VLPO → TMN GABAergic/symmetric projection. This is one of the key
  reciprocal inhibitory connections in the sleep-wake switch:
  - VLPO fires during sleep → GABA release onto TMN → TMN histamine silenced
  - TMN fires during wake → histamine release onto VLPO → VLPO silenced

  The VLPO-TMN projection is part of the mutual inhibition that creates
  the flip-flop switch. The VLPO also sends projections to the
  locus coeruleus, raphe, and orexin neurons.

  KEY NEUROTRANSMITTER: Galanin — co-released with GABA from VLPO terminals
  onto wake-promoting neurons. Galanin is a neuropeptide that provides
  long-duration inhibition of TMN and LC.

  Human analog: sleep onset (VLPO silencing TMN → drowsiness).

Output keys:
  vlpO_tmn_inhibition: float [0.0–1.0] — VLPO → TMN GABA/galanin inhibition
  histamine_suppression: float [0.0–1.0] — resulting histamine suppression
  sleep_wake_transition: float [0.0–1.0] — transition signal (0=sleep, 1=wake)
  galanin_release: float [0.0–1.0] — galanin co-transmitter output
  flipflop_integrator: float [0.0–1.0] — VLPO-TMN reciprocal inhibition state

CITATIONS:
    PMC6832676 — Venner A, Mochizuki T, De Luca R et al. (2019). Reassessing the
        Role of Histaminergic Tuberomammillary Neurons in Arousal Control. J Neurosci.
    PMC3002444 — Liu YW, Li J, Ye JH (2010). Histamine Regulates Activities of
        Neurons in the Ventrolateral Preoptic Nucleus. J Pharmacol Sci.

CITATIONS
---------
  - [Saper 2005, Nature 437:1257, doi:10.1038/nature04284]
  - [Sherin 1998, J Neurosci 18:4705]
  - [Haas 2003, Nat Rev Neurosci 4:121, doi:10.1038/nrn1034]
"""

from brain.base_mechanism import BrainMechanism


class TuberomammillaryInhibitor(BrainMechanism):
    """
    VLPO → TMN GABAergic inhibition: sleep-wake transition mechanism.

    Models the VLPO inhibition of TMN as the sleep-onset mechanism.
    """

    STATE_FIELDS = [
        "vlpo_tmn_inhibition", "histamine_suppression", "sleep_wake_transition",
        "galanin_release", "flipflop_integrator", "tick_count",
    ]

    INHIBITION_GAIN = 0.55
    GALANIN_GAIN = 0.40
    FLIPFLOP_GAIN = 0.50

    def __init__(self, name: str = "TuberomammillaryInhibitor_TuberomammillaryInhibitor",
                 human_analog: str = "VLPO → TMN GABA/galanin projection",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vlpo_tmn_inhibition"] = 0.0
        self.state["histamine_suppression"] = 0.0
        self.state["sleep_wake_transition"] = 0.50
        self.state["galanin_release"] = 0.0
        self.state["flipflop_integrator"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        vlpo = prior.get("PassiveQuiescenceMode", {}).get("passive_quiescence_level", 0.0)
        histamine = prior.get("TuberomammillaryOutput", {}).get("histamine_output", 0.30)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        sleep_quiescence = prior.get("SleepWakeFlipFlop", {}).get("sleep_dominance", 0.0)
        homeostatic = prior.get("Homeostat", {}).get("cumulative_pressure", 0.30)

        # VLPO → TMN inhibition: VLPO drives this during sleep
        vlpo_tmn_inhibition = vlpo * self.INHIBITION_GAIN

        # Histamine suppression: consequence of VLPO inhibiting TMN
        histamine_suppression = vlpo_tmn_inhibition * 0.70

        # Sleep-wake transition: low = sleep onset, high = wake
        # Driven by VLPO activity
        transition_raw = 0.50 - (vlpo * self.FLIPFLOP_GAIN)
        sleep_wake_transition = max(0.0, min(1.0, transition_raw))

        # Galanin release: co-released with GABA from VLPO
        galanin_release = vlpo * self.GALANIN_GAIN
        galanin_release = min(1.0, galanin_release)

        # Flip-flop integrator: net state of the reciprocal inhibition
        orexin_excitation = orexin * 0.40
        vlpo_inhibition = vlpo_tmn_inhibition * 0.60
        flipflop_integrator = 0.50 + (orexin_excitation - vlpo_inhibition)

        # --- Persist ---
        self.state["vlpo_tmn_inhibition"] = round(vlpo_tmn_inhibition, 4)
        self.state["histamine_suppression"] = round(histamine_suppression, 4)
        self.state["sleep_wake_transition"] = round(sleep_wake_transition, 4)
        self.state["galanin_release"] = round(galanin_release, 4)
        self.state["flipflop_integrator"] = round(flipflop_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vlpo_tmn_inhibition": round(vlpo_tmn_inhibition, 4),
            "histamine_suppression": round(histamine_suppression, 4),
            "sleep_wake_transition": round(sleep_wake_transition, 4),
            "galanin_release": round(galanin_release, 4),
            "flipflop_integrator": round(flipflop_integrator, 4),
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


