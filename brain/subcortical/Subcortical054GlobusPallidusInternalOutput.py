"""
Subcortical054GlobusPallidusInternalOutput.py — Wire 54: GPi Output

Neural substrate: Globus pallidus internal segment (GPi) — main BG output.

The GPi is the primary output nucleus of the basal ganglia. It receives
input from the striatum (via direct pathway: D1 Go neurons) and from
the subthalamic nucleus (via the hyperdirect pathway), processes these
signals through inhibitory GABAergic neurons, and sends its output
directly to the thalamus (VA/VLo nuclei). The GPi provides tonic
inhibition of thalamic motor nuclei — releasing thalamus from inhibition
is how the basal ganglia facilitate movement.

Parent 1999 mapped the organization of GPi — it has a somatotopic map
where different regions inhibit different thalamic motor nuclei. Hoover
2014 showed that GPi dysfunction is central to Parkinsonian bradykinesia
— excessive GPi output (from overactive STN/indirect pathway) suppresses
thalamic activation and produces movement poverty.

KEY RESEARCH FINDINGS:
1. Tonic inhibition. GPi neurons fire at 60-80 Hz at rest, providing
   continuous GABAergic inhibition to thalamic motor nuclei (VA/VLo).
   This tonic inhibition is what gets lifted (disinhibited) when the
   direct pathway activates — "GPi output provides a brake on movement."

2. Direct vs. indirect pathway effects. Albin et al. 1989: Direct
   pathway (D1 striatum → GPi → thalamus): activation DISINHIBITS
   thalamus → facilitates movement. Indirect pathway (D2 striatum →
   GPe → STN → GPi): activation INCREASES GPi output → suppresses
   thalamus → inhibits movement. These two pathways implement Go/NoGo
   competition at the GPi level.

3. Somatotopic organization. Parent & Hazrati 1995: GPi has multiple
   somatotopic maps in primates — one for skeletomotor, one for oculo-
   motor, one for cognitive. The motor map is organized: leg lateral,
   face medial. This allows selective facilitation of specific body
   parts while inhibiting others.

4. GPi in Parkinson's. Bergman et al. 1990: "PD results from excessive
   inhibitory output from GPi to thalamus." Loss of SNc dopamine removes
   the normal brake on the indirect pathway → GPe activity drops →
   STN activity increases → GPi fires too much → thalamus over-
   inhibited → movement blocked. GPi lidocaine injection in PD model
   restores movement.

5. GPi and thalamic inhibition. The VA/VLo thalamus receives the major
   GPi projection. The GPi→thalamus synapse is GABAergic, with short-
   latency inhibition. Thalamic relay neurons are released from this
   inhibition by direct pathway activation — allowing thalamic burst
   firing that drives cortical motor areas (Baker 1997).

6. Motor brake. GPi's normal function is to suppress competing motor
   programs — acting as a selective brake. When a motor program is
   selected, its GPi inhibition is reduced (via D1 direct pathway),
   while competing programs remain suppressed. This is the "focusing"
   function of the basal ganglia.

7. GPi firing patterns. In PD, GPi neurons show pathologically
   synchronized beta-frequency (13-30 Hz) oscillations — the same
   beta oscillations seen in STN. Levy et al. 2000: "GPi beta 
   synchrony correlates with bradykinesia severity." In dystonia,
   GPi firing is irregular and reduced, leading to excessive
   involuntary movement.

8. Cerebellar input to GPi. Not all GPi input comes from striatum.
   The pars reticulata of substantia nigra (SNr) and cerebellar
   nuclei also project to GPi. The SNr-GPi pathway may integrate
   reward information with motor inhibition.

OUTPUTS:
  GPi_output_strength: float 0-1 — net GPi firing/inhibition level
  thalamic_inhibition_factor: float 0-1 — degree of thalamic suppression
  motor_brake_applied: float 0-1 — how much motor suppression is active

INPUTS:
  direct_pathway_signal: D1 pathway activation (disinhibition)
  indirect_pathway_signal: D2 pathway activation (more inhibition)
  STN_hyperdirect_signal: hyperdirect pathway input (excitatory to GPi)
  motor_selection: current selected motor program

CITATIONS:
    PMC7584254 — Schwab BC, Kase D, Zimnik A et al. (2020). Neural Activity During
        a Simple Reaching Task in Macaques is Counter to Gating and Rebound in
        Basal Ganglia-Thalamic Communication. J Neurosci.
    PMC1738140 — Chang JW, Choi JY, Lee BW et al. (2002). Unilateral Globus Pallidus
        Internus Stimulation Improves Delayed Onset Post-Traumatic Cervical Dystonia.
        J Korean Neurosurg Soc.
"""

from brain.base_mechanism import BrainMechanism


