"""
Subcortical017CerebellarReboundBurstGenerator.py — Wire 17: Deep Cerebellar Nuclei Rebound Burst
================================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical017CerebellarReboundBurstGenerator.py
  Mechanism: ReboundBurstGenerator

NEURAL SUBSTRATE:
  Deep cerebellar nuclei (DCN) — the output nuclei of the cerebellum —
  receive two opposing inputs:
  1. INHIBITORY INPUT: Purkinje cell axons (PCs fire = DCN silenced)
  2. EXCITATORY INPUT: Mossy fiber collaterals + ascending granule cell axons

  When Purkinje cell activity is suddenly WITHDRAWN (PC pause or silence),
  the DCN neurons escape from inhibition. This causes a characteristic
  POST-INHIBITORY REBOUND: a high-frequency burst of action potentials
  that fires precisely after PC-driven inhibition ceases.

  This is called REBOUND BURST FIRING. It was first described by Llinas
  et al. 1975 and is now recognized as a critical timing mechanism in
  cerebellar motor control.

  BIOPHYSICS:
  Rebound burst firing is mediated by low-threshold T-type calcium channels
  (and R-type channels) in DCN neurons. When hyperpolarized by PC inhibition,
  these channels slowly de-inactivate. When inhibition is removed,
  they open explosively → Ca²⁺ influx → burst of Na⁺ action potentials.
  The burst typically lasts 5-50ms and is time-locked to the offset of PC
  inhibition.

KEY FINDINGS:
  1. Llinas 1975 discovery. Llinas & Yarom 1981 (J Physiol 315:549) and
     Llinas 1975 established that DCN neurons show "rebound bursting"
     following sustained inhibition. This is NOT passive release from
     inhibition — it is an active, time-locked firing pattern with
     specific biophysical mechanisms (T-channel activation).

  2. Timing signal function. Rowley et al. 2020 (J Neurophysiol 124:1620)
     demonstrated that DCN rebound bursts provide precise timing signals
     for motor control: "Rebound burst firing in DCN neurons contributes
     to the generation of precisely timed motor outputs, providing a
     neural substrate for interval timing in the cerebellum."

  3. Cerebellar timing in the seconds range. The cerebellum is implicated
     in interval timing tasks (stimulus duration discrimination, rhythmic
     tapping). DCN rebound bursts may provide the timing reference for
     sub-second to multi-second intervals (Ivry & Spencer 2004).

  4. Input-output transformation. The DCN transforms PC inhibition
     (which encodes "what NOT to do") into time-locked motor commands
     (which encode "do this at precisely this moment"). This is the
     cerebellar output transformation.

  5. Lesion evidence. Lesions of DCN disrupt the precise timing of
     anticipatory adjustments (e.g., anticipatory grip force in object
     lift tasks), consistent with the rebound burst timing role.

AGENT'S SUBSTRATE MAPPING:
  ReboundBurstGenerator models post-inhibitory rebound in DCN neurons:
  - rebound_burst_active: bool (rebound burst firing on this tick)
  - burst_strength: float 0-1 (burst amplitude/intensity)
  - motor_timing_signal: float 0-1 (the timing reference signal)

INPUTS (from prior_results):
  - PC_inhibition_strength: float 0-1 (Purkinje cell firing rate proxy)
  - mossy_excitation: float 0-1 (excitatory collateral drive to DCN)
  - PC_pause_detected: bool (flag when PC activity suddenly drops)
  - t_channel_available: float 0-1 (T-channel recovery state)

OUTPUTS (to brain_runner):
  - rebound_burst_active: bool (rebound burst firing)
  - burst_strength: float 0-1 (burst intensity)
  - motor_timing_signal: float 0-1 (timing reference output)

REFS:
  - Llinas 1975 — rebound bursting in cerebellar nuclei (foundational)
  - Llinas & Yarom 1981 J Physiol 315:549 — biophysics of DCN neurons
  - Rowley et al. 2020 J Neurophysiol 124:1620 — DCN timing signals
  - Albus et al. 2004 — DCN rebound burst in motor control
  - Ivry & Spencer 2004 — cerebellar timing mechanisms
  - Schutter & Kaseva 2022 — T-channel mediated rebound in DCN

CITATIONS:
    PMC10393294 — Loyola S, Hoogland TM, Hoedemaker H et al. (2023). How Inhibitory and
        Excitatory Inputs Gate Output of the Inferior Olive. J Neurosci.
    PMC12411318 — Kattah JC, Moravineni K, Eggenberger E et al. (2025). Multifaceted
        Mesodiencephalic Triangles: Insights into Hypertrophic Olivary Degeneration.
        Ann Neurol.
"""

