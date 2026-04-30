"""
AnteroVentralThalamus — AV — Papez circuit / spatial memory

NEURAL SUBSTRATE
================
The anteroventral thalamic nucleus (AV) is one of three anterior
thalamic nuclei (with AD, AM) and a core node of the Papez circuit.
AV receives a dense unilateral projection from the medial mammillary
nucleus (MMN) via the mammillothalamic tract, plus dense subicular
input via the postcommissural fornix. AV projects to the retrosplenial
cortex, cingulate cortex (especially area 29) and presubiculum.

AV is functionally specialized for theta-paced spatial memory: AV
contains theta-modulated cells (Tsanov 2011) and a small population of
HD-modulated cells; in rodents, lesions of AV impair spatial reference
memory in radial maze and water maze tasks (Aggleton & Brown 1999).

KEY FINDINGS
============
1. Mammillothalamic (MMN→AV) tract essential for diencephalic amnesia
   [Aggleton JP 1999, Behav Brain Sci 22:425, doi:10.1017/S0140525X99002034]
2. AV theta-modulated firing and HD tuning in freely moving rats
   [Tsanov M 2011, J Neurosci 31:9489, doi:10.1523/JNEUROSCI.0353-11.2011]
3. Mammillothalamic tract lesions disrupt AV theta / spatial memory
   [Vann SD 2009, Hippocampus 19:1198, doi:10.1002/hipo.20585]
4. AV/AM lesions impair allocentric spatial learning (radial-arm / T-maze)
   [Aggleton JP 1996, Behav Brain Res 81:189, doi:10.1016/S0166-4328(96)89080-2]
5. Anterior thalamic theta circuit (hippocampus / PFC) spatial memory
   [Jankowski MM 2013, Front Syst Neurosci 7:45, doi:10.3389/fnsys.2013.00045]
6. AV inputs required for subiculum spatial coding
   [Nelson AJD 2021, J Neurosci 41:6511, doi:10.1523/JNEUROSCI.2868-20.2021]

INPUTS
======
- MammillaryBodyMedial.mmn_drive (mammillothalamic driver)
- SubiculumDorsal.subiculum_output (postcommissural fornix)
- RetrosplenialCortex.cortical_drive (Layer-VI feedback)
- MedialSeptum.theta_signal (cholinergic / GABAergic theta pacing)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- av_drive (0-1)
- retrosplenial_signal (0-1)
- cingulate_signal (0-1)
- theta_modulation (0-1) — theta-paced firing depth
- spatial_memory_signal (0-1)
- av_state (str): "theta_active" | "spatial_relay" | "quiet"
"""

import math
from brain.base_mechanism import BrainMechanism


