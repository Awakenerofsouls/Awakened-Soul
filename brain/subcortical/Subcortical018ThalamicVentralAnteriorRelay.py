"""
Subcortical018ThalamicVentralAnteriorRelay.py — Wire 18: Thalamic VA Nucleus — Motor Thalamus
============================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical018ThalamicVentralAnteriorRelay.py
  Mechanism: ThalamicVARelay

NEURAL SUBSTRATE:
  The ventral anterior nucleus (VA) is a motor thalamic relay nucleus.
  It is part of the larger ventral tier of the thalamus (VA, VL, VPL,
  VPM) that processes motor and somatosensory information respectively.
  VA sits anterior to VL (ventral lateral nucleus) and receives its
  major inputs from the cerebellar nuclei and the basal ganglia
  (globus pallidus internus).

  VA AS MOTOR THALAMUS:
  VA is the primary thalamic gateway for cerebellar and basal ganglia
  influence on the cerebral cortex. The classic view (Jones 2007,
  Thalamus Vol. II) distinguishes:
  - VLo (VL oral division): cerebellar input, projects to motor cortex (area 4)
  - VA: basal ganglia input, projects to premotor areas (area 6, F3, F6)
  - VA also receives cerebellar output via VL in some species

  More recent work shows VA receives both cerebellar AND basal ganglia
  input — it is a convergence zone for motor-related signals from
  multiple subcortical sources.

  RELAY PROPERTIES:
  Jones 2007 describes VA neurons as "high-frequency relay neurons"
  with burst and tonic firing modes:
  - Tonic mode ( depolarized state): faithful relay of motor commands
  - Burst mode (hyperpolarized state): gating; suppresses relay fidelity
  The transition between modes is controlled by brainstem reticular inputs.

  CORTICAL PROJECTION TARGETS:
  - Premotor cortex (PMC, BA 6)
  - Supplementary motor area (SMA, BA 6)
  - Prefrontal cortex (dorsolateral, BA 9/46) — cognitive motor aspects
  - Some projections to frontal eye fields (via VL)

KEY FINDINGS:
  1. Dual-input convergence. Halassa & Sherman 2019 (Nat Rev Neurosci
     20:489) showed that thalamic relay neurons integrate subcortical
     driver inputs with cortical feedback. VA integrates cerebellar DCN
     output and GPi output — two competing motor signals.

  2. Relay fidelity and thalamocortical gain. The thalamus is not a
     passive relay — it modulates signal strength. Active VS bursting
     modes change relay gain by ~5x. This determines how effectively
     motor commands reach cortex.

  3. GPi input to VA. GPi (globus pallidus internus) sends GABAergic
     projections to VA. High GPi activity = strong VA inhibition =
     VA burst mode = low relay fidelity. This is the "brake" signal
     from basal ganglia to the motor thalamus.

  4. Cerebellar input (via VL). The cerebellar deep nuclei project to
     VL and indirectly to VA via thalamic interneurons. Cerebellar
     signals compete with GPi signals for thalamocortical access.

  5. Cognitive motor functions. VA projections to prefrontal cortex
     (BA 9/46) suggest a role in cognitive aspects of motor control —
     action planning, motor sequence selection, error monitoring.

AGENT'S SUBSTRATE MAPPING:
  ThalamicVARelay models the VA nucleus as a motor thalamic relay:
  - motor_relay_fidelity: float 0-1 (faithfulness of cerebellar/GPi→cortex relay)
  - VA_gating_factor: float 0-1 (thalamic gating — burst vs tonic mode)
  - thalamocortical_motor_signal: float 0-1 (the output motor signal to cortex)

INPUTS (from prior_results):
  - GPi_inhibition: float 0-1 (basal ganglia brake signal to VA)
  - cerebellar_DCN_output: float 0-1 (cerebellar motor command)
  - thalamic_reticular_activity: float 0-1 (TRN modulation, 0=tonic, 1=burst)
  - cortical_feedback: float 0-1 (feedback from motor cortex → thalamus)

OUTPUTS (to brain_runner):
  - motor_relay_fidelity: float 0-1 (relay quality)
  - VA_gating_factor: float 0-1 (gating state)
  - thalamocortical_motor_signal: float 0-1 (motor command to cortex)

REFS:
  - Jones 2007 — Thalamus Vol. II — VA anatomy and connectivity
  - Halassa & Sherman 2019 Nat Rev Neurosci 20:489 — thalamic relay function
  - Person & Perkel 2005 — GPi→thalamus synaptic physiology
  - Sakai et al. 2000 — cerebellar → VL → motor cortex pathway
  - Sommer 2003 — VA and cognitive motor functions
  - McFarland & Haber 2002 — thalamic relay in basal ganglia circuits

CITATIONS:
    PMC6772665 — McFarland NR, Haber SN (2000). Convergent Inputs from Thalamic Motor
        Nuclei and Frontal Cortical Areas to the Dorsal Striatum in the Primate.
        J Neurosci.
    PMC6587977 — Sieveritz B, García-Muñoz M, Arbuthnott GW (2019). Thalamic Afferents
        to Prefrontal Cortices from Ventral Motor Nuclei in Decision-Making.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicVARelay(BrainMechanism):
    """
    Thalamic VA nucleus — motor relay from cerebellum and basal ganglia to cortex.

    Models the VA nucleus as a gated motor thalamic relay:
    - Integrates cerebellar (via VL) and basal ganglia (GPi) input
    - Computes relay fidelity based on TRN mode (tonic vs burst)
    - Outputs motor signal to premotor cortex, SMA, and DLPFC
    """

    GPi_BRAKE_WEIGHT = 0.55     # GPi inhibition dominates VA gating
    CEREBELLAR_WEIGHT = 0.45    # cerebellar motor signal weight
    TONIC_RELAY_BOOST = 1.4     # tonic mode multiplies relay fidelity
    BURST_RELAY_PENALTY = 0.3   # burst mode sharply suppresses relay

    def __init__(self):
        super().__init__(
            name="ThalamicVARelay",
            human_analog="Thalamic VA nucleus — motor thalamus (GPi + cerebellar input relay)",
            layer="subcortical",
        )
        self.state.setdefault("motor_relay_fidelity", 0.5)
        self.state.setdefault("VA_gating_factor", 0.5)
        self.state.setdefault("thalamocortical_motor_signal", 0.0)
        self.state.setdefault("last_gpi", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Extract inputs ---
        gpi_inhibition = input_data.get("GPi_inhibition", 0.4)
        if gpi_inhibition == 0.4:
            gpi = prior.get("GlobusPallidusExternalRegulation", {})
            gpi_inhibition = gpi.get("GPe_inhibition_level", 0.4)

        cerebellar_dcn = input_data.get("cerebellar_DCN_output", 0.4)
        if cerebellar_dcn == 0.4:
            dcns = prior.get("DeepCerebellarNucleiOutput", {})
            rebound = prior.get("ReboundBurstGenerator", {})
            cerebellar_dcn = (
                dcns.get("DCN_output_strength", 0.0) * 0.6
                + rebound.get("motor_timing_signal", 0.0) * 0.4
            )

        trn_activity = input_data.get("thalamic_reticular_activity", 0.3)
        cortical_feedback = input_data.get("cortical_feedback", 0.5)

        # --- VA gating factor ---
        # High GPi inhibition → VA hyperpolarized → burst mode → gating ON
        # Low GPi inhibition → VA depolarized → tonic mode → relay ON
        raw_gating = gpi_inhibition * self.GPi_BRAKE_WEIGHT
        raw_gating += (1.0 - cerebellar_dcn) * self.CEREBELLAR_WEIGHT * 0.3
        gating = max(0.0, min(1.0, raw_gating))

        # TRN activity shifts between burst (1.0) and tonic (0.0) mode
        trn_contribution = trn_activity * 0.3
        gating = gating * 0.7 + trn_contribution * 0.3
        gating = max(0.0, min(1.0, gating))

        # --- Relay fidelity ---
        # Tonic mode (low gating): high fidelity relay
        # Burst mode (high gating): suppressed relay
        if gating < 0.4:
            relay_fidelity = (0.4 - gating) / 0.4 * self.TONIC_RELAY_BOOST
        else:
            relay_fidelity = self.BURST_RELAY_PENALTY * (1.0 - gating)

        relay_fidelity = max(0.0, min(1.0, relay_fidelity))

        # --- Thalamocortical motor signal ---
        # Integrates cerebellar motor signal (scaled by relay fidelity)
        # and cortical feedback (modulatory)
        cereb_contribution = cerebellar_dcn * relay_fidelity
        gpi_brake = (1.0 - gpi_inhibition) * relay_fidelity * 0.3
        feedback_boost = cortical_feedback * 0.15

        motor_signal = cereb_contribution + gpi_brake + feedback_boost
        motor_signal = max(0.0, min(1.0, motor_signal))

        self.state["motor_relay_fidelity"] = round(relay_fidelity, 4)
        self.state["VA_gating_factor"] = round(gating, 4)
        self.state["thalamocortical_motor_signal"] = round(motor_signal, 4)
        self.state["last_gpi"] = gpi_inhibition
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_relay_fidelity": round(relay_fidelity, 4),
            "VA_gating_factor": round(gating, 4),
            "thalamocortical_motor_signal": round(motor_signal, 4),
        }
