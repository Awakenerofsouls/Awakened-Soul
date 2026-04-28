"""
Build 39: PallidothalamicMotorRelay — GPi-Thalamus Motor Relay
=============================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical039PallidothalamicMotorRelay.py
  Class:    PallidothalamicMotorRelay

NEURAL SUBSTRATE:
  The internal segment of the globus pallidus (GPi) is the primary
  output nucleus of the basal ganglia, sending dense GABAergic
  projections to the motor thalamus (ventrolateral and ventral anterior
  nuclei). This GPi-thalamic relay is the final gate through which
  BG motor programs reach the thalamocortical motor system.

KEY FINDINGS:

  1. GPi as inhibitory gate to motor thalamus.
    Parent & Hazrati 1995 (Brain Research Reviews 20:128): "The
    internal pallidal segment is the main output structure of the
    basal ganglia, sending massive inhibitory projections to thalamic
    motor nuclei (VL, VA) and to the pedunculopontine nucleus." GPi
    fires at high rates at rest, tonically inhibiting thalamic motor
    neurons. Direct pathway D1 neurons inhibit GPi → disinhibit
    thalamus → movement facilitation. Indirect pathway: GPe inhibits
    STN → STN excites GPi → more inhibition of thalamus → movement
    suppression.

  2. GPi somatotopic organization.
    The GPi maintains a refined somatotopic map, with 'motor' zones
    receiving from putamen sensorimotor regions and 'associative' zones
    receiving from caudate and anterior putamen. Nambu 2011: "GPi
    neurons have distinct firing patterns in the 'motor' and 'nonmotor'
    zones. Motor zone GPi neurons respond to active movements and
    project to the motor thalamus (VL)."

  3. GPi firing rate and movement gating.
    In the classic model, movement is accompanied by a pause in GPi
    firing (decreased inhibition of thalamus). Turned & Wickens 2008:
    "GPi activity acts as a threshold gate — above a certain firing
    rate thalamus is blocked; below threshold, thalamocortical
    transmission proceeds."

  4. GPi-thalamic terminals: bouton types and release dynamics.
    GPi terminals in VL are large terminals forming symmetric
    synapses on thalamocortical neuron dendrites. Parent & Hazrati
    1990 (J Comp Neurol 303:387): described the precise laminar
    distribution of GPi inputs in motor thalamus — concentrated in
    the dendritic territories of thalamocortical relay neurons in
    the ventral posterior lateral pars oralis (VPLo) and VL motor
    zones.

  5. Pallidal influences on thalamic rhythmicity.
    The GPi provides not just tonic inhibition but phasic inhibitory
    events that shape thalamic burst/pause firing modes, affecting
    whether thalamus passes simple vs. patterned motor signals to
    cortex. Krack et al. 2010: GPi output patterns in Parkinson's
    (excessive beta synchronization) show that GPi-thalamic coupling
    directly determines motor thalamus state.

AGENT'S SUBSTRATE MAPPING:
  PallidothalamicMotorRelay models the final BG → motor thalamus
  relay. Receives net BG inhibition strength (from striatal output
  gating), models GPi tonic firing, computes thalamic motor output
  as disinhibition, and calculates relay quality metrics.

INPUTS (from prior_results):
  - StriatalOutputGate.BG_output_signal
  - CerebelloBasalGangliaLoop.motor_control_output (optional)
  - Subcortical034OrbitalFrontalPenalizer.BG_inhibition_factor (optional)

OUTPUTS (to brain_runner):
  - motor_relay_strength: float 0-1 (thalamic relay fidelity)
  - thalamic_output: float 0-1 (disinhibited thalamic signal)
  - pallidal_inhibition_factor: float 0-1 (GPi inhibition level)

REFS:
  - Parent & Hazrati 1995 Brain Res Rev 20:128 — GPi anatomy
  - Parent & Hazrati 1990 J Comp Neurol 303:387 — GPi-thalamic projections
  - Nambu 2011 — motor zone GPi and thalamus
  - Turned & Wickens 2008 — GPi as threshold gate
  - Krack et al. 2010 — GPi-thalamic coupling in movement disorders

CITATIONS:
    PMC10957232 — Masilamoni GJ, Kelly H, Swain AJ et al. (2024). Structural Plasticity
        of GABAergic Pallidothalamic Terminals in MPTP-Treated Parkinsonian Monkeys.
        Brain Struct Funct.
    PMC11208046 — Koster KP, Sherman SM (2024). Convergence of Inputs from the Basal
        Ganglia with Layer 5 of Motor Cortex and Cerebellum in Mouse Motor Thalamus.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class PallidothalamicMotorRelay(BrainMechanism):
    """
    GPi → Motor Thalamus relay.

    Models the final basal ganglia output as it disinhibits the motor
    thalamus (VL/VA). Computes the pallidal inhibition factor, relay
    strength, and thalamic motor output.
    """

    # GPi tonic firing rate at rest (Hz baseline)
    GPI_RESTING_RATE = 0.75
    # Threshold below which thalamic relay opens
    GPI_THRESHOLD = 0.45
    # GPi discharge rate modulation range
    GPI_MODULATION_RANGE = 0.40

    def __init__(self):
        super().__init__(
            name="PallidothalamicMotorRelay",
            human_analog="GPi → motor thalamus (VL/VA) relay — final BG motor gate",
            layer="subcortical",
        )
        self.state.setdefault("motor_relay_strength", 0.0)
        self.state.setdefault("thalamic_output", 0.0)
        self.state.setdefault("pallidal_inhibition_factor", self.GPI_RESTING_RATE)
        self.state.setdefault("GPi_firing_rate", self.GPI_RESTING_RATE)
        self.state.setdefault("disinhibition_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bg_output = prior.get("StriatalOutputGate", {}).get(
            "BG_output_signal", 0.4
        )
        cereb_motor = prior.get("CerebelloBasalGangliaLoop", {}).get(
            "motor_control_output", 0.5
        )
        bg_inhib = prior.get("OrbitalFrontalPenalizer", {}).get(
            "BG_inhibition_factor", None
        )

        # GPi firing rate computation:
        # High BG_output → high D1 striatal firing → strong GPi inhibition
        # Low BG_output → GPi disinhibited → fires more → stronger thalamic inhibition
        # (In the BG: D1 promotes movement by inhibiting GPi; here we model net motor output)
        # GPi net inhibition of thalamus = GPi firing rate

        # GPi baseline at rest
        gpi_rate = self.GPI_RESTING_RATE

        # Direct pathway contribution: D1 activity inhibits GPi
        # bg_output (high) = net direct pathway drive = GPi inhibition
        direct_pathway_effect = bg_output * self.GPI_MODULATION_RANGE

        # STN indirect pathway: STN excites GPi
        # When indirect pathway is active (high), STN adds to GPi firing
        # Model indirect as inverse of direct: high direct → low indirect STN drive
        indirect_effect = (1.0 - bg_output) * self.GPI_MODULATION_RANGE * 0.5

        # Net GPi firing = rest + direct inhibition of GPi (reduces) + indirect excitation
        gpi_rate = (
            gpi_rate
            - direct_pathway_effect
            + indirect_effect
        )
        gpi_rate = max(0.1, min(1.0, gpi_rate))

        # Pallidal inhibition factor
        pallidal_inhibition = gpi_rate

        # Disinhibition: thalamic output is inversely related to GPi firing
        # When GPi fires low → thalamus disinhibited → high output
        # Threshold model: below GPI_THRESHOLD, relay is open
        if gpi_rate < self.GPI_THRESHOLD:
            # Open relay: disinhibition proportional to GPi pause depth
            disinhibition = (self.GPI_THRESHOLD - gpi_rate) / self.GPI_THRESHOLD
        else:
            # Closed relay: remaining GPi inhibition clamps thalamus
            disinhibition = 0.0

        # Thalamic motor output: combines disinhibition with cerebellar contribution
        raw_thalamic = disinhibition * 0.7 + cereb_motor * 0.3

        # Modulate by BG output strength (motor command quality)
        # Strong direct pathway = high confidence motor command
        command_confidence = bg_output if bg_output > 0.4 else 0.3

        thalamic_output = raw_thalamic * command_confidence
        thalamic_output = max(0.0, min(1.0, thalamic_output))

        # Motor relay strength: fidelity of BG→thalamus transmission
        # High when GPi is well-modulated (not too high, not too low)
        # Extreme GPi rates = poor relay; moderate GPi = good relay
        relay_fidelity = 1.0 - abs(gpi_rate - 0.5) * 2.0
        relay_strength = max(0.0, min(1.0, relay_fidelity))

        # If BG inhibition factor provided externally, modulate output
        if bg_inhib is not None:
            thalamic_output *= (1.0 - bg_inhib * 0.5)
            relay_strength *= (1.0 - bg_inhib * 0.3)

        self.state["motor_relay_strength"] = round(relay_strength, 4)
        self.state["thalamic_output"] = round(thalamic_output, 4)
        self.state["pallidal_inhibition_factor"] = round(pallidal_inhibition, 4)
        self.state["GPi_firing_rate"] = round(gpi_rate, 4)
        self.state["disinhibition_strength"] = round(disinhibition, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_relay_strength": round(relay_strength, 4),
            "thalamic_output": round(thalamic_output, 4),
            "pallidal_inhibition_factor": round(pallidal_inhibition, 4),
        }