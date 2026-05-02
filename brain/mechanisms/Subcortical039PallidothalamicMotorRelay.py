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


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

