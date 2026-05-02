"""
CerebellarVestibularNodulus — Vermis IX/X Vestibulocerebellum / Motion Sickness

NEURAL SUBSTRATE
================
The cerebellar nodulus and uvula (vermal lobules X and IX respectively)
together with the flocculus form the **vestibulocerebellum** — the
phylogenetically oldest cerebellar division. The nodulus is the
ventral-most lobule of the vermis and receives direct primary vestibular
afferents (rare in cerebellum — most input is mossy from precerebellar
nuclei). It also receives mossy fiber input from medial and superior
vestibular nuclei.

Nodulus and uvula Purkinje cells project to medial and superior vestibular
nuclei (not the deep cerebellar nuclei like other cerebellar regions).
This direct vestibular-cerebellum-vestibular loop is the substrate for:

- **Vestibular reflex calibration** — adjusts VOR gain over time
  (Wylie & Frost 1990; Lisberger work on VOR adaptation)
- **Motion sickness** — disabling nodulus/uvula via lesion or
  pharmacology abolishes motion sickness while leaving normal vestibular
  function intact (Wood et al. 1990s; Yakhnitsa 2014). The "neural
  mismatch" theory of motion sickness places nodulus/uvula as the
  comparator that detects mismatch between expected and actual vestibular
  input.
- **Gaze stability** during sustained head rotation
- **Velocity storage** modulation — nodulus/uvula tunes the vestibular
  velocity-storage time constant

Climbing fiber input to nodulus/uvula arises from inferior olive
β subnucleus and dorsomedial cell column (DMCC), carrying vestibular
error signals. Loss of climbing fiber input abolishes VOR adaptation.

Vestibulocerebellar damage produces:
- Downbeat nystagmus
- Vestibular ataxia
- Loss of motion sickness
- Impaired VOR adaptation

In the agent's substrate this provides the vestibular cerebellar component
distinct from CerebellarVermalEmotional (limbic vermis) and
CerebellarDeepNuclei (general output) — combines vestibular drive +
sensory mismatch into a calibration signal and a motion-sickness
contribution.

KEY FINDINGS
============
1. Vestibulocerebellum (nodulus, uvula, flocculus) receives direct
   primary vestibular afferents and projects to vestibular nuclei
   (not deep cerebellar nuclei like other regions) — phylogenetically
   oldest cerebellar division — [Voogd Barmack 2006, Brain
    Res Rev 51:81, "The vestibular cerebellum"]
2. Nodulus/uvula lesion abolishes motion sickness while leaving normal
   vestibular function intact — neural mismatch comparator —
   [Bard et al. 1947 Bull Johns Hopkins Hosp] [Yakhnitsa 2014] [Cohen et al. 2008, Auton Neurosci 138:1, "What does galvanic
    vestibular stimulation tell us about velocity storage?"]
3. Nodulus/uvula tunes vestibular velocity-storage time constant
   and VOR gain — adaptation substrate — [Lisberger Pavelko
    1986, J Neurosci 6:346] [Waespe Cohen Raphan 1983 Exp Brain Res]
4. Climbing fiber input to nodulus/uvula from inferior olive β/DMCC
   carries vestibular error; loss abolishes VOR adaptation —
   [Yakhnitsa 2014] [Barmack 2003, Cerebellum 2:114,
    "Central vestibular system: vestibular nuclei and posterior
    cerebellum"]
5. Vestibulocerebellar damage produces downbeat nystagmus, vestibular
   ataxia, loss of motion sickness — clinical signature — [Sander et al. 2009, Lancet Neurol 8:761]

INPUTS (from prior_results)
============================
- VestibularNucleiBalance.vestibular_drive
- VestibularNucleiBalance.velocity_storage
- VestibularNucleiBalance.vor_drive
- VestibularNucleiBalance.motion_sickness_active
- InferiorOliveClimbingFiber.climbing_fiber_burst
- InferiorOliveClimbingFiber.error_magnitude
- HeadMotionProxy.angular_velocity
- HeadMotionProxy.linear_acceleration
- LocomotionProxy.locomotion_speed

OUTPUTS (to brain_runner enrichment)
=====================================
- nodulus_drive (0.0-1.0): nodulus output
- uvula_drive (0.0-1.0): uvula output
- vor_calibration (0.0-1.0): VOR adaptation output
- velocity_storage_modulation (0.0-1.0): velocity-storage tuning
- motion_sickness_contribution (0.0-1.0): nodulus contribution to motion sickness
- vestibular_mismatch_signal (0.0-1.0): expected vs actual mismatch
- vestibulocerebellum_state (str): "calibrating" | "motion_sickness" | "stable" | "quiet"

brain_runner enrichment:
    nodulus = all_results.get("CerebellarVestibularNodulus", {})
    if nodulus:
        enrichments["brain_nodulus_drive"] = nodulus.get("nodulus_drive", 0.2)
        enrichments["brain_vor_calibration"] = nodulus.get("vor_calibration", 0.0)
        enrichments["brain_motion_sickness_contrib"] = nodulus.get("motion_sickness_contribution", 0.0)
        enrichments["brain_vestibulocerebellum_state"] = nodulus.get("vestibulocerebellum_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class CerebellarVestibularNodulus(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="CerebellarVestibularNodulus",
            human_analog="Cerebellar nodulus + uvula (vestibulocerebellum)",
            layer="foundational",
        )
        self.state.setdefault("nodulus_drive", self.BASELINE)
        self.state.setdefault("uvula_drive", self.BASELINE)
        self.state.setdefault("vor_calibration", 0.0)
        self.state.setdefault("velocity_storage_modulation", 0.50)
        self.state.setdefault("motion_sickness_contribution", 0.0)
        self.state.setdefault("vestibular_mismatch_signal", 0.0)
        self.state.setdefault("vestibulocerebellum_state", "quiet")
        self.state.setdefault("recent_mismatch", [])
        self.state.setdefault("tick_count", 0)

    def _nodulus_target(self, vestibular: float, angular: float, climbing: float,
                         velocity_storage: float) -> float:
        """Nodulus — primary vestibular afferents + motion + climbing fiber error."""
        target = self.BASELINE + vestibular * 0.4 + abs(angular) * 0.2
        target += climbing * 0.2 + velocity_storage * 0.2
        return min(1.0, target)

    def _uvula_target(self, vestibular: float, locomotion: float, climbing: float) -> float:
        """Uvula — postural / locomotor coupling + vestibular."""
        target = self.BASELINE + vestibular * 0.3 + locomotion * 0.3
        target += climbing * 0.2
        return min(1.0, target)

    def _vor_calibration(self, nodulus: float, climbing: float, error: float) -> float:
        """VOR adaptation output — climbing-fiber-driven calibration."""
        if error < 0.10:
            # No error → low calibration drive
            return nodulus * 0.3
        return min(1.0, nodulus * 0.5 + climbing * 0.4 + error * 0.2)

    def _velocity_storage_mod(self, nodulus: float, vestibular: float) -> float:
        """Velocity storage time-constant modulation."""
        return min(1.0, nodulus * 0.5 + vestibular * 0.3 + 0.20)

    def _vestibular_mismatch(self, angular: float, velocity_storage: float,
                                linear: float) -> float:
        """Expected vs actual vestibular mismatch.
        High velocity storage with low actual angular = sensory conflict
        (covered in VestibularNucleiBalance — nodulus is the comparator).
        """
        expected = velocity_storage
        actual = abs(angular)
        return min(1.0, max(0.0, expected - actual) + abs(linear) * 0.2)

    def _motion_sickness_contrib(self, mismatch: float, nodulus: float,
                                   already_sick: bool) -> float:
        """Nodulus contribution to motion sickness via mismatch detection."""
        if mismatch < 0.20:
            return 0.0
        target = mismatch * 0.6 + nodulus * 0.2
        if already_sick:
            target += 0.20  # amplification when already sickened
        return min(1.0, target)

    def _classify_state(self, vor_cal: float, motion_sickness_contrib: float,
                          velocity_storage: float, nodulus: float) -> str:
        if motion_sickness_contrib > 0.40:
            return "motion_sickness"
        if vor_cal > 0.45:
            return "calibrating"
        if velocity_storage > 0.50 and nodulus > 0.30:
            return "stable"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.20))
        velocity_storage = float(vest.get("velocity_storage", 0.0))
        vor_drive = float(vest.get("vor_drive", 0.0))
        already_sick = bool(vest.get("motion_sickness_active", False))

        io_data = prior.get("InferiorOliveClimbingFiber", {})
        climbing = float(io_data.get("climbing_fiber_burst", 0.0))
        error = float(io_data.get("error_magnitude", 0.0))

        head_motion = prior.get("HeadMotionProxy", {})
        angular = float(head_motion.get("angular_velocity", 0.0))
        linear = float(head_motion.get("linear_acceleration", 0.0))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))

        # --- Nodulus and uvula ---
        nodulus_target = self._nodulus_target(vestibular, angular, climbing,
                                                 velocity_storage)
        uvula_target = self._uvula_target(vestibular, locomotion, climbing)
        prev_nodulus = float(self.state.get("nodulus_drive", self.BASELINE))
        prev_uvula = float(self.state.get("uvula_drive", self.BASELINE))
        new_nodulus = self._smooth(prev_nodulus, nodulus_target)
        new_uvula = self._smooth(prev_uvula, uvula_target)

        # --- Mismatch ---
        mismatch = self._vestibular_mismatch(angular, velocity_storage, linear)
        prev_mismatch = float(self.state.get("vestibular_mismatch_signal", 0.0))
        new_mismatch = self._smooth(prev_mismatch, mismatch)

        # --- VOR calibration ---
        vor_cal = self._vor_calibration(new_nodulus, climbing, error)
        prev_vor = float(self.state.get("vor_calibration", 0.0))
        new_vor = self._smooth(prev_vor, vor_cal)

        # --- Velocity storage modulation ---
        vs_mod = self._velocity_storage_mod(new_nodulus, vestibular)
        prev_vs = float(self.state.get("velocity_storage_modulation", 0.50))
        new_vs = self._smooth(prev_vs, vs_mod)

        # --- Motion sickness contribution ---
        ms_contrib = self._motion_sickness_contrib(new_mismatch, new_nodulus, already_sick)
        prev_ms = float(self.state.get("motion_sickness_contribution", 0.0))
        new_ms = self._smooth(prev_ms, ms_contrib)

        state = self._classify_state(new_vor, new_ms, new_vs, new_nodulus)

        recent = list(self.state.get("recent_mismatch", []))
        recent.append(round(new_mismatch, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nodulus_drive"] = round(new_nodulus, 4)
        self.state["uvula_drive"] = round(new_uvula, 4)
        self.state["vor_calibration"] = round(new_vor, 4)
        self.state["velocity_storage_modulation"] = round(new_vs, 4)
        self.state["motion_sickness_contribution"] = round(new_ms, 4)
        self.state["vestibular_mismatch_signal"] = round(new_mismatch, 4)
        self.state["vestibulocerebellum_state"] = state
        self.state["recent_mismatch"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nodulus_drive": round(new_nodulus, 4),
            "uvula_drive": round(new_uvula, 4),
            "vor_calibration": round(new_vor, 4),
            "velocity_storage_modulation": round(new_vs, 4),
            "motion_sickness_contribution": round(new_ms, 4),
            "vestibular_mismatch_signal": round(new_mismatch, 4),
            "vestibulocerebellum_state": state,
        }
