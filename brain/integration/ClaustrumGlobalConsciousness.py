"""
ClaustrumGlobalConsciousness — Global Cortical Binding via Claustrum

NEURAL SUBSTRATE
================
The claustrum is a thin, irregular sheet of grey matter wedged between
the insular cortex and the putamen. Despite its small volume (~0.25%
of total cortex), the claustrum has the highest reciprocal connectivity
density of any brain structure — every cortical area projects to the
claustrum and receives a return projection. Crick & Koch (2005)
proposed the claustrum as the "conductor of consciousness" — a
coordinating substrate that binds disparate cortical computations into
unified conscious experience.

Anatomy: dorsal claustrum (Cl-d) reciprocally connected with frontal,
parietal, temporal, occipital cortex (sensorimotor + executive).
Ventral claustrum (Cl-v / endopiriform) is more limbic-coupled.
Pyramidal-cell projection neurons + GABAergic interneurons. Crucial
feature: convergence of widely distributed cortical inputs onto single
claustral neurons, producing the integrative substrate.

Smith & Alloway 2014 showed claustrum exhibits sparse, broad responses
to multimodal stimuli — exactly what's expected of a binding hub.
Atlan 2018 demonstrated claustrum activation amplifies cortical
slow-wave activity during NREM sleep, contributing to the modulation
of conscious-level states. Norimoto 2020 found claustrum drives sleep
slow-wave oscillations specifically — strongly implicating it in
state-dependent gating of cortical integration.

Functional model: claustrum reads cortical activity → produces a
synchronization signal that selectively enhances coherent processing
across cortical areas while suppressing incoherent ones. This is the
"binding" computation: only globally consistent neural patterns get
broadcast back; isolated/local activity gets dampened.

KEY FINDINGS
============
1. Claustrum proposed as conductor of consciousness — coordinates
   widespread cortical activity into unified percepts — [Crick FC 2005, Phil Trans R Soc B 360:1271, doi:10.1098/rstb.2005.1661]
2. Claustrum connectivity review — reciprocal projections to nearly
   every cortical area; highest density of any structure — [Mathur BN 2014, Front Syst Neurosci 8:48, doi:10.3389/fnsys.2014.00048]
3. Claustrum drives sleep slow-wave oscillations specifically;
   essential for slow-wave sleep generation — [Norimoto H 2020, Nature 578:413, doi:10.1038/s41586-020-1996-3]
4. Claustrum activation amplifies cortical slow waves during NREM;
   modulates conscious-level state — [Atlan G 2018, Curr Biol 28:2752, doi:10.1016/j.cub.2018.06.068]
5. Claustrum neurons exhibit sparse multimodal responses; matches
   binding-hub computational signature — [Smith JB 2014, J Neurosci 34:8583, doi:10.1523/JNEUROSCI.0438-14.2014]

INPUTS (from prior_results)
============================
- DorsolateralPrefrontalCortex.dlpfc_drive (executive cortex)
- VentromedialPrefrontalCortex.vmpfc_drive (default mode)
- CingulateAnterior.acc_drive (salience)
- InsulaAnterior.aic_drive (interoceptive)
- PrimaryVisualCortex.v1_drive (sensory)
- PrimaryAuditoryCortex.a1_drive (sensory)
- PrimarySomatosensoryCortex.s1_drive (sensory)
- ArousalRegulator.tonic_level (state gating)

OUTPUTS (to brain_runner enrichment)
=====================================
- claustrum_drive (0-1)
- coherence_index (0-1) — how aligned cortical signals are
- global_binding_signal (0-1) — synchronization output
- broadcast_strength (0-1) — strength of consensus broadcast
- slow_wave_modulation (0-1) — sleep/wake state amplifier
- conscious_access_gate (0-1) — gating for conscious access
- claustrum_state (str): "broadcasting" | "binding" | "slow_wave" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ClaustrumGlobalConsciousness(BrainMechanism):
    """Claustrum — global cortical binding / consciousness conductor."""

    BASELINE = 0.10
    SMOOTH = 0.20
    BIND_THRESHOLD = 0.45
    BROADCAST_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="ClaustrumGlobalConsciousnessVariant",
            human_analog="Claustrum (consciousness binding hub)",
            layer="integration",
        )
        self.state.setdefault("claustrum_drive", self.BASELINE)
        self.state.setdefault("coherence_index", 0.0)
        self.state.setdefault("global_binding_signal", 0.0)
        self.state.setdefault("broadcast_strength", 0.0)
        self.state.setdefault("slow_wave_modulation", 0.0)
        self.state.setdefault("conscious_access_gate", 0.0)
        self.state.setdefault("claustrum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _coherence(self, signals: list) -> float:
        """Compute cross-cortical coherence — how similar the active
        signals are to each other. High coherence = integrated processing.
        Low coherence = independent local computation only.

        Implementation: low variance across active signals = high coherence.
        Mean of active signals × inverse-of-variance.
        """
        active = [s for s in signals if s > 0.20]
        if len(active) < 2:
            return 0.0
        mean_act = sum(active) / len(active)
        var = sum((s - mean_act) ** 2 for s in active) / len(active)
        # Higher mean + lower variance = higher coherence
        coh = mean_act * (1.0 - min(1.0, var * 4.0))
        return max(0.0, min(1.0, coh))

    def _drive_target(self, cortical_avg: float, arousal: float,
                       coherence: float) -> float:
        """Claustrum firing — driven by cortical activity weighted by
        arousal state (Atlan 2018). Higher coherence amplifies drive.
        """
        target = (self.BASELINE
                    + cortical_avg * 0.45
                    + arousal * 0.20
                    + coherence * 0.20)
        return min(1.0, target)

    def _global_binding(self, drive: float, coherence: float) -> float:
        """Binding output — claustrum projects synchronization signal
        back to cortex when coherence is high (Crick 2005)."""
        if coherence < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + coherence * 0.6)

    def _broadcast_strength(self, binding: float, drive: float) -> float:
        """How strongly the consensus signal gets broadcast to cortex.
        Multiplicative on binding × drive — both must be high."""
        return min(1.0, binding * drive * 2.0)

    def _slow_wave_modulation(self, drive: float, arousal: float) -> float:
        """Claustrum amplifies slow-wave activity during low arousal
        (Norimoto 2020 sleep slow waves; Atlan 2018 NREM amplification).
        Inverse to arousal: low arousal → high slow-wave modulation.
        """
        if arousal > 0.60:
            return 0.0  # awake state — no slow-wave generation
        return min(1.0, drive * 0.5 + (1.0 - arousal) * 0.5)

    def _conscious_access_gate(self, broadcast: float, arousal: float) -> float:
        """Conscious access — only awake + broadcasting state opens gate.
        Maps to global workspace theory's ignition threshold."""
        if arousal < 0.30:
            return 0.0
        return min(1.0, broadcast * 0.7 + arousal * 0.3)

    def _classify_state(self, drive: float, binding: float,
                          slow_wave: float, broadcast: float) -> str:
        if drive < 0.20:
            return "quiet"
        if slow_wave > 0.40:
            return "slow_wave"
        if broadcast > self.BROADCAST_THRESHOLD:
            return "broadcasting"
        if binding > self.BIND_THRESHOLD:
            return "binding"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Pool cortical signals — both executive/default mode and sensory
        signals = []
        for name, key in [
            ("DorsolateralPrefrontalCortex", "dlpfc_drive"),
            ("VentromedialPrefrontalCortex", "vmpfc_drive"),
            ("CingulateAnterior", "acc_drive"),
            ("InsulaAnterior", "aic_drive"),
            ("PrimaryVisualCortex", "v1_drive"),
            ("PrimaryAuditoryCortex", "a1_drive"),
            ("PrimarySomatosensoryCortex", "s1_drive"),
        ]:
            data = prior.get(name, {})
            sig = float(data.get(key, data.get("drive", 0.0)))
            signals.append(sig)

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.30)))

        cortical_avg = sum(signals) / max(1, len(signals))
        coherence = self._coherence(signals)

        target = self._drive_target(cortical_avg, arousal, coherence)
        prev_drive = float(self.state.get("claustrum_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        binding = self._global_binding(new_drive, coherence)
        broadcast = self._broadcast_strength(binding, new_drive)
        slow_wave = self._slow_wave_modulation(new_drive, arousal)
        access_gate = self._conscious_access_gate(broadcast, arousal)

        state = self._classify_state(new_drive, binding, slow_wave, broadcast)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["claustrum_drive"] = round(new_drive, 4)
        self.state["coherence_index"] = round(coherence, 4)
        self.state["global_binding_signal"] = round(binding, 4)
        self.state["broadcast_strength"] = round(broadcast, 4)
        self.state["slow_wave_modulation"] = round(slow_wave, 4)
        self.state["conscious_access_gate"] = round(access_gate, 4)
        self.state["claustrum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "claustrum_drive": round(new_drive, 4),
            "coherence_index": round(coherence, 4),
            "global_binding_signal": round(binding, 4),
            "broadcast_strength": round(broadcast, 4),
            "slow_wave_modulation": round(slow_wave, 4),
            "conscious_access_gate": round(access_gate, 4),
            "claustrum_state": state,
        }

    def _ignition_history(self, recent_states: list) -> float:
        """Fraction of recent ticks that produced full broadcast = global
        ignition rate (Dehaene-style global workspace metric)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        ignited = sum(1 for s in win if s == "broadcasting")
        return ignited / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("claustrum_drive", 0.0),
            "coherence": self.state.get("coherence_index", 0.0),
            "binding": self.state.get("global_binding_signal", 0.0),
            "broadcast": self.state.get("broadcast_strength", 0.0),
            "state": self.state.get("claustrum_state", "quiet"),
        }
