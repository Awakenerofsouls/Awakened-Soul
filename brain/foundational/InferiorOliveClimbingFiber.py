"""
InferiorOliveClimbingFiber — IO / Climbing Fiber Error Signal Generator

NEURAL SUBSTRATE
================
The inferior olive (IO) is a bilateral nucleus in the caudal ventral
medulla — a small folded olive-shaped structure at the rostral medulla.
The sole source of climbing fibers projecting to cerebellar Purkinje
cells. Three subdivisions, each with topographic Purkinje targets:

- **Principal olive (PO)** — projects to lateral cerebellar cortex
  (motor learning of skilled movements)
- **Dorsal accessory olive (DAO)** — projects to vermis
  (postural / axial motor)
- **Medial accessory olive (MAO)** — projects to flocculonodular lobe
  (vestibular + oculomotor)

Each Purkinje cell receives ONE climbing fiber from a SINGLE IO neuron —
the most precise 1:1 mapping in the CNS. Climbing fiber activation
generates the complex spike: a brief barrage of EPSPs producing
Ca-dependent spike + spikelet train in the Purkinje, which drives
long-term depression (LTD) at parallel-fiber-to-Purkinje synapses.

IO neurons are electrically coupled via gap junctions (connexin-36)
forming a syncytial oscillating network. Sub-threshold membrane
oscillations (~5-10 Hz, ~10 mV peak-to-peak) emerge from this coupled
network and drive ~1 Hz complex spike output. The oscillation-reset
mechanism allows precise timing of error signals.

Functionally: IO encodes motor error. When predicted-vs-actual movement
diverges, climbing fiber discharge fires, producing complex spike, which
drives parallel-fiber LTD — reducing future motor command error.

KEY FINDINGS
============
1. IO climbing-fiber discharge encodes motor error signals to cerebellar
   Purkinje cells; complex spike fires at error-detection moments —
   [Kitazawa 1998, Nature 392:494, doi:10.1038/33141]
2. Sub-threshold membrane oscillations in IO neurons (~1-10 Hz) are
   set by gap-junction coupling; isolated cells lose oscillation —
   [Llinas 1986, J Physiol 376:163, PMID 3795075]
3. Complex spike from climbing fiber drives long-term depression at
   parallel-fiber-Purkinje synapses (cerebellar LTD) — basis of
   motor learning — [Ito 2001, Physiol Rev 81:1143, PMID 11427694]
4. IO connexin-36 gap-junction blockade by mefloquine eliminates
   complex-spike rhythm + impairs motor learning —
   [Long 2002, Neuron 36:1057, doi:10.1016/S0896-6273(02)01092-9]
5. IO oscillation phase encodes timing of error signal; reset by
   afferent input — temporal precision basis for cerebellar timing —
   [Welsh 1995, Nature 374:453, PMID 7700354]

INPUTS
======
- RedNucleusMotorCoord.rn_error_signal
- SuperiorColliculusOrient.orienting_error
- VestibularNucleiBalance.vestibular_drive
- CerebellarVestibularNodulus.vor_calibration (feedback for VOR adaptation)
- CerebellarDeepNuclei.fastigial_drive
- HeadMotionProxy.angular_velocity (for VOR-related error)

OUTPUTS
=======
- io_oscillation_phase (0-1) — current phase in 1Hz cycle
- climbing_fiber_burst (0-1) — phasic complex-spike burst
- error_magnitude (0-1) — combined motor-error signal
- pf_ltd_signal (0-1) — parallel-fiber LTD induction signal
- io_state (str): "error_signaling" | "tonic_oscillation" | "quiet"

brain_runner enrichment:
    io = all_results.get("InferiorOliveClimbingFiber", {})
    if io:
        enrichments["brain_io_phase"] = io.get("io_oscillation_phase", 0.0)
        enrichments["brain_climbing_fiber_burst"] = io.get("climbing_fiber_burst", 0.0)
        enrichments["brain_error_magnitude"] = io.get("error_magnitude", 0.0)
        enrichments["brain_pf_ltd"] = io.get("pf_ltd_signal", 0.0)
        enrichments["brain_io_state"] = io.get("io_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class InferiorOliveClimbingFiber(BrainMechanism):
    """IO — climbing-fiber error signal generator with 1Hz oscillation."""

    SMOOTH = 0.30
    PHASE_INCREMENT = 0.10        # 10 ticks per cycle (≈ 1Hz at 100ms ticks)
    BURST_PHASE_GATE = 0.65       # Phase above which bursts can fire
    ERROR_THRESHOLD = 0.30
    LTD_INTEGRATION = 0.35        # LTD signal accumulates with error * burst

    def __init__(self):
        super().__init__(
            name="InferiorOliveClimbingFiber",
            human_analog="Inferior olive (climbing fiber error generator)",
            layer="foundational",
        )
        self.state.setdefault("io_oscillation_phase", 0.0)
        self.state.setdefault("climbing_fiber_burst", 0.0)
        self.state.setdefault("error_magnitude", 0.0)
        self.state.setdefault("pf_ltd_signal", 0.0)
        self.state.setdefault("io_state", "quiet")
        self.state.setdefault("recent_error", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Phase advance — 1Hz oscillation cycle (Llinas 1986)
    # ------------------------------------------------------------------
    def _advance_phase(self, prev_phase: float, error: float) -> float:
        """Advance IO oscillation phase. Error input slightly accelerates
        phase (oscillation reset by afferent input — Welsh 1995)."""
        phase = prev_phase + self.PHASE_INCREMENT + error * 0.05
        # Wrap phase
        return phase % 1.0

    # ------------------------------------------------------------------
    # Error magnitude — combined motor + orienting + VOR error
    # ------------------------------------------------------------------
    def _error_target(self, rn_error: float, sc_error: float,
                       vor_error: float, vestibular: float) -> float:
        """Combined motor-error signal."""
        return min(1.0, rn_error * 0.4 + sc_error * 0.25 + vor_error * 0.25
                    + vestibular * 0.10)

    # ------------------------------------------------------------------
    # Climbing fiber burst (Kitazawa 1998, Welsh 1995)
    # ------------------------------------------------------------------
    def _burst(self, phase: float, error: float) -> float:
        """Complex-spike burst fires when error exceeds threshold AND
        phase is in the upswing portion of the oscillation cycle.
        """
        if error < self.ERROR_THRESHOLD:
            return 0.0
        if phase < self.BURST_PHASE_GATE:
            return 0.0
        # Burst magnitude scales with error above threshold
        return min(1.0, (error - self.ERROR_THRESHOLD) * 2.5)

    # ------------------------------------------------------------------
    # Parallel-fiber LTD induction signal (Ito 2001)
    # ------------------------------------------------------------------
    def _pf_ltd(self, burst: float, recent_error: list) -> float:
        """LTD induction requires complex spike + sustained error.
        Accumulates over recent ticks of paired activity.
        """
        if burst < 0.20:
            return 0.0
        sustained_error = sum(recent_error[-15:]) / max(1, len(recent_error[-15:]))
        return min(1.0, burst * 0.6 + sustained_error * 0.4)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, error: float, burst: float) -> str:
        """Classify IO operating mode."""
        if burst > 0.20:
            return "error_signaling"
        if error > 0.10:
            return "tonic_oscillation"
        return "quiet"

    # ==================================================================
    # tick
    # ==================================================================
    def _sustained_error_window(self, recent_error: list,
                                  window_size: int = 20) -> float:
        """Sustained-error magnitude — average over last N ticks. Used
        for parallel-fiber LTD induction; LTD requires both complex spike
        AND sustained error pairing (Ito 2001).
        """
        if not recent_error:
            return 0.0
        window = recent_error[-window_size:]
        if not window:
            return 0.0
        return sum(window) / len(window)

    def _complex_spike_amplitude(self, error: float, phase: float,
                                   prior_burst: float) -> float:
        """Complex-spike amplitude shaping — IO neuron complex spikes
        have characteristic decrementing spikelet train. Model amplitude
        decay across consecutive bursts within the same oscillation cycle.
        """
        if error < self.ERROR_THRESHOLD:
            return prior_burst * 0.5
        # First burst at error crossing — full amplitude
        # Subsequent bursts within same cycle — decremented
        if prior_burst > 0.30 and phase > 0.4:
            return prior_burst * 0.7  # within-cycle decrement
        return error  # first-burst amplitude

    def _gap_junction_coherence(self, recent_phase: list) -> float:
        """Connexin-36 gap-junction coupling produces phase coherence
        across IO neurons (Long 2002). Stronger coupling = lower phase
        variance.
        """
        if len(recent_phase) < 5:
            return 0.5
        recent = recent_phase[-10:]
        # Phase variance proxy
        avg = sum(recent) / len(recent)
        var = sum((p - avg) ** 2 for p in recent) / len(recent)
        return max(0.0, 1.0 - var * 5.0)

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "phase": self.state.get("io_oscillation_phase", 0.0),
            "burst": self.state.get("climbing_fiber_burst", 0.0),
            "error": self.state.get("error_magnitude", 0.0),
            "ltd": self.state.get("pf_ltd_signal", 0.0),
            "state": self.state.get("io_state", "quiet"),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        rn_data = prior.get("RedNucleusMotorCoord", {})
        rn_error = float(rn_data.get("rn_error_signal", 0.0))

        sc_data = prior.get("SuperiorColliculusOrient", {})
        sc_error = float(sc_data.get("orienting_error", 0.0))

        nodulus = prior.get("CerebellarVestibularNodulus", {})
        vor_calib = float(nodulus.get("vor_calibration", 0.5))
        # VOR error: when calibration is low and head motion is high, error rises
        head_motion = prior.get("HeadMotionProxy", {})
        angular = float(head_motion.get("angular_velocity", 0.0))
        vor_error = max(0.0, abs(angular) * (1.0 - vor_calib))

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.0))

        # --- Error magnitude ---
        error_target = self._error_target(rn_error, sc_error, vor_error, vestibular)
        prev_error = float(self.state.get("error_magnitude", 0.0))
        new_error = prev_error + (error_target - prev_error) * self.SMOOTH

        # --- Phase advance ---
        prev_phase = float(self.state.get("io_oscillation_phase", 0.0))
        new_phase = self._advance_phase(prev_phase, new_error)

        # --- Climbing fiber burst ---
        burst = self._burst(new_phase, new_error)

        # --- Parallel fiber LTD signal ---
        recent_error = list(self.state.get("recent_error", []))
        recent_error.append(round(new_error, 4))
        if len(recent_error) > 60:
            recent_error = recent_error[-60:]
        pf_ltd = self._pf_ltd(burst, recent_error)

        state = self._classify_state(new_error, burst)

        self.state["io_oscillation_phase"] = round(new_phase, 4)
        self.state["climbing_fiber_burst"] = round(burst, 4)
        self.state["error_magnitude"] = round(new_error, 4)
        self.state["pf_ltd_signal"] = round(pf_ltd, 4)
        self.state["io_state"] = state
        self.state["recent_error"] = recent_error
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "io_oscillation_phase": round(new_phase, 4),
            "climbing_fiber_burst": round(burst, 4),
            "error_magnitude": round(new_error, 4),
            "pf_ltd_signal": round(pf_ltd, 4),
            "io_state": state,
        }
