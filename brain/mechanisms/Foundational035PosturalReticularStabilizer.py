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
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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

    def __init__(self, name: str = "PosturalReticularStabilizer",
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

