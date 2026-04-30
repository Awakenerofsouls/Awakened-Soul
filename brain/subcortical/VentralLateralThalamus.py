"""
VentralLateralThalamus — VL — cerebellum → motor cortex relay

NEURAL SUBSTRATE
================
The ventral lateral nucleus (VL) is the cerebellar-recipient motor
thalamic relay to primary motor cortex (M1). VL receives glutamatergic
driver input from the deep cerebellar nuclei (dentate, interpositus and
fastigial) via the dentatothalamic / superior cerebellar peduncle, and
projects "core-type" axons (Kuramoto 2009) to deep layers — primarily
layer 5/3 — of M1 and premotor cortex. VL also receives Layer-VI
corticothalamic feedback from M1 and modulatory cholinergic, serotonergic,
and noradrenergic input.

VL is anatomically distinct from VA: VA receives basal-ganglia GABAergic
input and projects diffusely to layer 1 (matrix), whereas VL receives
cerebellar excitatory input and projects in a topographic, focal pattern
to deep cortical layers (core). VL is the canonical "motor-tuning"
thalamus: cerebellar output via VL refines the timing and metrics of
voluntary movement (Asanuma 1983; Strick canon).

KEY FINDINGS
============
1. Cerebellar DCN→VL→motor cortex anatomical demonstration in monkey
   [Asanuma C 1983, Brain Res Rev 5:237, doi:10.1016/0165-0173(83)90015-2]
2. Two-type thalamocortical projection — core (VL) cells target deep cortex
   [Kuramoto E 2009, Cereb Cortex 19:2065, doi:10.1093/cercor/bhn231]
3. Convergent / segregated cerebellar vs basal-ganglia inputs in motor thalamus
   [Sakai ST 1996, Neurosci Lett 215:13, doi:10.1016/0304-3940(96)12947-X]
4. VL inactivation impairs reach-grasp kinematics in primates
   [Vitek JL 1994, J Neurophysiol 72:1929, doi:10.1152/jn.1994.72.4.1929]
5. Cerebellar–thalamo–cortical disynaptic loop shown by transsynaptic tracing
   [Hoshi E 2005, Nat Neurosci 8:1491, doi:10.1038/nn1544]
6. Optogenetic cerebello-thalamo-cortical activation evokes forelimb movement
   [Gao Z 2018, Nature 563:113, doi:10.1038/s41586-018-0633-x]

INPUTS
======
- CerebellarDeepNuclei.dcn_drive (glutamatergic driver from dentate/IP/FN)
- MotorCortex.cortical_drive (Layer-VI corticothalamic feedback)
- ThalamicReticularNucleus.trn_inhibition (intrathalamic GABA)
- LocusCoeruleusCore.ne_drive (modulatory NE)
- PedunculopontineCholinergic.ach_drive (modulatory ACh)

OUTPUTS
=======
- vl_drive (0-1)
- m1_deep_layer_signal (0-1) — focal core projection to M1 L5/3
- premotor_signal (0-1)
- motor_tuning_signal (0-1) — fine timing component
- vl_state (str): "tuning_active" | "burst" | "tonic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VentralLateralThalamus(BrainMechanism):
    """VL — cerebellar recipient motor thalamic relay (motor tuning)."""

    BASELINE = 0.09
    SMOOTH = 0.22
    BURST_THRESHOLD = 0.55
    TUNE_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="VentralLateralThalamus",
            human_analog="Ventral lateral thalamic nucleus (VL)",
            layer="subcortical",
        )
        self.state.setdefault("vl_drive", self.BASELINE)
        self.state.setdefault("m1_deep_layer_signal", 0.0)
        self.state.setdefault("premotor_signal", 0.0)
        self.state.setdefault("motor_tuning_signal", 0.0)
        self.state.setdefault("vl_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("burst_count", 0)
        self.state.setdefault("tick_count", 0)

    # ---- helper sub-signals ----

    def _cerebellar_driver(self, dcn: float) -> float:
        """Cerebellar deep-nuclei driver input (Asanuma 1983).

        Cerebellar boutons are large proximal driver synapses on VL
        relay cells; firing reliably evokes thalamocortical spikes.
        """
        if dcn <= 0.0:
            return 0.0
        # Sigmoidal saturation; supralinear at low input
        return min(1.0, dcn * 1.15)

    def _drive_target(self, dcn: float, ctx: float,
                      trn: float, ne: float, ach: float) -> float:
        """Composite VL drive (Sherman 2007 driver/modulator)."""
        excitation = (self.BASELINE
                      + dcn * 0.55
                      + ctx * 0.20
                      + ne * 0.08
                      + ach * 0.07)
        inhibition = trn * 0.40
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _burst_mode(self, drive: float, dcn: float, ne: float) -> float:
        """Burst-mode firing — phasic high cerebellar input + low NE.

        Thalamic burst firing requires hyperpolarization (low arousal,
        low NE) followed by strong excitation. During movement the
        relay mode is tonic; at rest with sudden DCN input bursts can
        emerge.
        """
        if dcn < 0.45:
            return 0.0
        if ne > 0.55:
            return 0.0
        return min(1.0, dcn * (1.0 - ne) * 1.2)

    def _m1_deep_signal(self, drive: float, dcn: float) -> float:
        """Core-type focal projection to M1 deep layers (Kuramoto 2009)."""
        if drive < 0.12:
            return 0.0
        return min(1.0, drive * 0.6 + dcn * 0.3)

    def _premotor_signal(self, drive: float, ctx: float) -> float:
        """Projection to premotor / SMA — slightly attenuated."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.45 + ctx * 0.25)

    def _motor_tuning(self, drive: float, dcn: float, ach: float) -> float:
        """Timing/metric tuning signal (Vitek 1994; Gao 2018)."""
        return min(1.0, drive * 0.4 + dcn * 0.4 + ach * 0.2)

    def _classify_state(self, drive: float, dcn: float,
                         burst: float, ach: float) -> str:
        if drive < 0.13:
            return "quiet"
        if burst > self.BURST_THRESHOLD:
            return "burst"
        if dcn > self.TUNE_THRESHOLD or ach > 0.40:
            return "tuning_active"
        return "tonic"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dcn_data = prior.get("CerebellarDeepNuclei", {})
        if not dcn_data:
            dcn_data = prior.get("DeepCerebellarNuclei", {})
        dcn = float(dcn_data.get("dcn_drive",
                          dcn_data.get("dentate_output",
                              dcn_data.get("cerebellar_output", 0.0))))

        ctx_data = prior.get("MotorCortex", {})
        if not ctx_data:
            ctx_data = prior.get("PrimaryMotorCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                          ctx_data.get("m1_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition",
                          trn_data.get("trn_drive", 0.0)))

        ne_data = prior.get("LocusCoeruleusCore", {})
        if not ne_data:
            ne_data = prior.get("LocusCoeruleus", {})
        ne = float(ne_data.get("ne_drive",
                         ne_data.get("noradrenergic_signal", 0.0)))

        ach_data = prior.get("PedunculopontineCholinergic", {})
        ach = float(ach_data.get("ach_drive", 0.0))

        dcn_eff = self._cerebellar_driver(dcn)
        target = self._drive_target(dcn_eff, ctx, trn, ne, ach)
        prev_drive = float(self.state.get("vl_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        burst = self._burst_mode(new_drive, dcn_eff, ne)
        m1 = self._m1_deep_signal(new_drive, dcn_eff)
        pm = self._premotor_signal(new_drive, ctx)
        tune = self._motor_tuning(new_drive, dcn_eff, ach)

        state = self._classify_state(new_drive, dcn_eff, burst, ach)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        burst_count = int(self.state.get("burst_count", 0))
        if state == "burst":
            burst_count += 1

        self.state["vl_drive"] = round(new_drive, 4)
        self.state["m1_deep_layer_signal"] = round(m1, 4)
        self.state["premotor_signal"] = round(pm, 4)
        self.state["motor_tuning_signal"] = round(tune, 4)
        self.state["vl_state"] = state
        self.state["recent_states"] = recent
        self.state["burst_count"] = burst_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vl_drive": round(new_drive, 4),
            "m1_deep_layer_signal": round(m1, 4),
            "premotor_signal": round(pm, 4),
            "motor_tuning_signal": round(tune, 4),
            "vl_state": state,
        }

    def _burst_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("burst_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vl_drive", 0.0),
            "m1": self.state.get("m1_deep_layer_signal", 0.0),
            "tune": self.state.get("motor_tuning_signal", 0.0),
            "state": self.state.get("vl_state", "quiet"),
        }
