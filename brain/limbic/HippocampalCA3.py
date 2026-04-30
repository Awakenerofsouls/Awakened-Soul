"""
HippocampalCA3 -- CA3 Recurrent Pattern Completion / Sharp-Wave Ripple Generator

NEURAL SUBSTRATE
================
The hippocampal CA3 region sits between dentate gyrus (DG) and CA1 in
the trisynaptic loop. CA3 pyramidal neurons are unique in mammalian
cortex for their dense recurrent collateral system -- each CA3 pyramidal
sends axon collaterals onto thousands of other CA3 pyramidal neurons,
creating an autoassociative recurrent network. This recurrent
architecture is the anatomical substrate for **pattern completion**:
when a partial cue arrives, the recurrent network reactivates the
complete stored pattern through positive feedback.

CA3 receives three principal inputs: (1) mossy fibers from DG granule
cells -- sparse, powerful "detonator" synapses on proximal dendrites
of CA3 pyramidals; (2) perforant path from layer II entorhinal cortex --
direct dense weak input; (3) recurrent CA3-CA3 collaterals -- the
autoassociative engine. Output goes to CA1 via Schaffer collaterals.

The Marr-Treves-Rolls computational framework (Marr 1971; Treves & Rolls
1994) positions CA3 as an autoassociative memory network: storage
through Hebbian plasticity at recurrent synapses, retrieval through
attractor dynamics that converge on the closest stored pattern.
Nakazawa et al. (2002) demonstrated this experimentally -- mice with
CA3-specific NMDAR knockout fail at pattern completion in spatial
memory tasks while showing intact pattern separation, isolating CA3's
specific role.

CA3 is also the principal generator of **sharp-wave ripples (SWRs)**
during quiet wake and NREM sleep -- high-frequency (150-250 Hz)
oscillations during which awake place-cell sequences replay in
compressed form for memory consolidation. CA3 recurrent dynamics
ignite SWRs which then propagate to CA1 and downstream targets via
subiculum.

Beyond memory, CA3 contains place cells with broader, less precise
fields than CA1 -- consistent with autoassociative coarse-coding rather
than CA1's pattern-completed precise coding.

In {{AGENT_NAME}}'s substrate this provides the autoassociative recall engine --
takes DG mossy-fiber input + EC perforant input and emits a
pattern-completed CA3 activity signal feeding CA1, plus a SWR
generator signal during quiet/sleep states.

KEY FINDINGS
============
1. CA3 contains dense recurrent collaterals making it the primary
   autoassociative network of the hippocampus -- substrate for pattern
   completion via attractor dynamics -- [Marr 1971, Philos Trans R Soc
    B 262:23-81, "Simple memory: a theory for archicortex"; Treves
    Rolls 1994, Hippocampus 4:374-391]
2. CA3-specific NMDAR knockout impairs pattern completion of spatial
   memory while sparing pattern separation -- direct experimental
   demonstration of CA3's role -- [Nakazawa et al. 2002, Science
    297:211-218, "Requirement for hippocampal CA3 NMDA receptors in
    associative memory recall"]
3. Mossy fiber synapses from DG granule cells onto CA3 pyramidals are
   "detonator" inputs -- single granule cell can drive CA3 spikes --
   [reviewed Henze Wittner Buzsáki 2002, Nat Neurosci 5:790-795,
    "Single granule cells reliably discharge targets in the hippocampal
    CA3 network in vivo"]
4. CA3 generates sharp-wave ripples -- recurrent excitation produces
   transient population bursts that propagate to CA1; SWR replay
   underlies memory consolidation -- [reviewed Buzsáki 2015,
    Hippocampus 25:1073-1188, "Hippocampal sharp wave-ripple"]
5. CA3 recurrent network operation and plasticity -- comprehensive
   review of CA3 mechanisms -- [Rebola Carta Mulle 2017, Nat Rev
    Neurosci 18:208-220, "Operation and plasticity of hippocampal
    CA3 recurrent networks"]

INPUTS (from prior_results)
============================
- DentateGyrusPatternSep.dg_output
- DentateGyrusPatternSep.mossy_fiber_drive
- DentateGyrusPatternSep.pattern_separation_index
- HippocampalContextProxy.context_id
- HippocampalContextProxy.familiarity
- HippocampalContextProxy.context_novelty
- MedialSeptumTheta.theta_active
- MedialSeptumTheta.theta_amplitude
- ArousalRegulator.tonic_level
- LocomotionProxy.locomotion_speed
- SleepWakeFlipFlop.sleep_wake_state

OUTPUTS (to brain_runner enrichment)
=====================================
- ca3_pyramidal_drive (0.0-1.0): CA3 pyramidal output
- recurrent_completion_strength (0.0-1.0): autoassociative reactivation
- mossy_detonation_active (bool): DG mossy fiber drove CA3 spike
- swr_generator_active (bool): CA3 SWR ignition
- schaffer_relay (0.0-1.0): CA3 → CA1 Schaffer collateral output
- attractor_state (str): "quiescent" | "encoding" | "retrieval" | "swr"
- ca3_state (str): same set, repeated as common state field

brain_runner enrichment:
    ca3 = all_results.get("HippocampalCA3", {})
    if ca3:
        enrichments["brain_ca3_drive"] = ca3.get("ca3_pyramidal_drive", 0.2)
        enrichments["brain_pattern_completion"] = ca3.get("recurrent_completion_strength", 0.0)
        enrichments["brain_schaffer_relay"] = ca3.get("schaffer_relay", 0.0)
        enrichments["brain_swr_generator"] = ca3.get("swr_generator_active", False)
        enrichments["brain_ca3_state"] = ca3.get("ca3_state", "quiescent")
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA3(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="HippocampalCA3",
            human_analog="Hippocampal CA3 recurrent pattern completion / SWR generator",
            layer="foundational",
        )
        self.state.setdefault("ca3_pyramidal_drive", self.BASELINE)
        self.state.setdefault("recurrent_completion_strength", 0.0)
        self.state.setdefault("mossy_detonation_active", False)
        self.state.setdefault("swr_generator_active", False)
        self.state.setdefault("schaffer_relay", 0.0)
        self.state.setdefault("attractor_state", "quiescent")
        self.state.setdefault("ca3_state", "quiescent")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ca3_drive_target(self, mossy: float, dg_out: float, theta_active: bool,
                           theta_amp: float, arousal: float) -> float:
        """CA3 pyramidal drive -- driven by mossy fiber + DG output + theta."""
        target = self.BASELINE + mossy * 0.5 + dg_out * 0.2
        if theta_active:
            target += theta_amp * 0.2
        target += max(0.0, arousal - 0.4) * 0.2
        return min(1.0, target)

    def _recurrent_completion(self, ca3: float, familiarity: float, theta_active: bool) -> float:
        """Autoassociative pattern completion -- Marr/Treves/Rolls.
        Engaged when familiar cue + sufficient CA3 drive + theta state.
        """
        if familiarity < 0.20:
            # Novel context -- DG separation dominates, CA3 doesn't pattern-complete
            return ca3 * 0.2
        # Recurrent dynamics ignite at threshold
        if ca3 < 0.30:
            return 0.0
        target = familiarity * 0.6 + ca3 * 0.3
        if theta_active:
            target += 0.10
        return min(1.0, target)

    def _mossy_detonation(self, mossy: float) -> bool:
        """Mossy fiber detonator -- single strong synapse can drive CA3 spike."""
        return mossy > 0.45

    def _swr_generator(self, ca3: float, sleep_state: str, theta_active: bool,
                        locomotion: float, novelty: float) -> bool:
        """SWR generator -- quiet wake or NREM with sufficient CA3 drive,
        no theta competition, low locomotion. Replay-prone after novel encoding.
        """
        if theta_active or locomotion > 0.20:
            return False
        if sleep_state == "WAKE" and ca3 > 0.45:
            return True
        if sleep_state == "SLEEP" and ca3 > 0.30:
            return True
        # Post-novelty replay biased
        if novelty > 0.50 and ca3 > 0.40:
            return True
        return False

    def _schaffer_relay(self, ca3: float, completion: float, swr: bool) -> float:
        """CA3 → CA1 Schaffer collateral output."""
        if swr:
            return min(1.0, ca3 * 0.95 + completion * 0.3)
        return min(1.0, ca3 * 0.7 + completion * 0.4)

    def _classify_state(self, completion: float, swr: bool, ca3: float,
                          novelty: float) -> str:
        if swr:
            return "swr"
        if completion > 0.45:
            return "retrieval"
        if novelty > 0.50 and ca3 > 0.30:
            return "encoding"
        if ca3 < 0.25:
            return "quiescent"
        return "quiescent"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg = prior.get("DentateGyrusPatternSep", {})
        dg_out = float(dg.get("dg_output", 0.0))
        mossy = float(dg.get("mossy_fiber_drive", 0.0))

        ctx = prior.get("HippocampalContextProxy", {})
        familiarity = float(ctx.get("familiarity", 0.5))
        novelty = float(ctx.get("context_novelty", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))
        theta_amp = float(ms.get("theta_amplitude", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- CA3 pyramidal drive ---
        ca3_target = self._ca3_drive_target(mossy, dg_out, theta_active, theta_amp, tonic)
        prev_ca3 = float(self.state.get("ca3_pyramidal_drive", self.BASELINE))
        new_ca3 = self._smooth(prev_ca3, ca3_target)

        # --- Recurrent pattern completion ---
        completion = self._recurrent_completion(new_ca3, familiarity, theta_active)
        prev_comp = float(self.state.get("recurrent_completion_strength", 0.0))
        new_comp = self._smooth(prev_comp, completion)

        # --- Mossy detonation ---
        detonation = self._mossy_detonation(mossy)

        # --- SWR generator ---
        swr = self._swr_generator(new_ca3, sleep_state, theta_active, locomotion, novelty)

        # --- Schaffer relay ---
        schaffer = self._schaffer_relay(new_ca3, new_comp, swr)

        # --- State ---
        state = self._classify_state(new_comp, swr, new_ca3, novelty)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ca3_pyramidal_drive"] = round(new_ca3, 4)
        self.state["recurrent_completion_strength"] = round(new_comp, 4)
        self.state["mossy_detonation_active"] = detonation
        self.state["swr_generator_active"] = swr
        self.state["schaffer_relay"] = round(schaffer, 4)
        self.state["attractor_state"] = state
        self.state["ca3_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ca3_pyramidal_drive": round(new_ca3, 4),
            "recurrent_completion_strength": round(new_comp, 4),
            "mossy_detonation_active": detonation,
            "swr_generator_active": swr,
            "schaffer_relay": round(schaffer, 4),
            "attractor_state": state,
            "ca3_state": state,
        }
