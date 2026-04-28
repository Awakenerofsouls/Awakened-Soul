"""
Subcortical056StriatalLowThresholdSpikeInterneurons.py — Wire 56: LTS Interneurons

Neural substrate: Striatal low-threshold spiking (LTS) interneurons.

LTS interneurons are a distinct class of striatal GABAergic interneurons
characterized by their low-threshold calcium spikes and slow-spiking
firing pattern (10-20 Hz). They are neuropeptide Y (NPY) positive and
somatostatin (SOM) positive, distinguishing them from FSIs (PV+) and
TANs (choline). Kawaguchi 1993 first characterized them in the rat
striatum; Beatty et al. 2012 demonstrated their role in network
integration and behavioral state modulation.

KEY RESEARCH FINDINGS:
1. Anatomical identity. Kawaguchi 1993: LTS neurons (NPY/SOM+) are
   ∼1% of striatal neurons, with extended dendritic trees spanning
   up to 300 μm. They receive input from cortical pyramidal cells
   (like FSIs) but have slower kinetics and broader integration windows.
   They inhibit MSNs via GABA_A receptors with slower kinetics than
   FSI-mediated IPSCs.

2. Low-threshold calcium spike (LTS). The defining characteristic:
   LTS neurons have a lower threshold for calcium spike generation
   than FSIs. They exhibit a "plateau" afterhyperpolarization and
   can fire at lower depolarization levels. This makes them responsive
   to convergent inputs from multiple cortical areas.

3. Network integration role. Beatty 2012: "LTS neurons integrate
   information across a broader temporal and spatial window than
   FSIs." They act as integrators of behavioral state — their firing
   reflects the integration of multiple concurrent signals (cognitive,
   emotional, motor). This makes them suited for state-dependent
   modulation of striatal output.

4. Slow inhibition and network dynamics. LTS-mediated inhibition has
   a slower time course (50-200 ms decay) compared to FSI (10-30 ms).
   This creates a "slow gating" effect: LTS inhibition can suppress
   MSN firing for hundreds of milliseconds after activation, implementing
   a broad temporal filter. This is important for sustained behavioral
   states (maintaining posture, sustained attention).

5. Integration with cholinergic system. LTS neurons receive input from
   TANs (tonically active cholinergic interneurons). ACh from TANs
   activates muscarinic receptors on LTS neurons, modulating their
   excitability. The cholinergic snapshot (timestamped events in
   the striatum, Apex 2013) can activate LTS neurons, which then
   provide a slow inhibitory gating of MSNs following the cholinergic
   signal — linking reward prediction errors to motor suppression.

6. Behavioral state modulation. LTS neurons fire during sustained
   behavioral states: immobility, sustained attention, grooming
   sequences. Their slow inhibition maintains MSN suppression during
   these states, effectively implementing a "hold" function — 
   "don't move while I'm doing this."

7. Synchrony in theta/alpha band. LTS neurons show rhythmic firing
   in the theta/alpha band (4-14 Hz) during network-level oscillations.
   This is slower than FSI gamma — LTS coordinates slower state
   transitions (e.g., shifting between behavioral modes).

8. NPY modulation. NPY is co-released with GABA from LTS neurons.
   NPY acts on Y1 receptors on MSNs to reduce excitability, providing
   a slower neuromodulatory effect in addition to fast GABAergic
   inhibition.

OUTPUTS:
  LTS_activity: float 0-1 — current LTS interneuron activation
  network_integration_signal: float 0-1 — degree of multi-domain integration
  slow_inhibition_strength: float 0-1 — strength of the slow MSN suppression

INPUTS:
  cortical_convergence: multiple cortical inputs converging
  cholinergic_signal: TAN activity (cholinergic "snapshot")
  behavioral_state: sustained vs. phasic behavioral mode
  emotional_input: limbic/emotional convergence

CITATIONS:
    PMC6507406 — Assous M, Tepper JM (2019). Excitatory Extrinsic Afferents to
        Striatal Interneurons and Interactions With Striatal Microcircuitry.
        Front Syst Neurosci.
    PMC5477498 — Assous M, Kaminer J, Shah F et al. (2017). Differential Processing
        of Thalamic Information Via Distinct Striatal Interneuron Circuits.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class StriatalLowThresholdSpikeInterneurons(BrainMechanism):
    """
    Striatal low-threshold spiking (LTS) interneurons.

    Provide slow, integrative inhibition across striatal MSNs.
    Unlike FSIs (fast, precise), LTS neurons integrate over broader
    temporal/spatial windows and implement slow gating for sustained
    behavioral states.
    """

    LTS_FIRING_RATE = 0.25
    INTEGRATION_WINDOW = 0.40  # temporal window for integration
    SLOW_INHIBITION_TAU = 180.0  # ms decay time for LTS inhibition
    SLOW_DECAY_RATE = 0.015
    THETA_FREQ = 8.0  # Hz — LTS theta rhythm

    def __init__(self):
        super().__init__(
            name="StriatalLowThresholdSpikeInterneurons",
            human_analog="Striatal LTS/NPY/SOM+ interneurons — slow integrative inhibition",
            layer="subcortical",
        )
        self.state.setdefault("LTS_activity", 0.0)
        self.state.setdefault("network_integration_signal", 0.5)
        self.state.setdefault("slow_inhibition_strength", 0.0)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("slow_inhibition_accumulator", 0.0)
        self.state.setdefault("sustained_suppression", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cortical_convergence = input_data.get("cortical_convergence", 0.4)
        cholinergic_signal = input_data.get("cholinergic_signal", 0.3)
        behavioral_state = input_data.get("behavioral_state", "phasic")
        emotional_input = input_data.get("emotional_input", 0.5)
        motor_convergence = input_data.get("motor_convergence", 0.3)

        # --- LTS activation ---
        # LTS fires when multiple convergent inputs sum above threshold
        # (low-threshold = less drive needed to reach spike)
        cortical_contribution = cortical_convergence * 0.35
        cholinergic_contribution = cholinergic_signal * 0.25  # ACh activates LTS via mAChRs
        emotional_contribution = (emotional_input - 0.5) * 0.20  # centered
        motor_contribution = motor_convergence * 0.15

        total_convergence = (
            cortical_contribution
            + cholinergic_contribution
            + emotional_contribution
            + motor_contribution
        )

        # LTS has low threshold — fires at lower activation than FSI
        raw_activity = self.LTS_FIRING_RATE + total_convergence
        LTS_activity = max(0.0, min(1.0, raw_activity))

        # --- Network integration signal ---
        # Network integration is the degree to which multiple domains converge
        # Higher integration = LTS fires more, providing stronger slow inhibition
        integration_composite = (
            cortical_convergence * 0.3
            + (cholinergic_signal > 0.5) * 0.25  # boolean: cholinergic snapshot detected
            + emotional_input * 0.25
            + motor_convergence * 0.20
        )

        # EMA smoothing of integration signal
        new_integration = self.state["network_integration_signal"] * 0.85 + integration_composite * 0.15
        self.state["network_integration_signal"] = max(0.0, min(1.0, new_integration))

        # --- Theta rhythm ---
        # LTS neurons fire in theta band — slower than FSI gamma
        theta_increment = (self.THETA_FREQ / 60.0) * 360.0
        new_theta_phase = (self.state["theta_phase"] + theta_increment) % 360.0
        self.state["theta_phase"] = new_theta_phase

        theta_wave = 0.5 * (1.0 + (1.0 if new_theta_phase < 180 else -1.0))
        theta_modulation = 0.08 * theta_wave

        # --- Slow inhibition ---
        # LTS inhibition is slow (50-200 ms decay) — a sustained effect
        # The slow_inhibition_strength accumulates with LTS firing
        # and decays slowly over time
        if LTS_activity > 0.3:
            inhibition_increment = LTS_activity * 0.08 * (1.0 + theta_modulation)
            new_accumulator = min(1.0, self.state["slow_inhibition_accumulator"] + inhibition_increment)
        else:
            # Decay of slow inhibition
            new_accumulator = self.state["slow_inhibition_accumulator"] * (1.0 - self.SLOW_DECAY_RATE)

        self.state["slow_inhibition_accumulator"] = max(0.0, min(1.0, new_accumulator))

        # Sustained suppression: increases in "sustained" behavioral states
        if behavioral_state == "sustained":
            sustained_delta = 0.03 * LTS_activity
            self.state["sustained_suppression"] = min(
                1.0, self.state["sustained_suppression"] + sustained_delta
            )
        else:
            self.state["sustained_suppression"] *= 0.98

        # Combined slow inhibition strength
        slow_inhibition_strength = (
            self.state["slow_inhibition_accumulator"] * 0.7
            + self.state["sustained_suppression"] * 0.3
        )

        self.state["LTS_activity"] = LTS_activity
        self.state["slow_inhibition_strength"] = slow_inhibition_strength
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "LTS_activity": round(LTS_activity, 4),
            "network_integration_signal": round(new_integration, 4),
            "slow_inhibition_strength": round(slow_inhibition_strength, 4),
            "theta_phase_degrees": round(new_theta_phase, 2),
            "sustained_suppression": round(self.state["sustained_suppression"], 4),
        }