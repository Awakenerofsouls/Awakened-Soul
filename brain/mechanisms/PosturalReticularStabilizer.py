"""
Build 35: Foundational035PosturalReticularStabilizer — Medial RF Posture/Stability Control
=====================================================================================

PLACEMENT:
  Layer:    foundational (brainstem — medial reticular formation, gigantocellular nucleus)
  Filename: brain/foundational/Foundational035PosturalReticularStabilizer.py
  Instance name: PosturalReticularStabilizer

NEURAL SUBSTRATE:
  Medial reticular formation (gigantocellular nucleus, Gi) in pons/medulla —
  descendingsupports posture, tone, and righting reflexes. The Gi receives:
  - Cortical input (voluntary posture commands from motor cortex)
  - Vestibular input (head position from vestibular nuclei)
  - Cerebellar input (corrective signals via fastigial nucleus)
  - Basal ganglia (via SNr, via thalamus → Gi)

  The Gi projects to spinal cord (ventral horn, medial zone) to control
  axial and proximal limb muscles for posture. The Gi also mediates
  atonia of postural muscles during REM sleep (via SubC input).

  Human analog: posture, balance, righting reflexes.

Output keys:
  postural_tone: float [0.0–1.0] — axial muscle tone
  righting_reflex: float [0.0–1.0] — righting response strength
  vestibular_compensation: float [0.0–1.0] — vestibular correction signal
  postural_atonia: float [0.0–1.0] — REM sleep postural suppression
  antigravity_drive: float [0.0–1.0] — anti-gravity extensor bias

CITATIONS:
    PMC2829753 — Reed WR, Shum-Siu A, Magnuson DS (2008). Reticulospinal Pathways in
        the Ventrolateral Funiculus With Terminations in the Cervical and Lumbar
        Enlargements of the Adult Rat Spinal Cord. Exp Neurol.
    PMC2565459 — Vinay L, Ben-Mabrouk F, Brocard F et al. (2005). Perinatal
        Development of the Motor Systems Involved in Postural Control. Exp Brain Res.

CITATIONS
---------
  - [Massion 1992, Prog Neurobiol 38:35]
  - [Takakusaki 2017, J Neurol 264:1]
  - [Mori 1987, Prog Brain Res 76:165]
"""

from brain.base_mechanism import BrainMechanism


class PosturalReticularStabilizer(BrainMechanism):
    """
    Medial RF: postural tone, righting reflexes, vestibular compensation.

    Maintains anti-gravity posture and controls postural atonia during REM.
    """

    STATE_FIELDS = [
        "postural_tone", "righting_reflex", "vestibular_compensation",
        "postural_atonia", "antigravity_drive", "tick_count",
    ]

    TONE_GAIN = 0.55
    RIGHTING_GAIN = 0.50
    VESTIBULAR_GAIN = 0.45
    GRAVITY_GAIN = 0.60

    def __init__(self, name: str = "PosturalReticularStabilizer_PosturalReticularStabilizer",
                 human_analog: str = "Medial RF — postural tone and righting reflexes",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["postural_tone"] = 0.50
        self.state["righting_reflex"] = 0.30
        self.state["vestibular_compensation"] = 0.20
        self.state["postural_atonia"] = 0.0
        self.state["antigravity_drive"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        cerebellar = prior.get("CerebellarDeepNuclei", {}).get("corrective_signal", 0.0)
        rem_atonia = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        motor_command = prior.get("MotorThalamus", {}).get("motor_command_strength", 0.0)

        # Postural tone: baseline from arousal; cortical input modulates
        postural_tone = arousal * self.TONE_GAIN
        # Motor cortex adds voluntary posture command
        postural_tone += motor_command * 0.20
        postural_tone = min(1.0, max(0.0, postural_tone))

        # Righting reflex: vestibular tilt triggers corrective response
        righting_reflex = abs(vestibular - 0.5) * self.RIGHTING_GAIN
        # Cerebellar correction strengthens righting
        righting_reflex += cerebellar * 0.30

        # Vestibular compensation: correction for head tilt
        vestibular_compensation = abs(vestibular - 0.5) * self.VESTIBULAR_GAIN

        # Postural atonia: REM atonia suppresses postural muscles
        postural_atonia = rem_atonia * 0.80

        # Antigravity drive: extensor bias (anti-gravity muscle activation)
        antigravity_drive = (postural_tone * 0.50) + (1.0 - rem_atonia) * 0.30

        # --- Persist ---
        self.state["postural_tone"] = round(postural_tone, 4)
        self.state["righting_reflex"] = round(righting_reflex, 4)
        self.state["vestibular_compensation"] = round(vestibular_compensation, 4)
        self.state["postural_atonia"] = round(postural_atonia, 4)
        self.state["antigravity_drive"] = round(antigravity_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "postural_tone": round(postural_tone, 4),
            "righting_reflex": round(righting_reflex, 4),
            "vestibular_compensation": round(vestibular_compensation, 4),
            "postural_atonia": round(postural_atonia, 4),
            "antigravity_drive": round(antigravity_drive, 4),
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