class AnteroVentralThalamus(BrainMechanism):
    """AV — Papez-circuit anteroventral spatial-memory relay."""

    BASELINE = 0.09
    SMOOTH = 0.22
    THETA_THRESHOLD = 0.30
    SPATIAL_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="AnteroVentralThalamus",
            human_analog="Anteroventral thalamic nucleus (AV)",
            layer="subcortical",
        )
        self.state.setdefault("av_drive", self.BASELINE)
        self.state.setdefault("retrosplenial_signal", 0.0)
        self.state.setdefault("cingulate_signal", 0.0)
        self.state.setdefault("theta_modulation", 0.0)
        self.state.setdefault("spatial_memory_signal", 0.0)
        self.state.setdefault("av_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("theta_count", 0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("theta_phase", 0.0)

    # ---- helper sub-signals ----

    def _mmn_driver(self, mmn: float) -> float:
        """Mammillothalamic driver — Aggleton 1999, Vann 2009."""
        return min(1.0, mmn * 1.05)

    def _drive_target(self, mmn: float, sub: float, theta: float,
                      ctx: float, trn: float) -> float:
        """Composite AV drive."""
        excitation = (self.BASELINE
                      + mmn * 0.40
                      + sub * 0.25
                      + theta * 0.15
                      + ctx * 0.10)
        inhibition = trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _theta_modulation(self, drive: float, theta: float,
                          phase: float) -> float:
        """Theta-paced firing depth (Tsanov 2011).

        AV cells modulate firing depth with septal theta. Phase is
        advanced each tick to model 8 Hz cycle.
        """
        if theta < 0.10:
            return 0.0
        # depth scales with septal theta amplitude; phase produces
        # a small oscillation around mean drive.
        cyc = 0.5 * (1.0 + math.sin(phase))
        return min(1.0, theta * (0.5 + cyc * 0.5) * drive * 1.2)

    def _retrosplenial(self, drive: float, theta_mod: float) -> float:
        """RSC-projecting axons (Aggleton 1996)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.55 + theta_mod * 0.25)

    def _cingulate(self, drive: float, sub: float) -> float:
        """Cingulate area 29/30 component."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.50 + sub * 0.20)

    def _spatial_memory(self, drive: float, mmn: float, sub: float,
                         theta_mod: float) -> float:
        """Composite spatial memory signal (Nelson 2021)."""
        return min(1.0, drive * 0.30 + mmn * 0.30
                        + sub * 0.20 + theta_mod * 0.20)

    def _classify_state(self, drive: float, theta_mod: float,
                         sub: float) -> str:
        if drive < 0.13:
            return "quiet"
        if theta_mod > self.THETA_THRESHOLD:
            return "theta_active"
        if sub > self.SPATIAL_THRESHOLD or drive > 0.30:
            return "spatial_relay"
        return "spatial_relay"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mmn_data = prior.get("MammillaryBodyMedial", {})
        if not mmn_data:
            mmn_data = prior.get("MedialMammillary", {})
        if not mmn_data:
            mmn_data = prior.get("MammillaryBody", {})
        mmn = float(mmn_data.get("mmn_drive",
                          mmn_data.get("medial_mammillary_output",
                              mmn_data.get("output", 0.0))))

        sub_data = prior.get("SubiculumDorsal", {})
        if not sub_data:
            sub_data = prior.get("Subiculum", {})
        sub = float(sub_data.get("subiculum_output",
                          sub_data.get("subicular_output", 0.0)))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        ctx_data = prior.get("RetrosplenialCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                          ctx_data.get("rsc_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        mmn_eff = self._mmn_driver(mmn)
        target = self._drive_target(mmn_eff, sub, theta, ctx, trn)
        prev_drive = float(self.state.get("av_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # advance theta phase (8 Hz proxy ≈ 0.5 rad/tick)
        phase = float(self.state.get("theta_phase", 0.0)) + 0.5
        if phase > 6.283:
            phase -= 6.283
        theta_mod = self._theta_modulation(new_drive, theta, phase)

        rsc = self._retrosplenial(new_drive, theta_mod)
        cing = self._cingulate(new_drive, sub)
        sp_mem = self._spatial_memory(new_drive, mmn_eff, sub, theta_mod)

        state = self._classify_state(new_drive, theta_mod, sub)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        theta_count = int(self.state.get("theta_count", 0))
        if state == "theta_active":
            theta_count += 1

        self.state["av_drive"] = round(new_drive, 4)
        self.state["retrosplenial_signal"] = round(rsc, 4)
        self.state["cingulate_signal"] = round(cing, 4)
        self.state["theta_modulation"] = round(theta_mod, 4)
        self.state["spatial_memory_signal"] = round(sp_mem, 4)
        self.state["av_state"] = state
        self.state["recent_states"] = recent
        self.state["theta_count"] = theta_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["theta_phase"] = round(phase, 4)
        self.persist_state()

        return {
            "av_drive": round(new_drive, 4),
            "retrosplenial_signal": round(rsc, 4),
            "cingulate_signal": round(cing, 4),
            "theta_modulation": round(theta_mod, 4),
            "spatial_memory_signal": round(sp_mem, 4),
            "av_state": state,
        }

    def _theta_engagement(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("theta_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("av_drive", 0.0),
            "rsc": self.state.get("retrosplenial_signal", 0.0),
            "theta": self.state.get("theta_modulation", 0.0),
            "state": self.state.get("av_state", "quiet"),
        }
