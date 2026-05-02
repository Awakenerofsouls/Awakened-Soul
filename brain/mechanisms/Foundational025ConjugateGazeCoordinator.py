"""
Build 25: Foundational025ConjugateGazeCoordinator — Superior Colliculus Gaze Control
================================================================================

PLACEMENT:
  Layer:    foundational (midbrain — superior colliculus, rostral interstitial nucleus)
  Filename: brain/foundational/Foundational025ConjugateGazeCoordinator.py
  Instance name: ConjugateGazeCoordinator

NEURAL SUBSTRATE:
  Superior colliculus (SC) in midbrain — the multisensory integration and
  gaze command center. The deep layers contain a motor map of visual space;
  stimulation produces coordinated eye, head, and pinna movements toward
  or away from stimuli. Contains:
  - Deep layer: motor map for orienting movements (saccades, head turns)
  - Intermediate layer: movement initiation, fixation neurons
  - Superficial layers: visual receptive fields

  The SC receives:
  - Visual: retina, visual cortex (overwrite signal)
  - Auditory: inferior colliculus, auditory cortex
  - Somatosensory: somatosensory cortex, spinal cord
  - Frontal eye fields (FEF): voluntary saccade commands
  - Basal ganglia (substantia nigra pars reticulata): saccade gating (INH)

  Human analog: saccadic eye movements, gaze shifts, orienting, visual search.

Output keys:
  gaze_shift_command: float [0.0–1.0] — magnitude of gaze shift command
  gaze_target_x: float [-1.0 to 1.0] — horizontal gaze target
  gaze_target_y: float [-1.0 to 1.0] — vertical gaze target
  saccade_initiation: float [0.0–1.0] — saccade readiness
  orienting_priority: float [0.0–1.0] — priority for orienting response

CITATIONS:
    PMC6957570 — May PJ, Sun W, Wright NF et al. (2020). Pupillary Light Reflex
        Circuits in the Macaque Monkey: The Preganglionic Edinger-Westphal Nucleus.
        J Comp Neurol.
    PMC8869431 — May PJ, Warren S (2020). Pupillary Light Reflex Circuits in the
        Macaque Monkey: The Olivary Pretectal Nucleus. J Comp Neurol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class ConjugateGazeCoordinator(BrainMechanism):
    """
    Superior colliculus: gaze command, orienting, saccade control.

    Integrates visual, auditory, and somatosensory cues to generate
    coordinated gaze shift commands. Models the motor map of the SC
    deep layers.
    """

    STATE_FIELDS = [
        "gaze_shift_command", "gaze_target_x", "gaze_target_y",
        "saccade_initiation", "orienting_priority", "tick_count",
    ]

    SACCADE_GAIN = 0.60
    ORIENT_GAIN = 0.50
    FIXATION_THRESHOLD = 0.30

    def __init__(self, name: str = "ConjugateGazeCoordinator",
                 human_analog: str = "Superior colliculus — conjugate gaze and orienting",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["gaze_shift_command"] = 0.0
        self.state["gaze_target_x"] = 0.0
        self.state["gaze_target_y"] = 0.0
        self.state["saccade_initiation"] = 0.10
        self.state["orienting_priority"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        visual_salience = prior.get("VisualSalienceMap", {}).get("salience_level", 0.0)
        auditory_salience = prior.get("AuditoryOrienting", {}).get("azimuth_salience", 0.0)
        frontal_command = prior.get("FrontalEyeFields", {}).get("saccade_command", 0.0)
        basal_ganglia = prior.get("SNprInhibition", {}).get("snr_inhibition", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)

        # Orienting priority: strongest salience determines priority
        max_salience = max(visual_salience, auditory_salience, frontal_command)
        orienting_priority = max_salience * self.ORIENT_GAIN

        # Saccade initiation: SC activity minus SNr inhibition
        sc_activity = max_salience * self.SACCADE_GAIN
        snr_suppression = basal_ganglia * 0.60
        saccade_initiation = max(0.0, min(1.0, sc_activity - snr_suppression))

        # Gaze shift command: proportional to saccade readiness
        gaze_shift = saccade_initiation * arousal

        # Gaze targets: derive from salience locations
        # For simplicity, use visual vs auditory to determine axis
        gaze_target_x = np.clip((auditory_salience - 0.5) * 2.0 * saccade_initiation, -1.0, 1.0)
        gaze_target_y = np.clip((visual_salience - 0.5) * 2.0 * saccade_initiation, -1.0, 1.0)

        # --- Persist ---
        self.state["gaze_shift_command"] = round(gaze_shift, 4)
        self.state["gaze_target_x"] = round(float(gaze_target_x), 4)
        self.state["gaze_target_y"] = round(float(gaze_target_y), 4)
        self.state["saccade_initiation"] = round(saccade_initiation, 4)
        self.state["orienting_priority"] = round(orienting_priority, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gaze_shift_command": round(gaze_shift, 4),
            "gaze_target_x": round(float(gaze_target_x), 4),
            "gaze_target_y": round(float(gaze_target_y), 4),
            "saccade_initiation": round(saccade_initiation, 4),
            "orienting_priority": round(orienting_priority, 4),
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

