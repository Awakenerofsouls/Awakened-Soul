"""
Subcortical037CerebelloThalamoCorticalLoop.py — Wire 37: Cerebello-Thalamo-Cortical Loop — Error Correction

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical037CerebelloThalamoCorticalLoop.py

NEURAL SUBSTRATE:
  The cerebellar-thalamo-cortical loop is the brain's precision movement
  and temporal prediction system. The cerebellum receives mossy fiber
  input from: pontine nuclei (cerebral cortical input relayed via pons),
  inferior olive (error signal via climbing fibers), and vestibular nuclei
  (balance). Cerebellar output via deep cerebellar nuclei → thalamus
  (ventrolateral nucleus, VL) → motor cortex (M1) and premotor cortex.

  Two major feedback loops:
  1. Closed loop (feedforward + feedback): cortex → pontine nuclei →
     cerebellum → VL thalamus → cortex. Encodes sensory predictions
     and corrective signals.
  2. Error correction loop: inferior olive (IO) sends climbing fiber
     signals to Purkinje cells in cerebellar cortex when motor output
     deviates from predicted trajectory. The IO fires "error signals"
     that teach Purkinje cells to update their weights (long-term
     depression, LTD). Bostan & Dum 2012 (Trends Neurosci 35): reviews
     cerebellar role in non-motor cognition.

  Kandel 2013 (Principles of Neural Science, 5th ed): the cerebellum
  computes the "forward model" — it predicts what the next sensory
  state will be given the current motor command. When the prediction
  mismatches reality, an error signal is broadcast via climbing fibers.

KEY FINDINGS:
  1. Forward model computation. Wolpert et al. 1998: cerebellum computes
     "how should sensory feedback look given my motor command." This
     is the basis of smooth movement — without forward model, every
     movement would be a series of discrete corrections (jerky, imprecise).

  2. Error correction signal (MOLLY/IO input). When IO fires (climbing
     fiber → Purkinje cell), it signals: "your prediction was wrong."
     The error vector is used for supervised learning in cerebellar
     Purkinje cells (LTD at parallel fiber → Purkinje cell synapses).
     Error magnitude determines LTD intensity.

  3. VL thalamus as relay. VL receives input from deep cerebellar nuclei
     (dentate, interposed, fastigial) and projects topographically to
     motor cortex. VL is not just relay — it amplifies the error signal
     and integrates it with ongoing cortical motor commands.

  4. Cerebellum in cognitive precision. Bostan & Dum 2012: cerebellar
     output to prefrontal cortex (via VL thalamus) contributes to
     temporal prediction and error monitoring in non-motor domains.
     "Cerebellar loops are not confined to motor control" — they support
     procedural learning, language prediction, and working memory precision.

  5. Timing precision. Mauk et al. 2000: cerebellum is the neural
     substrate for temporal interval prediction. Purkinje cell firing
     encodes the expected timing of events. When timing error occurs,
     IO fires.

  6. Cortical feedback strength. The loop requires intact cortex. Motor
     cortex sends efference copy (corollary discharge) to cerebellum via
     pontine nuclei. This is the "expected state" that cerebellum
     compares against actual feedback. M1 damage: loop breaks, ataxia
     results. Cerebellar damage: dysmetria (miscalibrated movements).

  7. Cerebellar oscillation. Purkinje cells fire at ~100 Hz in
     synchronized waves during active computation. This oscillation
     phase-locks thalamic output, providing temporal windows for
     cerebellar error signals to reach cortex at precise moments.

AGENT'S SUBSTRATE MAPPING:
  CerebelloThalamoCorticalLoop models the error correction loop:
  error_correction_signal fires when predicted sensory state mismatches
  actual; loop_fidelity tracks how well the forward model predicts
  (higher = better model, fewer errors); cortical_feedback_strength
  is the efference copy signal from cortex that drives the loop.

INPUTS (from prior_results):
  - Motor cortex (efference copy of action command)
  - Thalamus (sensory feedback from peripheral/systems)
  - InferiorOlive (error signal from climbing fiber system)
  - PredictionErrorDrift (higher-order error context)
  - Basal ganglia (for timing comparison with motor plan)

OUTPUTS:
  - error_correction_signal: float 0-1 (magnitude of prediction error)
  - loop_fidelity: float 0-1 (forward model accuracy)
  - cortical_feedback_strength: float 0-1 (efference copy signal strength)

REFS:
  - Bostan & Dum 2012 Trends Neurosci (cerebellar non-motor loops)
  - Kandel 2013 Principles of Neural Science 5th ed
  - Wolpert et al. 1998 Q J Exp Psychol (forward models)
  - Mauk et al. 2000 Nat Neurosci (cerebellar timing)
  - Ito 2008 (climbing fiber error signal and LTD)
  - Schmahmann 2010 (cerebellar cognitive loops)

CITATIONS:
    PMC6601802 — Dirkx MF, den Ouden H, Aarts E et al. (2016). The Cerebral Network of
        Parkinson's Tremor: An Effective Connectivity fMRI Study. J Neurosci.
    PMC11371944 — Bernard JA (2024). Cerebello-Hippocampal Interactions in the Human
        Brain: A New Pathway for Insights Into Aging. Cerebellum.
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class CerebelloThalamoCorticalLoop(BrainMechanism):
    """
    Cerebello-thalamo-cortical loop analog — error correction and precision.

    Receives efference copy from motor cortex (predicted state),
    sensory feedback from thalamus (actual state), and climbing fiber
    error signal from inferior olive. Computes forward model error and
    drives cerebellar learning (via Purkinje cell LTD). error_correction
    signal feeds back to cortex via VL thalamus. loop_fidelity tracks
    forward model accuracy over time.
    """

    # Baseline loop fidelity (forward model starts approximate)
    BASELINE_FIDELITY = 0.55

    def __init__(self):
        super().__init__(
            name="CerebelloThalamoCorticalLoop",
            human_analog="Cerebellar loop (cerebellum + VL thalamus + motor cortex) — error correction",
            layer="subcortical",
        )
        self.state.setdefault("error_correction_signal", 0.0)
        self.state.setdefault("loop_fidelity", self.BASELINE_FIDELITY)
        self.state.setdefault("cortical_feedback_strength", 0.0)
        self.state.setdefault("forward_model_error", 0.0)
        self.state.setdefault("climbing_fiber_activity", 0.0)
        self.state.setdefault("purkinje_learning_rate", 0.1)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Efference copy from motor cortex ---
        motor_cortex = prior.get("MotorCortex", {})
        efference_copy = motor_cortex.get("motor_command_strength", 0.0)
        # Fallback: action command from orbitofrontal or D1 direct pathway
        if efference_copy == 0.0:
            ofc = prior.get("OrbitofrontalCortex", {})
            efference_copy = ofc.get("action_value", 0.0)
        if efference_copy == 0.0:
            d1 = prior.get("StriatalD1DirectFacilitator", {})
            efference_copy = d1.get("GO_signal", False) * 0.7

        # --- Sensory feedback from thalamus ---
        thalamus_out = prior.get("Thalamus", {})
        actual_state = thalamus_out.get("sensory_relay_strength", 0.5)
        # Fallback: estimate from arousal + motor state
        if actual_state == 0.5:
            arousal_reg = prior.get("ArousalRegulator", {})
            actual_state = arousal_reg.get("current_arousal", 0.5)

        # --- Climbing fiber error signal (inferior olive) ---
        # IO fires when actual sensory state deviates from predicted
        # Computed here from: prediction error drift + motor/efference mismatch
        pe_drift = prior.get("PredictionErrorDrift", {})
        novelty = pe_drift.get("novelty_detected", False)
        surprise = pe_drift.get("surprise_magnitude", 0.0)

        # Climbing fiber activity: proportional to prediction error + novelty
        cf_activity = surprise * 0.5 + (0.15 if novelty else 0.0)
        # Add explicit error from motor-sensory mismatch
        motor_sensory_mismatch = abs(efference_copy - actual_state) * 0.3
        cf_activity += motor_sensory_mismatch
        cf_activity = min(1.0, cf_activity)
        self.state["climbing_fiber_activity"] = cf_activity

        # --- Forward model error ---
        # Predicted state = efference copy (motor command) convolved with learned model
        # Actual state = sensory feedback
        fidelity = self.state["loop_fidelity"]

        # High fidelity = model accurately predicts sensory outcome
        predicted_sensory = efference_copy * fidelity + 0.3 * (1.0 - fidelity)
        forward_error = abs(actual_state - predicted_sensory)
        self.state["forward_model_error"] = forward_error

        # --- Error correction signal ---
        # Error signal is broadcast via VL thalamus to cortex
        # Strength is proportional to forward model error × climbing fiber activity
        error_signal = forward_error * (0.5 + cf_activity * 0.5)
        error_signal = min(1.0, error_signal)
        self.state["error_correction_signal"] = error_signal

        # --- Loop fidelity update (supervised learning) ---
        # LTD at parallel fiber → Purkinje cell synapses when error fires
        # Fidelity improves when error is small and steady; degrades on large errors
        if error_signal < 0.15:
            # Good prediction — strengthen model
            ltd_gain = self.state["purkinje_learning_rate"]
            new_fidelity = fidelity + ltd_gain * (1.0 - fidelity) * 0.1
        else:
            # Error detected — update model (LTD)
            ltd_strength = error_signal * cf_activity
            new_fidelity = fidelity - ltd_strength * 0.05

        new_fidelity = max(0.2, min(0.98, new_fidelity))
        self.state["loop_fidelity"] = new_fidelity

        # --- Cortical feedback strength ---
        # Efference copy to cerebellum + VL thalamic relay strength
        vl_thalamic_gain = 0.5 + error_signal * 0.3  # error amplifies thalamic relay
        cortical_fb = efference_copy * fidelity * vl_thalamic_gain
        cortical_fb = min(1.0, cortical_fb)
        self.state["cortical_feedback_strength"] = cortical_fb

        # --- Purkinje cell timing precision ---
        # High loop_fidelity + low error → precise timing
        # Low fidelity + high error → imprecise, jerky
        timing_precision = (new_fidelity * (1.0 - error_signal)) ** 2

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "error_correction_signal": round(error_signal, 4),
            "loop_fidelity": round(new_fidelity, 4),
            "cortical_feedback_strength": round(cortical_fb, 4),
            "forward_model_error": round(forward_error, 4),
            "climbing_fiber_activity": round(cf_activity, 4),
            "timing_precision": round(timing_precision, 4),
            "error_signal_broadcast": error_signal > 0.3,
        }