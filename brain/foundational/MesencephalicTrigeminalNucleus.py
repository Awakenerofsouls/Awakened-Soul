"""
MesencephalicTrigeminalNucleus — MesV / Proprioceptive Primary Afferents
                                  with CNS-Internal Cell Bodies

NEURAL SUBSTRATE
================
Unique CNS structure: pseudounipolar primary sensory neurons with cell
bodies inside the brainstem — the only such case in the entire CNS. All
other primary afferents have their somata in dorsal root ganglia (spinal)
or peripheral cranial ganglia. MesV's somata sit along the trigeminal
mesencephalic tract in dorsolateral midbrain.

Function: carry proprioceptive input from masticatory muscle spindles
(masseter, temporalis) and periodontal ligament mechanoreceptors. Drive
the jaw-jerk reflex via direct synapse onto trigeminal motor nucleus
motoneurons — the only known monosynaptic stretch reflex closed inside
the brainstem rather than spinal cord.

Critical for:
- Bite-force regulation via periodontal feedback
- Jaw-jerk stretch reflex
- Masticatory rhythm support (spindle feedback)
- Jaw-position sense

Clinical: MesV degeneration in ALS contributes to early bulbar symptoms
(masticatory dysfunction, drooling, dysarthria).

KEY FINDINGS
============
1. MesV neurons are pseudounipolar primary afferents with somata
   inside the CNS — sole exception to the dorsal-root-ganglion rule —
   [Lazarov 2002, Prog Neurobiol 66:19, doi:10.1016/S0301-0082(01)00021-1]
2. MesV mediates the monosynaptic jaw-jerk reflex via direct synapse
   onto trigeminal motor nucleus motoneurons —
   [Pang 2009, J Comp Neurol 514:559, PMID 19363806]
3. MesV proprioception from periodontal ligament critical for bite-
   force regulation; periodontal block impairs precise occlusion —
   [Kubota 1962, J Dent Res 41:1033, PMID 13927692]
4. MesV neurons exhibit oscillatory burst firing supporting masticatory
   rhythm generation — [Wu 2001, J Neurophysiol 85:2627, PMID 11387408]
5. MesV degeneration in ALS contributes to early bulbar symptoms —
   [Ferguson 2007, Brain 130:1671, doi:10.1093/brain/awm068]

INPUTS
======
- JawTensionSimulator.masticatory_drive, .bite_force_estimate
- TrigeminalSensoryComplex.trigeminal_input
- ArousalRegulator.tonic_level

OUTPUTS
=======
- mesv_proprioceptive_signal (0-1) — combined spindle + periodontal afferent
- jaw_jerk_reflex_command (0-1) — monosynaptic stretch reflex output
- bite_force_feedback (0-1) — closed-loop bite force signal
- masticatory_rhythm_phase (0-1) — burst-rhythm phase
- mesv_state (str): "active_chewing" | "stretch_reflex" |
  "tonic_proprioception" | "quiet"

brain_runner enrichment:
    mesv = all_results.get("MesencephalicTrigeminalNucleus", {})
    if mesv:
        enrichments["brain_mesv_proprio"] = mesv.get("mesv_proprioceptive_signal", 0.0)
        enrichments["brain_jaw_jerk"] = mesv.get("jaw_jerk_reflex_command", 0.0)
        enrichments["brain_bite_force_fb"] = mesv.get("bite_force_feedback", 0.0)
        enrichments["brain_mesv_state"] = mesv.get("mesv_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MesencephalicTrigeminalNucleus(BrainMechanism):
    """MesV — primary afferent w/ CNS-internal cell bodies; jaw proprioception."""

    BASELINE = 0.10
    SMOOTH = 0.30
    STRETCH_THRESHOLD = 0.30
    PHASE_INCREMENT = 0.10  # masticatory rhythm step per tick

    def __init__(self):
        super().__init__(
            name="MesencephalicTrigeminalNucleus",
            human_analog="Mesencephalic trigeminal nucleus (jaw proprioception)",
            layer="foundational",
        )
        self.state.setdefault("mesv_proprioceptive_signal", 0.0)
        self.state.setdefault("jaw_jerk_reflex_command", 0.0)
        self.state.setdefault("bite_force_feedback", 0.0)
        self.state.setdefault("masticatory_rhythm_phase", 0.0)
        self.state.setdefault("mesv_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Proprioceptive signal (Lazarov 2002, Pang 2009, Kubota 1962)
    # ------------------------------------------------------------------
    def _proprioceptive(self, masticatory: float, bite_force: float,
                          trigeminal: float) -> float:
        """Combined spindle + periodontal afferent signal."""
        return min(1.0, masticatory * 0.45 + bite_force * 0.35
                    + trigeminal * 0.20)

    # ------------------------------------------------------------------
    # Jaw-jerk reflex (Pang 2009)
    # ------------------------------------------------------------------
    def _jaw_jerk(self, bite_force: float, masticatory: float,
                    proprio: float) -> float:
        """Monosynaptic stretch reflex.

        Fires when sudden bite-force or masticatory drive crosses
        threshold — modeled as proprio surge above STRETCH_THRESHOLD.
        """
        signal = max(bite_force, masticatory)
        if signal < self.STRETCH_THRESHOLD:
            return 0.0
        return min(1.0, (signal - self.STRETCH_THRESHOLD) * 1.6)

    # ------------------------------------------------------------------
    # Bite-force feedback (Kubota 1962)
    # ------------------------------------------------------------------
    def _bite_feedback(self, bite_force: float, proprio: float) -> float:
        """Closed-loop bite-force feedback signal.
        Periodontal mechanoreceptor signal scales with applied force.
        """
        return min(1.0, bite_force * 0.7 + proprio * 0.2)

    # ------------------------------------------------------------------
    # Masticatory rhythm phase (Wu 2001)
    # ------------------------------------------------------------------
    def _advance_phase(self, prev_phase: float, masticatory: float) -> float:
        """Phase advances during active chewing only."""
        if masticatory < 0.20:
            return 0.0  # No active chewing → reset phase
        phase = prev_phase + self.PHASE_INCREMENT * (0.5 + masticatory * 0.5)
        return phase % 1.0

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, proprio: float, masticatory: float,
                          jaw_jerk: float) -> str:
        # Prioritize active_chewing for sustained mastication;
        # stretch_reflex is reserved for transient bite-force surges
        # without ongoing chewing (Wu 2001 rhythm context).
        if masticatory > 0.30:
            return "active_chewing"
        if jaw_jerk > 0.20:
            return "stretch_reflex"
        if proprio > 0.10:
            return "tonic_proprioception"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _periodontal_to_motoneuron(self, bite_force: float,
                                     proprio: float) -> float:
        """Periodontal-ligament mechanoreceptor signal projects directly
        onto trigeminal motor nucleus. Bite-force feedback for precise
        occlusion (Kubota 1962).
        """
        return min(1.0, bite_force * 0.65 + proprio * 0.20)

    def _spindle_burst_balance(self, masticatory: float,
                                 bite_force: float) -> float:
        """Balance between muscle-spindle and periodontal afferent input.
        High masticatory drive = spindle dominant; high bite_force =
        periodontal dominant.
        """
        total = masticatory + bite_force
        if total < 0.05:
            return 0.5
        return masticatory / total

    def _is_sustained_chewing(self, recent_states: list,
                                masticatory: float) -> bool:
        """Detect sustained chewing across recent ticks — distinguishes
        ongoing mastication from transient stretch reflexes (Wu 2001).
        """
        if masticatory < 0.30:
            return False
        if not recent_states:
            return False
        recent = recent_states[-10:]
        chewing_count = sum(1 for s in recent
                            if s in ("active_chewing", "stretch_reflex"))
        return chewing_count >= 3

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "proprio": self.state.get("mesv_proprioceptive_signal", 0.0),
            "jaw_jerk": self.state.get("jaw_jerk_reflex_command", 0.0),
            "bite_fb": self.state.get("bite_force_feedback", 0.0),
            "rhythm_phase": self.state.get("masticatory_rhythm_phase", 0.0),
            "state": self.state.get("mesv_state", "quiet"),
        }
    def _bite_dynamic_vs_static(self, bite_force: float,
                                  prev_bite: float) -> str:
        """Distinguish dynamic bite (changing force, jaw-jerk-relevant)
        from static bite (sustained occlusion, periodontal-tonic).
        """
        delta = bite_force - prev_bite
        if abs(delta) > 0.20:
            return "dynamic"
        if bite_force > 0.30:
            return "static_loaded"
        return "unloaded"

    def _masticatory_burst_amplitude(self, masticatory: float,
                                        phase: float) -> float:
        """Burst amplitude during chewing rhythm — peaks at mid-cycle
        (closing phase) per Wu 2001 oscillatory MesV firing.
        """
        if masticatory < 0.20:
            return 0.0
        # Phase 0.4-0.6 = closing/biting peak
        cycle_position = abs(phase - 0.5)
        amplitude_factor = max(0.0, 1.0 - cycle_position * 2.0)
        return min(1.0, masticatory * 0.7 + amplitude_factor * 0.3)


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        jaw = prior.get("JawTensionSimulator", {})
        masticatory = float(jaw.get("masticatory_drive", 0.0))
        bite_force = float(jaw.get("bite_force_estimate", 0.0))

        trig = prior.get("TrigeminalSensoryComplex", {})
        trigeminal = float(trig.get("trigeminal_input", 0.0))

        # --- Proprioceptive signal ---
        proprio_target = self._proprioceptive(masticatory, bite_force, trigeminal)
        prev_proprio = float(self.state.get("mesv_proprioceptive_signal", 0.0))
        new_proprio = self._smooth(prev_proprio, proprio_target)

        # --- Jaw-jerk reflex ---
        jaw_jerk = self._jaw_jerk(bite_force, masticatory, new_proprio)

        # --- Bite force feedback ---
        bite_fb = self._bite_feedback(bite_force, new_proprio)

        # --- Masticatory phase ---
        prev_phase = float(self.state.get("masticatory_rhythm_phase", 0.0))
        new_phase = self._advance_phase(prev_phase, masticatory)

        state = self._classify_state(new_proprio, masticatory, jaw_jerk)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mesv_proprioceptive_signal"] = round(new_proprio, 4)
        self.state["jaw_jerk_reflex_command"] = round(jaw_jerk, 4)
        self.state["bite_force_feedback"] = round(bite_fb, 4)
        self.state["masticatory_rhythm_phase"] = round(new_phase, 4)
        self.state["mesv_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mesv_proprioceptive_signal": round(new_proprio, 4),
            "jaw_jerk_reflex_command": round(jaw_jerk, 4),
            "bite_force_feedback": round(bite_fb, 4),
            "masticatory_rhythm_phase": round(new_phase, 4),
            "mesv_state": state,
        }
