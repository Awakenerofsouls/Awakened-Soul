"""
Subcortical019ThalamicVentralLateralMotor.py — Wire 19: ThalamicVLMotorRelay

Motor thalamus — cerebellar input relay to motor/premotor cortex.

Neural analog: Ventral lateral (VL) thalamic nucleus. The VL is the primary
cerebellar-recipient relay for motor cortex. Purkinje cells of the deep
cerebellar nuclei project via the superior cerebellar peduncle (SCP) to VL,
which in turn projects topographically to primary motor (M1), premotor (PMC),
and supplementary motor (SMA) cortices. This is the cerebellar-thalamo-cortical
(Cb-Th-Cx) loop underpinning coordinated movement sequencing.

ANATOMY (Jones 2007):
  - VL receives from: deep cerebellar nuclei (dentate, interposed, fastigial)
    via the decussation of the superior cerebellar peduncle
  - VL sends to: M1 (Brodmann 4), premotor cortex (BA 6), SMA
  - Two subdivisions: VLo (oralis) = cerebellar input zone; VLc = cerebellar/
    basal ganglia convergence zone
  - Receptive field organization: somatotopic, matched to the contralateral body

CEREBELLAR INPUT — what VL relays:
  - Error teaching signals from Purkinje cells (via deep nuclei)
  - Timing signals for coordinated sequences (Purkinje cells fire in
    precisely timed patterns during motor learning)
  - Forward model predictions (cerebellum as internal model of body dynamics)
  - VL amplifies cerebellar signals for cortical consumption

HALASSA & SHERMAN 2019 THALAMIC TYPES:
  First-order relays (first receipt from subcortical): e.g., MGN → V1
  Higher-order relays (first receipt from layer 5 cortex): e.g., layer 5
    motor cortex → VL. This classifies VL as a "higher-order" relay that
    receives corticothalamic input from L5 pyramidal neurons in motor cortex.
  So VL sits at the nexus of BOTH cerebellar input AND cortical feedback.

KEY FUNCTIONS:
  1. Relay strength: strength of VL signal to motor cortex (modulated by
     cerebellar firing rate and current motor state)
  2. Motor input integration: combines cerebellar teaching signals with
     cortical feedback (Cortico-thalamic loop)
  3. Motor cortex signal: drives M1/PMC activation for movement execution

CLINICAL RELEVANCE:
  - VL lesion → cerebellar ataxia (can initiate but cannot coordinate)
  - Deep brain stimulation of VL (and VLp) used for tremor (interrupts
    thalamo-cortical tremor circuits)
  - Cerebellar-thalamic pathway is key target for Parkinson's DBS

REFS:
- Jones 2007 Thalamus Vol I & II (2nd ed.) — definitive VL anatomy
- Halassa & Sherman 2019 Neuron 103:7-19 — first-order vs higher-order taxonomy
- Middleton & Strick 2001 Trends Neurosci — cerebellar output nuclei
- Gao et al. 2018 Nat Neurosci — cerebellar timing for motor sequencing
- Bostan & Strick 2018 J Neurosci — cerebellar-basal ganglia-VL loop

CITATIONS:
    PMC6695568 — Bohne P, Schwarz MK, Herlitze S et al. (2019). A New Projection From
        the Deep Cerebellar Nuclei to the Hippocampus via the Ventrolateral and
        Laterodorsal Thalamus in Mice. Front Neural Circuits.
    PMC12499924 — Lenz FA, Meeker TJ, Saffer MI et al. (2025). Neuroscience of Human
        Ventral Lateral Thalamic Nucleus Related to Movement and Movement Disorders.
        Neuroscientist.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicVentralLateralMotor(BrainMechanism):
    """
    Motor thalamus — cerebellar input relay to M1/premotor cortex.

    Receives cerebellar teaching signals (from deep cerebellar nuclei),
    integrates with cortical feedback from layer 5 motor neurons, and
    relays a processed motor coordination signal to motor cortex.

    This is the VL: highest-fidelity cerebellar relay in the thalamus.
    """

    # Relay parameters
    RELAY_GAIN = 0.80          # VL signal amplification
    CORTICAL_FEEDBACK_WEIGHT = 0.30  # Layer 5 cortical influence on VL
    MOTOR_BASELINE = 0.25      # Baseline motor readiness
    DECAY_RATE = 0.05           # Signal decay per tick
    MOTOR_THRESHOLD = 0.35     # Threshold for motor_cortex_signal output

    def __init__(self):
        super().__init__(
            name="ThalamicVentralLateralMotor",
            human_analog="Ventral lateral (VL) thalamus — cerebellar motor relay",
            layer="subcortical",
        )
        self.state.setdefault("VL_relay_strength", 0.0)
        self.state.setdefault("cerebellar_motor_input", 0.0)
        self.state.setdefault("motor_cortex_signal", 0.0)
        self.state.setdefault("cortical_feedback_level", 0.0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("cerebellar_history", [])

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Cerebellar deep nuclei output (via SCP decussation)
        # Deep Cerebellar Nuclei Output fires with learned timing signals
        cerebellar_output = prior.get("DeepCerebellarNucleiOutput", {})
        cerebellar_signal = cerebellar_output.get("nuclear_output_strength", 0.0)

        # Source 2: SCP relay (superior cerebellar peduncle)
        scp_relay = prior.get("SuperiorCerebellarPeduncleRelay", {})
        scp_signal = scp_relay.get("SCP_signal_strength", 0.0)

        # Source 3: Purkinje error signals (from cerebellar learning)
        purkinje = prior.get("PurkinjeCellErrorLearning", {})
        purkinje_error = purkinje.get("error_signal_strength", 0.0)

        # Combine cerebellar inputs
        combined_cerebellar = (
            cerebellar_signal * 0.50
            + scp_signal * 0.30
            + purkinje_error * 0.20
        )

        # Source 4: Layer 5 cortical feedback (VL = higher-order relay)
        # Motor cortex L5 sends efference copy back to VL
        cortical_fb = prior.get("CorticothalamicLayer5Feedback", {})
        cortical_strength = cortical_fb.get("layer5_efference_strength", 0.0)

        # VL relay strength: amplified cerebellar input + cortical modulation
        raw_relay = (
            combined_cerebellar * self.RELAY_GAIN
            + cortical_strength * self.CORTICAL_FEEDBACK_WEIGHT
        )
        vl_relay = max(0.0, min(1.0, raw_relay))

        # Motor cortex signal: gated by motor readiness baseline
        # Only fires if VL relay is strong enough
        motor_signal = 0.0
        if vl_relay > self.MOTOR_THRESHOLD:
            motor_signal = max(
                0.0,
                min(1.0, (vl_relay - self.MOTOR_THRESHOLD) * 2.0 + self.MOTOR_BASELINE)
            )

        # Decay VL relay if no strong cerebellar input
        if combined_cerebellar < 0.1:
            vl_relay = max(0.0, vl_relay - self.DECAY_RATE)

        # Update state
        self.state["VL_relay_strength"] = round(vl_relay, 4)
        self.state["cerebellar_motor_input"] = round(combined_cerebellar, 4)
        self.state["motor_cortex_signal"] = round(motor_signal, 4)
        self.state["cortical_feedback_level"] = round(cortical_strength, 4)
        self.state["tick_count"] += 1

        # Track cerebellar history for diagnostic
        hist = list(self.state["cerebellar_history"])
        hist.append(round(combined_cerebellar, 3))
        if len(hist) > 10:
            hist = hist[-10:]
        self.state["cerebellar_history"] = hist

        self.persist_state()

        return {
            "VL_relay_strength": round(vl_relay, 4),
            "cerebellar_motor_input": round(combined_cerebellar, 4),
            "motor_cortex_signal": round(motor_signal, 4),
        }
