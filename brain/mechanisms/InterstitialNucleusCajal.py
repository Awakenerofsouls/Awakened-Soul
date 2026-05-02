"""
InterstitialNucleusCajal — INC / Vertical-Gaze Velocity-to-Position Integrator

NEURAL SUBSTRATE
================
Small nucleus in rostral midbrain reticular formation, lateral to oculomotor
nucleus, dorsal to MLF (medial longitudinal fasciculus). The vertical-gaze
velocity-to-position neural integrator — direct functional complement to NPH
(which integrates horizontal).

Inputs:
- riMLF (rostral interstitial nucleus of MLF) — vertical saccade burst
  generator. Provides velocity command for vertical saccades.
- Vestibular nuclei — head-velocity input for vertical VOR
- Cerebellum (flocculus / fastigial) — calibration feedback

Outputs:
- Oculomotor nucleus (CN III) — drives elevation/depression motoneurons
- Trochlear nucleus (CN IV) — drives intorsion
- Interstitial commissure — bilateral coordination of vertical gaze

Lesion: vertical-gaze nystagmus, downbeat or upbeat depending on lesion
location, inability to hold vertical gaze.

KEY FINDINGS
============
1. INC is the vertical-gaze velocity-to-position integrator — mirrors
   NPH's horizontal role; firing rate proportional to vertical eye
   position — [Crawford 1991, J Neurophysiol 65:1268, PMID 1875238]
2. INC lesion produces vertical-gaze nystagmus + downbeat/upbeat
   eye drift; severity scales with lesion size — [Helmchen 2002,
   Brain 125:2150, doi:10.1093/brain/awf215]
3. riMLF→INC vertical-saccade pathway generates upward + downward
   saccades; INC integrates riMLF velocity command into eye position —
   [Buttner-Ennever 1988, Brain Res Bull 21:691, PMID 3219495]
4. INC neurons fire in proportion to vertical eye position; tonic
   firing rate encodes elevation; small lesions impair holding
   eccentric vertical gaze — [King 1981, J Neurophysiol 46:549,
   PMID 7299434]
5. INC + interstitial commissure coordinate conjugate vertical gaze;
   commissure transection produces vertical disconjugacy —
   [Hassler 1972, Acta Anat 81:177, PMID 4336167]

INPUTS
======
- HeadMotionProxy.angular_velocity_pitch (default 0; vertical head motion)
- VestibularNucleiBalance.vor_drive
- CerebellarVestibularNodulus.vor_calibration
- CerebellarDeepNuclei.fastigial_drive
- ArousalRegulator.tonic_level

OUTPUTS
=======
- inc_drive (0-1) — INC firing rate
- vertical_velocity_input (-1 to 1) — input velocity (signed)
- vertical_position_output (-1 to 1) — integrated position
- vertical_gaze_holding (0-1) — gaze-hold magnitude
- vertical_nystagmus_marker (bool) — chronic poor calibration with offset
- inc_state (str): "up_gaze" | "down_gaze" | "stable_gaze" |
  "nystagmus" | "quiet"

brain_runner enrichment:
    inc = all_results.get("InterstitialNucleusCajal", {})
    if inc:
        enrichments["brain_inc_drive"] = inc.get("inc_drive", 0.0)
        enrichments["brain_vertical_position"] = inc.get("vertical_position_output", 0.0)
        enrichments["brain_vertical_gaze_holding"] = inc.get("vertical_gaze_holding", 0.0)
        enrichments["brain_vertical_nystagmus"] = inc.get("vertical_nystagmus_marker", False)
        enrichments["brain_inc_state"] = inc.get("inc_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class InterstitialNucleusCajal(BrainMechanism):
    """INC — vertical-gaze velocity-to-position integrator."""

    BASELINE = 0.20
    SMOOTH = 0.30
    INTEGRATOR_LEAK = 0.05
    NYSTAGMUS_THRESHOLD = 30

    def __init__(self):
        super().__init__(
            name="InterstitialNucleusCajal",
            human_analog="Interstitial nucleus of Cajal (vertical gaze)",
            layer="foundational",
        )
        self.state.setdefault("inc_drive", self.BASELINE)
        self.state.setdefault("vertical_velocity_input", 0.0)
        self.state.setdefault("vertical_position_output", 0.0)
        self.state.setdefault("vertical_gaze_holding", 0.50)
        self.state.setdefault("vertical_nystagmus_marker", False)
        self.state.setdefault("inc_state", "quiet")
        self.state.setdefault("integrator_drift_streak", 0)
        self.state.setdefault("recent_position", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vestibular: float, vor_calib: float,
                        fastigial: float, arousal: float) -> float:
        """INC drive — proportional to vestibular + cerebellar inputs."""
        target = self.BASELINE + vestibular * 0.30 + vor_calib * 0.20
        target += fastigial * 0.20 + max(0.0, arousal - 0.40) * 0.10
        return min(1.0, target)

    def _velocity_input(self, pitch: float, vor: float) -> float:
        """Vertical velocity = pitch head motion + vertical VOR drive."""
        return max(-1.0, min(1.0, pitch + vor * 0.5))

    def _integrate_position(self, prev: float, velocity: float,
                              calibration: float) -> float:
        """Velocity-to-position integration with leak (Crawford 1991).
        Higher cerebellar calibration → lower leak → better gaze hold.
        """
        leak = self.INTEGRATOR_LEAK * (1.0 - min(0.9, calibration))
        new_pos = prev + velocity * 0.3 - leak * prev
        return max(-1.0, min(1.0, new_pos))

    def _gaze_holding(self, position: float, drive: float) -> float:
        return min(1.0, abs(position) * 0.7 + drive * 0.3)

    def _classify_state(self, position: float, drive: float, velocity: float,
                          nystagmus: bool) -> str:
        if nystagmus:
            return "nystagmus"
        if abs(velocity) > 0.30:
            # Active vertical saccade
            return "up_gaze" if velocity > 0 else "down_gaze"
        if position > 0.20 and drive > 0.25:
            return "up_gaze"
        if position < -0.20 and drive > 0.25:
            return "down_gaze"
        if abs(position) < 0.15 and drive > 0.20:
            return "stable_gaze"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH
    def _conjugate_coordination(self, position: float,
                                  contralateral_pos: float = None) -> float:
        """Vertical-gaze conjugate coordination via interstitial commissure
        (Hassler 1972). Without contralateral information, return
        unilateral position. With it, compute conjugacy quality.
        """
        if contralateral_pos is None:
            return abs(position)
        diff = abs(position - contralateral_pos)
        return max(0.0, 1.0 - diff)

    def _vertical_saccade_burst_phase(self, velocity: float,
                                         prev_velocity: float) -> float:
        """Detect vertical saccade burst phase from riMLF — large
        velocity transient signals saccade onset, integrated by INC
        into position (Buttner-Ennever 1988).
        """
        delta = velocity - prev_velocity
        if abs(delta) < 0.15:
            return 0.0
        return min(1.0, abs(delta) * 1.5)

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "drive": self.state.get("inc_drive", 0.0),
            "position": self.state.get("vertical_position_output", 0.0),
            "gaze_holding": self.state.get("vertical_gaze_holding", 0.0),
            "nystagmus": self.state.get("vertical_nystagmus_marker", False),
            "state": self.state.get("inc_state", "quiet"),
        }


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        head = prior.get("HeadMotionProxy", {})
        pitch = float(head.get("angular_velocity_pitch", 0.0))

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.20))
        vor = float(vest.get("vor_drive", 0.0))

        nodulus = prior.get("CerebellarVestibularNodulus", {})
        vor_calib = float(nodulus.get("vor_calibration", 0.0))

        cdn = prior.get("CerebellarDeepNuclei", {})
        fastigial = float(cdn.get("fastigial_drive", 0.30))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- INC drive ---
        target = self._drive_target(vestibular, vor_calib, fastigial, tonic)
        prev_drive = float(self.state.get("inc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # --- Velocity + position ---
        velocity = self._velocity_input(pitch, vor)
        prev_pos = float(self.state.get("vertical_position_output", 0.0))
        calibration = (vor_calib + fastigial * 0.5) / 2.0
        new_pos = self._integrate_position(prev_pos, velocity, calibration)

        # --- Gaze holding ---
        gaze_hold_target = self._gaze_holding(new_pos, new_drive)
        prev_gh = float(self.state.get("vertical_gaze_holding", 0.5))
        new_gh = self._smooth(prev_gh, gaze_hold_target)

        # --- Nystagmus detection (chronic low calibration with offset) ---
        prev_streak = int(self.state.get("integrator_drift_streak", 0))
        if calibration < 0.10 and abs(new_pos) > 0.05:
            streak = prev_streak + 1
        elif abs(velocity) < 0.10 and abs(new_pos - prev_pos) > 0.15:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        nystagmus = streak > self.NYSTAGMUS_THRESHOLD

        state = self._classify_state(new_pos, new_drive, velocity, nystagmus)

        recent = list(self.state.get("recent_position", []))
        recent.append(round(new_pos, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["inc_drive"] = round(new_drive, 4)
        self.state["vertical_velocity_input"] = round(velocity, 4)
        self.state["vertical_position_output"] = round(new_pos, 4)
        self.state["vertical_gaze_holding"] = round(new_gh, 4)
        self.state["vertical_nystagmus_marker"] = nystagmus
        self.state["inc_state"] = state
        self.state["integrator_drift_streak"] = streak
        self.state["recent_position"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "inc_drive": round(new_drive, 4),
            "vertical_velocity_input": round(velocity, 4),
            "vertical_position_output": round(new_pos, 4),
            "vertical_gaze_holding": round(new_gh, 4),
            "vertical_nystagmus_marker": nystagmus,
            "inc_state": state,
        }
