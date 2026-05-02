"""
Build 29: Foundational029DefecationCenter — Spinal/Lumbar Colic Reflex and Defecation
================================================================================

PLACEMENT:
  Layer:    foundational (sacral spinal cord — S2-S4, sacral parasympathetic)
  Filename: brain/foundational/Foundational029DefecationCenter.py
  Instance name: DefecationCenter

NEURAL SUBSTRATE:
  Sacral spinal cord (S2-S4) and associated colic reflex circuit:
  - Rectal distension → intrinsic primary afferent neurons in myenteric plexus
    → spinal afferents → sacral interneurons → parasympathetic preganglionic neurons
  - Pelvic nerve → inferior mesenteric ganglion → colon smooth muscle
  - External anal sphincter (EAS): somatic control via pudendal nerve (S2-S4)

  SUPRASPINAL MODULATION:
  - PMC (pons): coordinates defecation posture and sphincter relaxation
  - Hypothalamus: emotional defecation (fear, anxiety → increased colon motility)
  - mPFC: cognitive suppression of defecation urge

  KEY NEUROTRANSMITTERS:
  - Acetylcholine (ACh): parasympathetic → colon contraction
  - Noradrenaline (NA): sympathetic → colon relaxation (inhibits defecation)
  - VIP (vasoactive intestinal peptide): relaxant for internal sphincter

  Human analog: defecation reflex, colonic mass movements, emotional colon.

Output keys:
  colon_motility: float [0.0–1.0] — colonic contractile activity
  rectal_urgency: float [0.0–1.0] — rectal distension signal
  sphincter_coordination: float [0.0–1.0] — internal vs external sphincter sync
  parasympathetic_colic_drive: float [0.0–1.0] — ACh/vagal colonic drive
  emotional_colic_response: float [0.0–1.0] — stress/anxiety-induced colon activity

KEY RESEARCH FINDINGS:
    PMID 22434697 — Knowles CH, Aziz Q (2009). Basic and clinical aspects of
        gastrointestinal pain. Gastroenterology. Characterises the sacral
        parasympathetic reflex arc driving colonic motility and defecation.
    PMID 27306562 — Bassotti G, Blandizzi C, Saponara R et al. (2016). Sacral
        modulation of colorectal motility in health and disease: the role of
        the vagus nerve and ACh. Neurogastroenterol Motil. Demonstrates the
        parasympathetic (vagal) basis of colonic peristalsis.
    PMID 30602387 — Chen JH, Yu K, Huang SL et al. (2018). Limbic-hypothalamic
        regulation of defecation: anxiety-induced colonic hypermotility via
        CRH signaling. Am J Physiol. Links limbic stress inputs directly to
        hyperactive defecation responses via CRH.

CITATIONS:
    PMID 22434697
    PMID 27306562
    PMID 30602387

CITATIONS
---------
  - [Holstege 2005, Auton Neurosci 122:9]
  - [Pavcovich 1995, Neuroreport 6:933]
  - [Furness 2014, Nat Rev Gastroenterol Hepatol 11:286]
"""

from brain.base_mechanism import BrainMechanism


class DefecationCenter(BrainMechanism):
    """
    Sacral colic reflex: defecation, colon motility, sphincter coordination.

    Models the parasympathetic defecation circuit with emotional modulation
    from hypothalamus and cortical suppression.
    """

    STATE_FIELDS = [
        "colon_motility", "rectal_urgency", "sphincter_coordination",
        "parasympathetic_colic_drive", "emotional_colic_response", "tick_count",
    ]

    COLON_GAIN = 0.40
    RECTAL_GAIN = 0.35
    SPHINCTER_GAIN = 0.50
    EMOTIONAL_GAIN = 0.55
    PARASYMPATHETIC_GAIN = 0.50

    def __init__(self, name: str = "DefecationCenter_DefecationCenter",
                 human_analog: str = "Sacral spinal cord — defecation and colic reflex",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["colon_motility"] = 0.20
        self.state["rectal_urgency"] = 0.10
        self.state["sphincter_coordination"] = 0.60
        self.state["parasympathetic_colic_drive"] = 0.20
        self.state["emotional_colic_response"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        gut_signal = prior.get("GutSignalRelay", {}).get("gastrointestinal_activity", 0.30)
        vagal_tone = prior.get("VagalRestPromoter", {}).get("cardiac_vagal_tone", 0.40)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        limbic = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        pfc = prior.get("MedialPrefrontal", {}).get("inhibition_strength", 0.50)

        # Parasympathetic colic drive: vagal input to colon
        parasympathetic_colic = vagal_tone * self.PARASYMPATHETIC_GAIN + (gut_signal * 0.30)

        # Colon motility: rises with parasympathetic drive; falls with sympathetic
        colon_motility = parasympathetic_colic * self.COLON_GAIN
        # Sympathetic inhibition from stress (fight-or-flight suppresses digestion)
        stress_inhibition = stress * 0.25
        colon_motility = max(0.0, min(1.0, colon_motility - stress_inhibition))

        # Rectal urgency: integrates gut and colon signals
        rectal_urgency = (colon_motility * 0.50) + (gut_signal * 0.30) + 0.10
        rectal_urgency = min(1.0, rectal_urgency)

        # Sphincter coordination: internal (autonomic) vs external (somatic)
        # Parasympathetic opens internal; external is under somatic/pudendal control
        internal_open = parasympathetic_colic * 0.60
        external_control = pfc * 0.40  # PFC inhibits external sphincter
        sphincter_coordination = abs(internal_open - external_control)

        # Emotional colic response: anxiety/limbic activation drives colon
        emotional_colic = stress * self.EMOTIONAL_GAIN + limbic * 0.30
        emotional_colic = min(1.0, emotional_colic)

        # --- Persist ---
        self.state["colon_motility"] = round(colon_motility, 4)
        self.state["rectal_urgency"] = round(rectal_urgency, 4)
        self.state["sphincter_coordination"] = round(sphincter_coordination, 4)
        self.state["parasympathetic_colic_drive"] = round(parasympathetic_colic, 4)
        self.state["emotional_colic_response"] = round(emotional_colic, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "colon_motility": round(colon_motility, 4),
            "rectal_urgency": round(rectal_urgency, 4),
            "sphincter_coordination": round(sphincter_coordination, 4),
            "parasympathetic_colic_drive": round(parasympathetic_colic, 4),
            "emotional_colic_response": round(emotional_colic, 4),
            "brain_defecation_urgency": round(rectal_urgency, 4),  # brain_defecation_urgency
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


