"""
NucleusPrepositusHypoglossi — NPH Gaze-Holding Eye Movement Integrator

NEURAL SUBSTRATE
================
The nucleus prepositus hypoglossi (NPH, also called nucleus prepositus
nervi hypoglossi) sits in the medulla, adjacent to the medial vestibular
nucleus (MVN) and rostral to the hypoglossal nucleus (despite the name,
it is not directly involved in tongue motor control). NPH and MVN
together form the **horizontal gaze-holding neural integrator** —
they convert eye-velocity signals into eye-position signals through a
mathematical integration operation that holds gaze stable between
saccades.

The Robinson "neural integrator" framework (Robinson 1989, Cannon &
Robinson 1985) established NPH-MVN as the substrate for the position-
holding signal that maintains stable gaze after eye movements. Without
this integrator function, the eyes drift back to center after every
saccade, producing nystagmus.

NPH receives:
- Vestibular afferents from semicircular canals (via vestibular nuclei)
- Eye velocity signals from saccadic burst neurons (paramedian pontine
  reticular formation, PPRF)
- Visual feedback from optokinetic system (NOT pretectum)
- Cerebellar feedback from flocculus (calibration of the integrator)

NPH projects to:
- Oculomotor nuclei (III, IV, VI) for direct eye-position commands
- Vestibular nuclei (reciprocal coupling)
- Inferior olive (climbing fiber feedback)

The integrator function depends on positive feedback within the
NPH-MVN-cerebellar flocculus loop. Damage to NPH or its inputs produces
gaze-evoked nystagmus — eyes drift centrally after attempted lateral
gaze, then re-fixate. This is a clinical localizing sign for medullary/
pontine lesions.

Beyond gaze-holding, NPH contributes to:
- VOR phase tuning (with flocculus)
- Smooth pursuit eye movements
- Coupling head and eye movements

In Nova's substrate this provides the gaze-holding integrator —
combines eye velocity / vestibular / cerebellar floccular input proxies
to produce a position-holding signal.

KEY FINDINGS
============
1. NPH and medial vestibular nucleus together form the horizontal gaze-
   holding neural integrator — converts eye-velocity to eye-position
   signal — [Cannon Robinson 1985, Brain Res 358:217, "An improved
   neural network model for the neural integrator of the oculomotor
   system"] [Robinson 1989, Annu Rev Neurosci 12:33]
2. NPH lesion produces gaze-evoked nystagmus (eyes drift centrally
   after lateral gaze attempt) — clinical localizing sign for
   medullary/pontine damage — [Leigh Zee 2015, "The Neurology
    of Eye Movements" 5th ed.]
3. Cerebellar flocculus calibrates NPH-MVN integrator function;
   floccular damage produces failure of velocity-to-position
   integration — [Lisberger Pavelko 1986, J Neurosci 6:346] [Zee Yamazaki Butler Gücer 1981 J Neurophysiol]
4. NPH receives input from saccadic burst neurons (PPRF) and projects
   to oculomotor nuclei + reciprocally to vestibular nuclei —
   [Strassman Highstein McCrea 1986 J Comp Neurol]
5. NPH contributes to VOR phase, smooth pursuit, and head-eye coupling
   beyond pure gaze-holding — [Buttner-Ennever Buttner 1992
    in Schmidt-Bleek "Vestibular and Brain Stem Control of Eye, Head
    and Body Movements"]

INPUTS (from prior_results)
============================
- VestibularNucleiBalance.vestibular_drive
- VestibularNucleiBalance.vor_drive
- VestibularNucleiBalance.velocity_storage
- CerebellarVestibularNodulus.vor_calibration
- CerebellarDeepNuclei.fastigial_drive
- HeadMotionProxy.angular_velocity
- VisualInputProxy.motion_strength
- ArousalRegulator.tonic_level
- SuperiorColliculusOrient.sc_orienting_command
- PretectalPupillaryReflex.okr_command

OUTPUTS (to brain_runner enrichment)
=====================================
- nph_drive (0.0-1.0): NPH integrator output
- gaze_holding_signal (0.0-1.0): position-holding signal to oculomotor
- horizontal_velocity_input (signed -1..+1): integrator velocity input
- horizontal_position_output (signed -1..+1): integrated position output
- pursuit_drive (0.0-1.0): smooth pursuit eye-movement contribution
- gaze_evoked_nystagmus_marker (bool): integrator failure
- nph_state (str): "stable_gaze" | "saccade_integrating" | "pursuit" | "nystagmus" | "quiet"

brain_runner enrichment:
    nph = all_results.get("NucleusPrepositusHypoglossi", {})
    if nph:
        enrichments["brain_nph_drive"] = nph.get("nph_drive", 0.2)
        enrichments["brain_gaze_holding"] = nph.get("gaze_holding_signal", 0.5)
        enrichments["brain_pursuit_drive"] = nph.get("pursuit_drive", 0.0)
        enrichments["brain_nph_state"] = nph.get("nph_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class NucleusPrepositusHypoglossi(BrainMechanism):
    BASELINE = 0.30
    NYSTAGMUS_THRESHOLD = 30
    SMOOTH = 0.30  # Eye position needs fast convergence
    INTEGRATOR_LEAK = 0.05

    def __init__(self):
        super().__init__(
            name="NucleusPrepositusHypoglossi",
            human_analog="Nucleus prepositus hypoglossi (gaze-holding integrator)",
            layer="foundational",
        )
        self.state.setdefault("nph_drive", self.BASELINE)
        self.state.setdefault("gaze_holding_signal", 0.50)
        self.state.setdefault("horizontal_velocity_input", 0.0)
        self.state.setdefault("horizontal_position_output", 0.0)
        self.state.setdefault("pursuit_drive", 0.0)
        self.state.setdefault("gaze_evoked_nystagmus_marker", False)
        self.state.setdefault("nph_state", "quiet")
        self.state.setdefault("integrator_drift_streak", 0)
        self.state.setdefault("recent_position", [])
        self.state.setdefault("tick_count", 0)

    def _nph_drive_target(self, vestibular: float, vor_calibration: float,
                           fastigial: float, arousal: float) -> float:
        """NPH drive — integrator activity, scaled by vestibular and cerebellar."""
        target = self.BASELINE + vestibular * 0.3 + vor_calibration * 0.2
        target += fastigial * 0.2
        target += max(0.0, arousal - 0.4) * 0.1
        return min(1.0, target)

    def _velocity_input(self, angular: float, vor: float, motion: float, sc_orient: float) -> float:
        """Horizontal velocity input to integrator — combined eye/head velocity."""
        return max(-1.0, min(1.0, angular + vor * 0.5 + motion * 0.3 + sc_orient * 0.2))

    def _integrate_position(self, prev_position: float, velocity_input: float,
                              calibration: float) -> float:
        """Velocity-to-position integration with leak.
        Position += velocity - leak * position * (1 - calibration).
        Higher calibration = lower leak = better gaze-holding.
        """
        leak = self.INTEGRATOR_LEAK * (1.0 - min(0.9, calibration))
        new_position = prev_position + velocity_input * 0.3 - leak * prev_position
        return max(-1.0, min(1.0, new_position))

    def _gaze_holding_signal(self, position: float, nph: float) -> float:
        """Position-holding signal to oculomotor — magnitude of position commitment."""
        return min(1.0, abs(position) * 0.7 + nph * 0.3)

    def _pursuit_drive(self, motion: float, vor_calibration: float, nph: float) -> float:
        """Smooth-pursuit eye-movement contribution."""
        if motion < 0.10:
            return 0.0
        return min(1.0, motion * 0.6 + vor_calibration * 0.2 + nph * 0.2)

    def _detect_nystagmus(self, streak: int) -> bool:
        """Gaze-evoked nystagmus marker — integrator failing chronically."""
        return streak > self.NYSTAGMUS_THRESHOLD

    def _classify_state(self, nph: float, position: float, pursuit: float,
                          nystagmus: bool, velocity: float) -> str:
        if nystagmus:
            return "nystagmus"
        if pursuit > 0.40:
            return "pursuit"
        if abs(velocity) > 0.30:
            return "saccade_integrating"
        if abs(position) < 0.20 and nph > 0.25:
            return "stable_gaze"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.20))
        vor = float(vest.get("vor_drive", 0.0))
        velocity_storage = float(vest.get("velocity_storage", 0.0))

        nodulus = prior.get("CerebellarVestibularNodulus", {})
        vor_calibration = float(nodulus.get("vor_calibration", 0.0))

        cdn = prior.get("CerebellarDeepNuclei", {})
        fastigial = float(cdn.get("fastigial_drive", 0.30))

        head_motion = prior.get("HeadMotionProxy", {})
        angular = float(head_motion.get("angular_velocity", 0.0))

        visual = prior.get("VisualInputProxy", {})
        motion = float(visual.get("motion_strength", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        sc = prior.get("SuperiorColliculusOrient", {})
        sc_orient = float(sc.get("sc_orienting_command", 0.0))

        pretectum = prior.get("PretectalPupillaryReflex", {})
        okr = float(pretectum.get("okr_command", 0.0))

        # --- NPH drive ---
        nph_target = self._nph_drive_target(vestibular, vor_calibration, fastigial, tonic)
        prev_nph = float(self.state.get("nph_drive", self.BASELINE))
        new_nph = self._smooth(prev_nph, nph_target)

        # --- Velocity input ---
        velocity = self._velocity_input(angular, vor, motion + okr * 0.3, sc_orient)

        # --- Integrate position ---
        prev_position = float(self.state.get("horizontal_position_output", 0.0))
        # Calibration combines floccular vor_calibration + general fastigial signal
        calibration = (vor_calibration + fastigial * 0.5) / 2.0
        new_position = self._integrate_position(prev_position, velocity, calibration)

        # --- Gaze-holding signal ---
        gaze_holding = self._gaze_holding_signal(new_position, new_nph)
        prev_gh = float(self.state.get("gaze_holding_signal", 0.50))
        new_gh = self._smooth(prev_gh, gaze_holding)

        # --- Pursuit ---
        pursuit = self._pursuit_drive(motion, vor_calibration, new_nph)

        # --- Nystagmus detection (integrator failing → drift) ---
        prev_streak = int(self.state.get("integrator_drift_streak", 0))
        # Chronic low-calibration with offset position — integrator failing.
        # Or sudden position change without velocity — also integrator failing.
        if calibration < 0.10 and abs(new_position) > 0.05:
            streak = prev_streak + 1
        elif abs(velocity) < 0.10 and abs(new_position - prev_position) > 0.15:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        nystagmus = self._detect_nystagmus(streak)

        state = self._classify_state(new_nph, new_position, pursuit, nystagmus, velocity)

        recent = list(self.state.get("recent_position", []))
        recent.append(round(new_position, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nph_drive"] = round(new_nph, 4)
        self.state["gaze_holding_signal"] = round(new_gh, 4)
        self.state["horizontal_velocity_input"] = round(velocity, 4)
        self.state["horizontal_position_output"] = round(new_position, 4)
        self.state["pursuit_drive"] = round(pursuit, 4)
        self.state["gaze_evoked_nystagmus_marker"] = nystagmus
        self.state["nph_state"] = state
        self.state["integrator_drift_streak"] = streak
        self.state["recent_position"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nph_drive": round(new_nph, 4),
            "gaze_holding_signal": round(new_gh, 4),
            "horizontal_velocity_input": round(velocity, 4),
            "horizontal_position_output": round(new_position, 4),
            "pursuit_drive": round(pursuit, 4),
            "gaze_evoked_nystagmus_marker": nystagmus,
            "nph_state": state,
        }
