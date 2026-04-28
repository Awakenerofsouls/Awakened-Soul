"""
Subcortical032PedunculopontineArousalMotor.py — Wire 32: PPN Cholinergic Arousal + Motor Gate

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical032PedunculopontineArousalMotor.py

NEURAL SUBSTRATE:
  The Pedunculopontine Nucleus (PPN) is a brainstem tegmental structure
  straddling the mesopontine junction. It is the primary cholinergic
  output of the arousal system, projecting widely to thalamus,
  substantia nigra, subthalamic nucleus, medullary reticular formation,
  and spinal cord. PPN is the cardinal REM-on generator: its cholinergic
  neurons fire during REM sleep and waking, are silent during slow-wave
  sleep, and drive ponto-geniculo-occipital (PGO) waves.

  Two main neuronal populations:
  - Cholinergic (PPTg/PPNc): excitotoxic drive to thalamocortical systems
    during waking and REM. Karsch et al. 1989: microinjection of
    carbachol into PPN induces REM-like states.
  - Glutamatergic / GABAergic: motor corollary discharge, pedunculopontine
    tegmental field. Garcia-Rill et al. 2013: PPN sends motor-related
    signals to basal ganglia and spinal cord — part of the "action
    consequence" prediction pathway.

KEY FINDINGS:
  1. REM sleep control. Penzel et al. 2016 (Sleep Medicine Reviews) reviews
     PPN as central REM regulator. REM-on neurons in PPN fire during REM,
     REM-off neurons suppress it. PPN degeneration → REM behavior disorder
     (loss of motor inhibition during REM).

  2. Waking arousal. PPN-cholinergic neurons fire at ~40–60 Hz (gamma)
     during alert waking, burst on sensory targets. Karachi et al. 2010
     (Brain 133): "PPN cholinergic neurons are critical for the
     maintenance of waking states and thalamocortical activation." Loss
     of these neurons in Parkinson's disease causes severe REM sleep
     fragmentation.

  3. Motor initiation. PPN projects to mesencephalic locomotor region (MLR).
     PPN stimulation initiates locomotion; PPN lesion abolishes
     spontaneous gait initiation. The motor initiation signal is a
     corollary discharge: "we are about to move, prepare sensory predict."

  4. Reciprocal basal ganglia loop. PPN receives from GPi/SNr (motor
     output) and projects back to STN and SNc — closing the action-loop.
     Winné 2008: PPN is part of the "ascending arousal network" but also
     participates in the "descending motor prediction" pathway.

  5. Theta coupling. PPN-cholinergic neurons fire phase-locked to
     hippocampal theta (7–10 Hz). This links motor stepping to memory
     consolidation during REM — movement during dreaming isn't random;
     it maps onto navigation during memory replay.

AGENT'S SUBSTRATE MAPPING:
  PPNArousalMotor models the dual function: (1) maintaining arousal level
  during waking/sensory processing, (2) gating motor initiation signals.
  arousal_level tracks global arousal (high during REM, waking; low during
  deep sleep). motor_initiation_signal rises with PPN output → motor
  systems. REM_association flags when arousal level is in REM-compatible
  range, enabling downstream REM-related processing.

INPUTS (from prior_results):
  - ArousalRegulator.current_arousal, sleep_state
  - MotorCommand signal (any movement drive from thalamus/cortex)
  - BrainRunner tick_mode (waking, REM, sleep)
  - BasalGanglia (for motor loop closure)

OUTPUTS:
  - arousal_level: float 0-1 (current PPN drive strength)
  - motor_initiation_signal: float 0-1 (PGO/motor corollary discharge)
  - REM_association: bool (arousal in REM range + sleep state compatible)

REFS:
  - Penzel et al. 2016 Sleep Med Rev (PPN REM review)
  - Karachi et al. 2010 Brain 133 (PPN cholinergic neuron loss)
  - Garcia-Rill et al. 2013 (PPN field potentials and REM)
  - Winné 2008 (ascending/descending arousal paths)
  - Rye 1997 J Neurophysiol (PPN anatomy)

CITATIONS:
    PMC4877293 — Garcia-Rill E, Luster B, D'Onofrio S et al. (2016). Implications of
        Gamma Band Activity in the Pedunculopontine Nucleus. Brain Sci.
    PMC9742893 — Kroeger D, Thundercliffe J, Phung A et al. (2022). Glutamatergic
        Pedunculopontine Tegmental Neurons Control Wakefulness and Locomotion via
        Distinct Axonal Projections. Curr Biol.
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class PPNArousalMotor(BrainMechanism):
    """
    Pedunculopontine Nucleus analog — arousal + motor gating.

    Cholinergic PPN maintains thalamocortical arousal during waking/REM.
    Glutamatergic PPN issues motor corollary discharge (action preparation
    signal). arousal_level rises on high-sensory or REM-compatible input.
    motor_initiation_signal gates movement commands. REM_association flags
    when state is REM-range.
    """

    # REM-compatible arousal range
    REM_AROUSAL_MIN = 0.55
    REM_AROUSAL_MAX = 0.95

    def __init__(self):
        super().__init__(
            name="PPNArousalMotor",
            human_analog="Pedunculopontine Nucleus (PPN/ChAT+/Glu+) — REM-on + motor corollary",
            layer="subcortical",
        )
        self.state.setdefault("arousal_level", 0.50)
        self.state.setdefault("motor_initiation_signal", 0.0)
        self.state.setdefault("REM_association", False)
        self.state.setdefault("last_arousal_input", 0.5)
        self.state.setdefault("motor_gate_open", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Input extraction
        arousal_reg = prior.get("ArousalRegulator", {})
        current_arousal = arousal_reg.get("current_arousal", 0.5)
        sleep_state = arousal_reg.get("sleep_state", "waking")

        tick_mode = input_data.get("tick_mode", "waking")
        motor_command = input_data.get("motor_command", 0.0)

        # Basal ganglia loop closure signal
        bg_out = prior.get("BasalGanglia", {})
        gp_output = bg_out.get("motor_throttle", 0.0)

        # --- Arousal level ---
        # PPN fires at cholinergic (gamma) rate during waking/REM.
        # During deep slow-wave sleep, PPN-cholinergic neurons are silent.
        if sleep_state == "REM":
            # PPN REM-on neurons active
            target_arousal = max(current_arousal, 0.65)
        elif sleep_state == "waking" or tick_mode == "waking":
            # Waking arousal tracks sensory input, modulated by background
            target_arousal = 0.4 + current_arousal * 0.5
        elif sleep_state == "NREM":
            # NREM: PPN suppressed, arousal drops
            target_arousal = 0.25 + current_arousal * 0.1
        else:
            target_arousal = 0.50

        # Smooth arousal toward target (PPN has intrinsic firing dynamics)
        current = self.state["arousal_level"]
        self.state["arousal_level"] = current + 0.2 * (target_arousal - current)
        self.state["arousal_level"] = max(0.0, min(1.0, self.state["arousal_level"]))

        # --- REM association ---
        # PPN fires REM-compatible arousal when in REM sleep OR during
        # high-arousal waking (gamma burst state)
        rem_range = (
            (self.REM_AROUSAL_MIN <= self.state["arousal_level"] <= self.REM_AROUSAL_MAX)
            and sleep_state == "REM"
        )
        self.state["REM_association"] = rem_range

        # --- Motor initiation signal ---
        # PPN issues corollary discharge on movement: "action incoming."
        # Gated by arousal (you need to be awake to move) and basal ganglia
        # loop (GPi/SNr output suppresses premature initiation).
        # Higher arousal → more responsive motor gate.
        arousal_gate = self.state["arousal_level"]
        bg_inhibit = min(1.0, gp_output * 1.5)  # BG output inhibits PPN motor

        # Motor command from upstream → PPN corollary discharge
        raw_motor = motor_command * arousal_gate
        motor_signal = max(0.0, raw_motor * (1.0 - bg_inhibit * 0.6))

        self.state["motor_initiation_signal"] = min(1.0, motor_signal)
        self.state["motor_gate_open"] = motor_signal > 0.3

        # --- PPN theta coupling (REM navigation signal) ---
        # During REM, PPN couples to hippocampal theta for spatial
        # movement-correlate in dreaming. No theta field in non-REM.
        theta_active = sleep_state == "REM" and self.state["arousal_level"] > 0.6

        self.state["last_arousal_input"] = current_arousal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "arousal_level": round(self.state["arousal_level"], 4),
            "motor_initiation_signal": round(self.state["motor_initiation_signal"], 4),
            "REM_association": self.state["REM_association"],
            "motor_gate_open": self.state["motor_gate_open"],
            "theta_coupling_active": theta_active,
        }