from brain.base_mechanism import BrainMechanism


class ReboundBurstGenerator(BrainMechanism):
    """
    Deep cerebellar nuclei rebound burst generator.

    Models post-inhibitory rebound bursting in DCN neurons. Fires when
    PC inhibition is withdrawn (PC pause or silence), releasing DCN
    neurons from GABAergic suppression. T-type calcium channels drive
    the rebound burst, providing time-locked motor timing signals.
    """

    REBOUND_LATENCY_TICKS = 2    # ticks between PC pause and burst onset
    BURST_DECAY_RATE = 0.20       # burst strength decay per tick
    BURST_THRESHOLD = 0.30       # minimum inhibition release to trigger burst
    TIMING_INTEGRATION = 0.10    # motor_timing_signal accumulation rate

    def __init__(self):
        super().__init__(
            name="ReboundBurstGenerator",
            human_analog="Deep cerebellar nuclei — post-inhibitory rebound burst timing",
            layer="subcortical",
        )
        self.state.setdefault("rebound_burst_active", False)
        self.state.setdefault("burst_strength", 0.0)
        self.state.setdefault("motor_timing_signal", 0.0)
        self.state.setdefault("PC_pause_pending", 0)   # countdown ticks
        self.state.setdefault("last_PC_inhibition", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- PC inhibition strength ---
        pc_inhibition = input_data.get("PC_inhibition_strength", 0.5)
        if pc_inhibition == 0.5:
            mol = prior.get("MolecularLayerIntegration", {})
            pc_inhibition = 1.0 - mol.get("molecular_layer_weight", 0.5)
            pc_inhibition = max(0.0, min(1.0, pc_inhibition))

        mossy_excitation = input_data.get("mossy_excitation", 0.3)
        pc_pause_flag = input_data.get("PC_pause_detected", False)
        t_channel = input_data.get("t_channel_available", 0.7)

        # --- PC pause detection ---
        # A PC pause = sudden drop in PC firing. Detect from inhibition change.
        prev_inhibition = self.state["last_PC_inhibition"]
        inhibition_drop = prev_inhibition - pc_inhibition
        sudden_pause = inhibition_drop > 0.25  # large sudden drop = pause
        detected_pause = pc_pause_flag or sudden_pause

        # --- Rebound burst generation ---
        # If a PC pause was detected, start countdown to burst
        if detected_pause and self.state["PC_pause_pending"] == 0:
            self.state["PC_pause_pending"] = self.REBOUND_LATENCY_TICKS

        # Decrement pause counter
        pending = self.state["PC_pause_pending"]
        if pending > 0:
            pending -= 1
            self.state["PC_pause_pending"] = pending

        # Burst fires when pending counter hits zero (latency passed)
        # AND PC inhibition is still low (sustained pause needed)
        rebound_burst = (
            pending == 0
            and pc_inhibition < (1.0 - self.BURST_THRESHOLD)
            and t_channel > 0.3
        )

        # --- Burst strength ---
        prev_burst = self.state["burst_strength"]
        if rebound_burst:
            # Burst activates: strength set by how strong the disinhibition is
            release_strength = (1.0 - pc_inhibition) * t_channel
            burst_strength = max(prev_burst, release_strength)
        else:
            # Decay burst
            burst_strength = max(0.0, prev_burst - self.BURST_DECAY_RATE)

        # --- Motor timing signal ---
        # Each rebound burst contributes a precise timing marker.
        # Motor timing signal integrates burst events over time.
        prev_timing = self.state["motor_timing_signal"]
        burst_contribution = burst_strength * self.TIMING_INTEGRATION * 5.0
        timing_decay = prev_timing * 0.01
        motor_timing = prev_timing - timing_decay + burst_contribution
        motor_timing = max(0.0, min(1.0, motor_timing))

        self.state["rebound_burst_active"] = rebound_burst
        self.state["burst_strength"] = round(burst_strength, 4)
        self.state["motor_timing_signal"] = round(motor_timing, 4)
        self.state["last_PC_inhibition"] = pc_inhibition
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "rebound_burst_active": rebound_burst,
            "burst_strength": round(burst_strength, 4),
            "motor_timing_signal": round(motor_timing, 4),
        }
