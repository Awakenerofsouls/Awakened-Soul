"""
GlobalWorkspaceIntegrator — Global Neuronal Workspace / Conscious Access

NEURAL SUBSTRATE
================
Global Neuronal Workspace Theory (GNWT, Dehaene & Naccache 2001;
Dehaene 2014) proposes that conscious access arises when cortical
processing crosses a threshold of "ignition" — a sudden, late, all-or-
nothing recruitment of widespread frontoparietal and cingulate networks
that broadcasts the contents to the entire cortical workspace. Below
threshold: local processing only (subliminal/preconscious). Above
threshold: globally integrated, reportable, conscious.

The substrate is a network of long-range pyramidal neurons in layer V
of frontal, parietal, and cingulate cortex (Dehaene 1998 model). These
"workspace neurons" form a sparse but globally connected system that
reads from local processors (sensory, memory, motor, value) and
amplifies whichever input crosses ignition threshold, broadcasting it
back across the cortex.

Key empirical signature: the conscious-vs-subliminal contrast (e.g.,
masked stimulus presentation) shows P3b ERP component (~300-500ms),
gamma-band coherence ignition, and frontoparietal BOLD amplification
specifically when stimuli reach awareness — vs no late activity when
they don't.

Mashour 2020 reviewed the GNWT model in connection with consciousness
disorders: anesthesia, vegetative state, and minimally conscious state
all show reduced global workspace ignition.

KEY FINDINGS
============
1. Global workspace theory: conscious access arises from late
   amplification + broadcast across frontoparietal cortex —
   [Dehaene S 2001, Cognition 79:1, doi:10.1016/S0010-0277(00)00123-2]
2. P3b ERP ~300-500ms is the electrophysiological signature of
   conscious access; absent in subliminal trials —
   [Sergent C 2005, Nat Neurosci 8:1391, doi:10.1038/nn1549]
3. Frontoparietal ignition shows nonlinear all-or-nothing dynamics
   above threshold — [Dehaene S 2011, Neuron 70:200, doi:10.1016/j.neuron.2011.03.018]
4. Disorders of consciousness (vegetative, anesthesia) show reduced
   global workspace ignition; loss of long-range coherence —
   [Mashour GA 2020, Neuron 105:776, doi:10.1016/j.neuron.2020.01.026]
5. Workspace ignition correlates with gamma-band long-range
   coherence and increased P3b amplitude —
   [Gaillard R 2009, PLoS Biol 7:e1000061, doi:10.1371/journal.pbio.1000061]

INPUTS (from prior_results)
============================
- ClaustrumGlobalConsciousness.broadcast_strength
- ClaustrumGlobalConsciousness.coherence_index
- DorsolateralPrefrontalCortex.dlpfc_drive
- PosteriorParietalCortex.ppc_drive
- CingulateAnterior.acc_drive
- ArousalRegulator.tonic_level
- Various sensory/limbic mechanisms (any salient signal)

OUTPUTS (to brain_runner enrichment)
=====================================
- workspace_drive (0-1)
- ignition_strength (0-1) — current ignition magnitude
- ignition_threshold_crossed (bool) — boolean ignition event
- broadcast_content_strength (0-1) — what's being broadcast
- p3b_signature (0-1) — late ERP-like marker
- workspace_state (str): "ignited" | "preconscious" | "subliminal" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class GlobalWorkspaceIntegrator(BrainMechanism):
    """Global neuronal workspace — conscious-access ignition coordinator."""

    BASELINE = 0.0
    SMOOTH = 0.20
    IGNITION_THRESHOLD = 0.50  # Dehaene's all-or-nothing threshold
    P3B_LAG_TICKS = 3   # late amplification (proxy for ~300-500ms)

    def __init__(self):
        super().__init__(
            name="GlobalWorkspaceIntegratorVariant",
            human_analog="Global neuronal workspace (Dehaene 2001)",
            layer="integration",
        )
        self.state.setdefault("workspace_drive", 0.0)
        self.state.setdefault("ignition_strength", 0.0)
        self.state.setdefault("ignition_threshold_crossed", False)
        self.state.setdefault("broadcast_content_strength", 0.0)
        self.state.setdefault("p3b_signature", 0.0)
        self.state.setdefault("workspace_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("drive_history", [])
        self.state.setdefault("ignition_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, claustrum_broadcast: float, coherence: float,
                       fp_drive: float, arousal: float,
                       max_signal: float) -> float:
        """Workspace drive — fed by claustrum binding, frontoparietal
        cortex, and the strongest current local signal."""
        # The strongest local signal (the 'content') competes for entry
        target = (claustrum_broadcast * 0.30
                    + coherence * 0.20
                    + fp_drive * 0.25
                    + max_signal * 0.15
                    + arousal * 0.10)
        return min(1.0, target)

    def _ignition(self, drive: float, prev_drive: float) -> float:
        """All-or-nothing ignition (Dehaene 2011 nonlinear dynamics).

        Below threshold: drive grows linearly with input.
        At/above threshold: amplification kicks in, drive jumps to high.
        Hysteresis: once ignited, stays ignited slightly longer than
        input would suggest (positive feedback).
        """
        if drive < self.IGNITION_THRESHOLD:
            # Subthreshold — no ignition amplification
            return drive
        # Above threshold — amplification
        amplified = drive + (drive - self.IGNITION_THRESHOLD) * 0.6
        # Hysteresis: previous ignited state biases toward continued ignition
        if prev_drive > self.IGNITION_THRESHOLD:
            amplified += 0.10
        return min(1.0, amplified)

    def _p3b_signature(self, drive_history: list) -> float:
        """Late amplification signature — looks for sustained ignited
        drive over the last few ticks (proxying the ~300-500ms P3b)."""
        if len(drive_history) < self.P3B_LAG_TICKS:
            return 0.0
        recent = drive_history[-self.P3B_LAG_TICKS:]
        if all(d > self.IGNITION_THRESHOLD for d in recent):
            return min(1.0, sum(recent) / len(recent))
        return 0.0

    def _broadcast_content(self, ignition: float, max_signal: float) -> float:
        """The content being broadcast — only meaningful when ignited."""
        if ignition < self.IGNITION_THRESHOLD:
            return 0.0
        return min(1.0, ignition * 0.5 + max_signal * 0.5)

    def _classify_state(self, drive: float, ignition: float,
                          arousal: float) -> str:
        if arousal < 0.10 or drive < 0.10:
            return "quiet"
        if ignition > self.IGNITION_THRESHOLD:
            return "ignited"
        if drive > 0.30:
            return "preconscious"
        return "subliminal"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cl_data = prior.get("ClaustrumGlobalConsciousness", {})
        cl_broadcast = float(cl_data.get("broadcast_strength", 0.0))
        coherence = float(cl_data.get("coherence_index", 0.0))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive", 0.0))

        ppc_data = prior.get("PosteriorParietalCortex", {})
        ppc = float(ppc_data.get("ppc_drive", 0.0))

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive", 0.0))

        fp_drive = max(dlpfc, ppc, acc)

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        # Find strongest "local" signal — any non-workspace mechanism
        # that could be a candidate for conscious content
        max_signal = 0.0
        for name in ["BasolateralAmygdala", "ValenceTagger",
                       "PrimaryVisualCortex", "PrimaryAuditoryCortex",
                       "InsulaAnterior", "HippocampalCA1Dorsal"]:
            data = prior.get(name, {})
            if not data:
                continue
            for k, v in data.items():
                if isinstance(v, (int, float)) and "drive" in k.lower():
                    max_signal = max(max_signal, float(v))

        target = self._drive_target(cl_broadcast, coherence, fp_drive,
                                       arousal, max_signal)
        prev_drive = float(self.state.get("workspace_drive", 0.0))
        smoothed = self._smooth(prev_drive, target)
        ignition = self._ignition(smoothed, prev_drive)

        # Track history for P3b signature
        history = list(self.state.get("drive_history", []))
        history.append(round(ignition, 4))
        if len(history) > 20:
            history = history[-20:]

        p3b = self._p3b_signature(history)
        broadcast = self._broadcast_content(ignition, max_signal)
        threshold_crossed = ignition > self.IGNITION_THRESHOLD

        state = self._classify_state(smoothed, ignition, arousal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        ignition_count = int(self.state.get("ignition_count", 0))
        if threshold_crossed and prev_drive <= self.IGNITION_THRESHOLD:
            ignition_count += 1  # rising-edge detector

        self.state["workspace_drive"] = round(smoothed, 4)
        self.state["ignition_strength"] = round(ignition, 4)
        self.state["ignition_threshold_crossed"] = threshold_crossed
        self.state["broadcast_content_strength"] = round(broadcast, 4)
        self.state["p3b_signature"] = round(p3b, 4)
        self.state["workspace_state"] = state
        self.state["recent_states"] = recent
        self.state["drive_history"] = history
        self.state["ignition_count"] = ignition_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "workspace_drive": round(smoothed, 4),
            "ignition_strength": round(ignition, 4),
            "ignition_threshold_crossed": threshold_crossed,
            "broadcast_content_strength": round(broadcast, 4),
            "p3b_signature": round(p3b, 4),
            "workspace_state": state,
        }

    def _conscious_access_rate(self, recent: list) -> float:
        """Fraction of recent ticks that were ignited = conscious-access
        rate (Mashour 2020 disorders-of-consciousness metric)."""
        if not recent:
            return 0.0
        win = recent[-50:]
        ignited = sum(1 for s in win if s == "ignited")
        return ignited / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("workspace_drive", 0.0),
            "ignition": self.state.get("ignition_strength", 0.0),
            "p3b": self.state.get("p3b_signature", 0.0),
            "broadcast": self.state.get("broadcast_content_strength", 0.0),
            "state": self.state.get("workspace_state", "quiet"),
        }
