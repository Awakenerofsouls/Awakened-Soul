"""
VentralAnteriorThalamus — VA — basal-ganglia → motor cortex relay

NEURAL SUBSTRATE
================
The ventral anterior nucleus (VA) of the thalamus is the principal
basal-ganglia receiving relay to frontal cortex. VA receives massive
GABAergic input from the internal pallidum (GPi) and substantia nigra
pars reticulata (SNr) via the pallidothalamic and nigrothalamic tracts,
and it projects to layer 1 of supplementary motor area, premotor cortex,
prefrontal cortex, and motor cortex. VA is the canonical "matrix-type"
thalamic nucleus described by Kuramoto et al. 2009 — its axons broadly
arborize in layer 1, contacting apical tufts of pyramidal neurons across
many cortical columns.

Functionally, VA mediates basal-ganglia control of cortical motor and
cognitive sequencing through tonic disinhibition: GPi/SNr tonically
inhibit VA neurons, and pauses in pallidonigral firing release VA
thalamocortical cells to drive cortex. This is the canonical
action-selection / gating circuit (Hikosaka 2000).

KEY FINDINGS
============
1. VA receives GPi/SNr GABAergic drivers and is disinhibited by basal
   ganglia output pauses; this gates cortical motor programs —
   [Hikosaka O 2000, Physiol Rev 80:953, doi:10.1152/physrev.2000.80.3.953]
2. Two-type thalamocortical projection: matrix (VA) cells broadly target
   layer 1 of frontal cortex; core cells target middle layers —
   [Kuramoto E 2009, Cereb Cortex 19:2065, doi:10.1093/cercor/bhn231]
3. Sherman/Guillery driver–modulator framework distinguishes large
   GPi/SNr boutons on proximal dendrites as drivers of VA —
   [Sherman SM 2007, Curr Opin Neurobiol 17:417, doi:10.1016/j.conb.2007.07.003]
4. Pallidothalamic projections form glomerular synapses on proximal
   dendrites and powerfully control VA thalamocortical firing —
   [Bodor AL 2008, J Neurosci 28:3090, doi:10.1523/JNEUROSCI.5266-07.2008]
5. Optogenetic disinhibition of VA from SNr drives behavioural
   approach and movement initiation in mice —
   [Rizzi G 2017, Neuron 93:1141, doi:10.1016/j.neuron.2017.02.026]
6. Lesions of motor thalamus (VA/VL) impair action selection and
   produce akinesia akin to parkinsonism —
   [Canteras NS 1990, Brain Res 513:43, doi:10.1016/0006-8993(90)91086-V]

INPUTS
======
- GlobusPallidusInternal.gpi_output (tonic GABAergic; high = suppression)
- SubstantiaNigraReticulata.snr_output (tonic GABAergic)
- MotorCortex.cortical_drive (Layer-VI corticothalamic feedback)
- PedunculopontineCholinergic.ach_drive (modulatory ACh)
- ThalamicReticularNucleus.trn_inhibition (intrathalamic GABA)

OUTPUTS
=======
- va_drive (0-1) — overall VA thalamocortical activity
- layer1_motor_signal (0-1) — broadcast to motor/premotor layer 1
- prefrontal_layer1_signal (0-1) — broadcast to PFC layer 1
- disinhibition_event (0-1) — phasic GPi/SNr pause = action gate
- gating_state (str): "gated" | "released" | "modulated" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VentralAnteriorThalamus(BrainMechanism):
    """VA — basal-ganglia recipient motor/prefrontal thalamic relay."""

    BASELINE = 0.08
    SMOOTH = 0.22
    RELEASE_THRESHOLD = 0.45
    PFC_GAIN = 0.55
    MOTOR_GAIN = 0.65
    BG_REST = 0.50  # tonic GPi/SNr firing rate proxy

    def __init__(self):
        super().__init__(
            name="VentralAnteriorThalamus",
            human_analog="Ventral anterior thalamic nucleus (VA)",
            layer="subcortical",
        )
        self.state.setdefault("va_drive", self.BASELINE)
        self.state.setdefault("layer1_motor_signal", 0.0)
        self.state.setdefault("prefrontal_layer1_signal", 0.0)
        self.state.setdefault("disinhibition_event", 0.0)
        self.state.setdefault("gating_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("release_count", 0)
        self.state.setdefault("tick_count", 0)

    # ---- helper sub-signals (physiologically motivated) ----

    def _bg_inhibition(self, gpi: float, snr: float) -> float:
        """Combined tonic GABAergic suppression on VA (Hikosaka 2000).

        GPi and SNr provide largely segregated inhibition; their pooled
        output gates VA. Higher value = stronger suppression.
        """
        # take the larger of the two suppressors — they project to
        # partly overlapping VA territories, so pooled max is a fair
        # proxy for net inhibition on a given VA neuron pool.
        pooled = 0.65 * max(gpi, snr) + 0.35 * (gpi + snr) * 0.5
        return min(1.0, pooled)

    def _disinhibition(self, bg: float) -> float:
        """Phasic release when GPi/SNr fall below tonic baseline.

        Action gating in basal-ganglia thalamocortical loops is driven by
        pauses in pallidonigral firing (Hikosaka 2000; Rizzi 2017).
        """
        if bg >= self.BG_REST:
            return 0.0
        # below tonic level: release scales with depth of pause
        depth = (self.BG_REST - bg) / self.BG_REST
        return min(1.0, depth * 1.4)

    def _drive_target(self, bg: float, ctx: float, ach: float,
                      trn: float, release: float) -> float:
        """Composite VA drive (Sherman 2007 driver/modulator).

        Drivers are corticothalamic L6 + disinhibition; modulators are
        ACh (excitatory) and TRN (inhibitory).
        """
        excitation = (self.BASELINE
                      + ctx * 0.32
                      + release * 0.50
                      + ach * 0.15)
        inhibition = bg * 0.55 + trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _motor_layer1(self, drive: float, release: float) -> float:
        """VA matrix-type axons in motor cortex layer 1 (Kuramoto 2009)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * self.MOTOR_GAIN + release * 0.30)

    def _prefrontal_layer1(self, drive: float, release: float,
                            ach: float) -> float:
        """VA broadcast to PFC layer 1; modulated by cholinergic tone."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * self.PFC_GAIN
                        + release * 0.20
                        + ach * 0.10)

    def _classify_state(self, drive: float, bg: float,
                         release: float, ach: float) -> str:
        if drive < 0.12:
            return "quiet"
        if release > self.RELEASE_THRESHOLD:
            return "released"
        if bg > 0.55:
            return "gated"
        if ach > 0.45:
            return "modulated"
        return "modulated" if drive > 0.25 else "gated"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        gpi_data = prior.get("GlobusPallidusInternal", {})
        gpi = float(gpi_data.get("gpi_output",
                          gpi_data.get("gpi_drive",
                              gpi_data.get("inhibitory_output", 0.0))))

        snr_data = prior.get("SubstantiaNigraReticulata", {})
        if not snr_data:
            snr_data = prior.get("SubstantiaNigraPars", {})
        snr = float(snr_data.get("snr_output",
                          snr_data.get("snr_drive", 0.0)))

        ctx_data = prior.get("MotorCortex", {})
        if not ctx_data:
            ctx_data = prior.get("PrimaryMotorCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                          ctx_data.get("m1_drive",
                              ctx_data.get("cortico_thalamic", 0.0))))

        ach_data = prior.get("PedunculopontineCholinergic", {})
        if not ach_data:
            ach_data = prior.get("LaterodorsalTegmentalNucleus", {})
        ach = float(ach_data.get("ach_drive",
                          ach_data.get("cholinergic_signal", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition",
                          trn_data.get("trn_drive", 0.0)))

        bg = self._bg_inhibition(gpi, snr)
        release = self._disinhibition(bg)
        target = self._drive_target(bg, ctx, ach, trn, release)
        prev_drive = float(self.state.get("va_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        motor_l1 = self._motor_layer1(new_drive, release)
        pfc_l1 = self._prefrontal_layer1(new_drive, release, ach)

        state = self._classify_state(new_drive, bg, release, ach)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        release_count = int(self.state.get("release_count", 0))
        if state == "released":
            release_count += 1

        self.state["va_drive"] = round(new_drive, 4)
        self.state["layer1_motor_signal"] = round(motor_l1, 4)
        self.state["prefrontal_layer1_signal"] = round(pfc_l1, 4)
        self.state["disinhibition_event"] = round(release, 4)
        self.state["gating_state"] = state
        self.state["recent_states"] = recent
        self.state["release_count"] = release_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "va_drive": round(new_drive, 4),
            "layer1_motor_signal": round(motor_l1, 4),
            "prefrontal_layer1_signal": round(pfc_l1, 4),
            "disinhibition_event": round(release, 4),
            "gating_state": state,
        }

    def _release_rate(self) -> float:
        """Frequency of disinhibition events — proxy for action gating."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("release_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("va_drive", 0.0),
            "motor_l1": self.state.get("layer1_motor_signal", 0.0),
            "pfc_l1": self.state.get("prefrontal_layer1_signal", 0.0),
            "release": self.state.get("disinhibition_event", 0.0),
            "state": self.state.get("gating_state", "quiet"),
        }