class GlobusPallidusInternalOutput(BrainMechanism):
    """
    GPi internal segment — main basal ganglia output nucleus.

    Integrates direct/indirect/hyperdirect pathway signals, provides
    tonic thalamic inhibition, and implements the motor brake that
    selectively suppresses competing motor programs.
    """

    TONIC_FIRING_RATE = 0.65  # resting GPi output
    DIRECT_PATHWAY_GAIN = -0.70  # direct = disinhibition (negative effect on GPi output)
    INDIRECT_PATHWAY_GAIN = 0.55  # indirect = more inhibition
    HYPERDIRECT_GAIN = 0.45  # hyperdirect = sharp brake
    THALAMIC_INHIBITION_BASE = 0.75  # baseline thalamic suppression
    BRAKE_FOCUS_GAIN = 0.30

    def __init__(self):
        super().__init__(
            name="GlobusPallidusInternalOutput",
            human_analog="Globus pallidus internal segment (GPi) — BG output nucleus",
            layer="subcortical",
        )
        self.state.setdefault("GPi_output_strength", 0.65)
        self.state.setdefault("thalamic_inhibition_factor", 0.75)
        self.state.setdefault("motor_brake_applied", 0.5)
        self.state.setdefault("direct_pathway_activity", 0.0)
        self.state.setdefault("indirect_pathway_activity", 0.0)
        self.state.setdefault("beta_synchrony", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        direct_pathway = input_data.get("direct_pathway_signal", 0.3)
        indirect_pathway = input_data.get("indirect_pathway_signal", 0.3)
        STN_signal = input_data.get("STN_hyperdirect_signal", 0.2)
        motor_selection = input_data.get("motor_selection", 0.5)
        parkinsonian_factor = input_data.get("parkinsonian_factor", 0.0)

        # --- Pathway integration ---
        # GPi output = tonic base + indirect contribution - direct contribution + STN
        # Direct pathway reduces GPi output (disinhibition)
        direct_effect = direct_pathway * self.DIRECT_PATHWAY_GAIN
        # Indirect pathway increases GPi output (more inhibition)
        indirect_effect = indirect_pathway * self.INDIRECT_PATHWAY_GAIN
        # Hyperdirect (STN) sharpens the brake sharply
        hyperdirect_effect = STN_signal * self.HYPERDIRECT_GAIN
        # Parkinsonian factor: reduces DA → overactive indirect → excessive GPi
        PD_effect = parkinsonian_factor * 0.3

        raw_output = (
            self.TONIC_FIRING_RATE
            + direct_effect
            + indirect_effect
            + hyperdirect_effect
            + PD_effect
        )
        GPi_output_strength = max(0.0, min(1.0, raw_output))

        # --- Thalamic inhibition ---
        # GPi's GABAergic output to VA/VLo determines thalamic activity
        # High GPi = high thalamic inhibition = movement blocked
        thalamic_inhibition = self.THALAMIC_INHIBITION_BASE * GPi_output_strength
        thalamic_inhibition_factor = max(0.0, min(1.0, thalamic_inhibition))

        # Thalamic disinhibition: when direct pathway fires, GPi goes down,
        # thalamus gets released. Compute effective thalamic freedom.
        thalamic_freedom = 1.0 - thalamic_inhibition_factor
        release_benefit = thalamic_freedom * direct_pathway
        effective_thalamic_inhibition = thalamic_inhibition_factor - release_benefit * 0.3

        # --- Motor brake ---
        # The motor brake is the difference between GPi activity and
        # how much a given motor program is selected (released from inhibition)
        # If GPi_output is high AND motor_selection is low → strong brake
        # If motor_selection is high → motor program released from inhibition
        brake_strength = GPi_output_strength * (1.0 - motor_selection)
        # Focus: brake is sharper when competing programs exist
        competing_programs = 1.0 - motor_selection
        focused_brake = brake_strength * (1.0 + self.BRAKE_FOCUS_GAIN * competing_programs)
        motor_brake_applied = max(0.0, min(1.0, focused_brake))

        # --- Beta oscillations (PD marker) ---
        # Excessive synchronized beta in GPi is a PD biomarker
        beta_osc = (self.state["tick_count"] * 20.0 / 60.0) % 1.0
        beta_wave = 0.5 * (1.0 + (1.0 if beta_osc < 0.5 else -1.0))
        beta_synchrony = beta_wave * GPi_output_strength * (1.0 + parkinsonian_factor)
        self.state["beta_synchrony"] = max(0.0, min(1.0, beta_synchrony))

        # --- State tracking ---
        self.state["GPi_output_strength"] = GPi_output_strength
        self.state["thalamic_inhibition_factor"] = effective_thalamic_inhibition
        self.state["motor_brake_applied"] = motor_brake_applied
        self.state["direct_pathway_activity"] = direct_pathway
        self.state["indirect_pathway_activity"] = indirect_pathway
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "GPi_output_strength": round(GPi_output_strength, 4),
            "thalamic_inhibition_factor": round(effective_thalamic_inhibition, 4),
            "motor_brake_applied": round(motor_brake_applied, 4),
            "beta_synchrony": round(self.state["beta_synchrony"], 4),
            "thalamic_release_benefit": round(release_benefit, 4),
        }