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
