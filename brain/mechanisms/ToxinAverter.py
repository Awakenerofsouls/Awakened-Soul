"""
Build 45: Foundational045ToxinAverter — Area Postrema Chemoreceptor Trigger Zone
==========================================================================

PLACEMENT:
  Layer:    foundational (brainstem — area postrema, area postrema NTS)
  Filename: brain/foundational/Foundational045ToxinAverter.py
  Instance name: ToxinAverter

NEURAL SUBSTRATE:
  Area postrema (AP) — the chemoreceptor trigger zone (CTZ), located
  in the floor of the fourth ventricle, lacking a blood-brain barrier.
  The AP detects emetic (vomiting-inducing) substances in the blood:
  - Toxins: bacterial toxins (Staphylococcus aureus enterotoxin)
  - Chemotherapy agents: cisplatin, doxorubicin (activate 5-HT3 on AP neurons)
  - Motion sickness signals: vestibular input to AP → nausea
  - Cytokines: IL-1β, IL-6, TNF-α → sickness nausea via AP

  AP PROJECTS TO:
  - NTS (solitary tract): integration of emetic signals
  - Dorsal motor nucleus of vagus: vomiting motor program
  - Parabrachial nucleus: nausea/aversion learning

  EMETIC PATHWAY:
  AP/NTS → central pattern generator for vomiting → respiratory muscles,
  diaphragm, abdominal muscles → retrograde GI motility + antiperistalsis

  Human analog: nausea, emesis, toxin avoidance, motion sickness.

Output keys:
  nausea_intensity: float [0.0–1.0] — nausea level
  emetic_trigger: float [0.0–1.0] — vomiting trigger (thresholded)
  toxin_detection: float [0.0–1.0] — AP toxin signal
  motion_sickness_contribution: float [0.0–1.0] — vestibular nausea input
  defensive_gag_reflex: float [0.0–1.0] — anticipatory defensive response

CITATIONS:
    PMC1028578 — Baker PC, Bernat JL (1985). The Neuroanatomy of Vomiting in Man:
        Association of Projectile Vomiting With a Solitary Metastasis in the Lateral
        Tegmentum of the Pons. Mayo Clin Proc.
    PMC7364392 — Cohen DT, Craven C, Bragin I (2020). Ischemic Stroke Induced Area
        Postrema Syndrome With Intractable Nausea, Vomiting, and Hiccups.
        Neurologist.

CITATIONS
---------
  - [Borison 1989, Pharmacol Ther 42:147]
  - [Andrews 2005, Auton Neurosci 125:100]
  - [Hornby 2001, Am J Med 111:106S]
"""

from brain.base_mechanism import BrainMechanism


class ToxinAverter(BrainMechanism):
    """
    Area postrema: chemoreceptor trigger zone for nausea and emesis.

    Detects blood-borne toxins, chemotherapy agents, cytokines, and
    vestibular signals to generate nausea and trigger protective vomiting.
    """

    STATE_FIELDS = [
        "nausea_intensity", "emetic_trigger", "toxin_detection",
        "motion_sickness_contribution", "defensive_gag_reflex", "tick_count",
    ]

    NAUSEA_GAIN = 0.60
    EMETIC_THRESHOLD = 0.80
    TOXIN_GAIN = 0.55
    VESTIBULAR_GAIN = 0.40
    GAG_GAIN = 0.45

    def __init__(self, name: str = "ToxinAverter_ToxinAverter",
                 human_analog: str = "Area postrema — chemoreceptor trigger zone",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["nausea_intensity"] = 0.0
        self.state["emetic_trigger"] = 0.0
        self.state["toxin_detection"] = 0.0
        self.state["motion_sickness_contribution"] = 0.0
        self.state["defensive_gag_reflex"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cytokines = prior.get("ImmuneSignalRelay", {}).get("immune_activation", 0.0)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        gut_signal = prior.get("GutSignalRelay", {}).get("gastrointestinal_activity", 0.30)
        serotonin = prior.get("DorsalRapheSerotonin", {}).get("serotonin_level", 0.30)
        emetic_drug = prior.get("EmeticChemotherapySignal", {}).get("emetic_level", 0.0)

        # Toxin detection: cytokines + emetic drugs directly activate AP
        toxin_detection = (cytokines * self.TOXIN_GAIN) + (emetic_drug * 0.80)
        toxin_detection = min(1.0, toxin_detection)

        # Motion sickness: vestibular input to AP via NTS
        vestibular_nausea = abs(vestibular - 0.5) * self.VESTIBULAR_GAIN
        motion_sickness_contribution = vestibular_nausea

        # Nausea: sum of all emetic contributors
        nausea_raw = (
            toxin_detection * self.NAUSEA_GAIN +
            vestibular_nausea * self.NAUSEA_GAIN * 0.50 +
            gut_signal * 0.20
        )
        nausea_intensity = min(1.0, max(0.0, nausea_raw))

        # Emetic trigger: fires when nausea exceeds threshold
        if nausea_intensity > self.EMETIC_THRESHOLD:
            emetic_trigger = (nausea_intensity - self.EMETIC_THRESHOLD) / (1.0 - self.EMETIC_THRESHOLD)
        else:
            emetic_trigger = 0.0
        emetic_trigger = min(1.0, emetic_trigger)

        # Defensive gag reflex: anticipatory response before full emesis
        if nausea_intensity > 0.40 and emetic_trigger < 0.30:
            gag_reflex = nausea_intensity * self.GAG_GAIN
        else:
            gag_reflex = 0.0

        # --- Persist ---
        self.state["nausea_intensity"] = round(nausea_intensity, 4)
        self.state["emetic_trigger"] = round(emetic_trigger, 4)
        self.state["toxin_detection"] = round(toxin_detection, 4)
        self.state["motion_sickness_contribution"] = round(motion_sickness_contribution, 4)
        self.state["defensive_gag_reflex"] = round(gag_reflex, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "nausea_intensity": round(nausea_intensity, 4),
            "emetic_trigger": round(emetic_trigger, 4),
            "toxin_detection": round(toxin_detection, 4),
            "motion_sickness_contribution": round(motion_sickness_contribution, 4),
            "defensive_gag_reflex": round(gag_reflex, 4),
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


