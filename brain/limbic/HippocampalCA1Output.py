"""
HippocampalCA1Output -- CA1 Pyramidal Output / Pattern Completion / Place Coding

NEURAL SUBSTRATE
================
The hippocampal CA1 region is the principal output stage of the
hippocampal trisynaptic loop (entorhinal → DG → CA3 → CA1) and the
source of most extra-hippocampal hippocampal output. CA1 contains
glutamatergic pyramidal neurons (~80%) and diverse GABAergic
interneurons (parvalbumin-, somatostatin-, VIP-, cholecystokinin-
expressing). CA1 pyramidal neurons receive Schaffer collateral input
from CA3, direct entorhinal input via the perforant path (layer III
EC → CA1 stratum lacunosum-moleculare), and modulatory input from
medial septum, locus coeruleus, raphe, and VTA.

CA1 is the principal site of "place cells" -- neurons that fire when
the animal is in a particular spatial location, the foundational
discovery of O'Keefe & Dostrovsky (1971) that won the 2014 Nobel
Prize. Place coding is generated through pattern-completion dynamics
in CA3 → CA1 transmission, allowing partial cue reactivation of
complete memory representations. CA1 also encodes time, space-time
trajectories, and non-spatial associations.

Theta phase precession (CA1 place cells fire at progressively earlier
theta phases as the animal traverses a place field; O'Keefe Recce 1993)
provides a temporal coding scheme that interacts with the medial
septum theta pacemaker. Sharp-wave ripples (SWRs) during quiet wake
and NREM sleep are CA1-CA3 reactivation events critical for memory
consolidation -- replay of awake place-cell sequences during ripples
supports systems-level consolidation.

CA1 output reaches subiculum (the main hippocampal output station,
covered separately), prefrontal cortex via direct projections, and
lateral septum.

In Nova's substrate this provides hippocampal output, place-coding
proxy, theta-phase coding, and the SWR replay signal. Reads from
medial septum theta and emits CA1 output to subiculum / LS / mPFC
equivalent mechanisms.

KEY FINDINGS
============
1. CA1 pyramidal neurons are place cells -- fire when animal is at a
   particular spatial location -- Nobel-winning discovery -- [O'Keefe
    Dostrovsky 1971, Brain Res 34:171; reviewed Moser Kropff Moser
    2008 Annu Rev Neurosci 31:69]
2. CA1 phase precession -- place cells fire at progressively earlier
   theta phases through field traversal -- temporal coding mechanism --
   [O'Keefe Recce 1993, Hippocampus 3:317-330]
3. Sharp-wave ripples in CA1 during quiet wake and NREM replay awake
   sequences -- substrate of memory consolidation -- [Wilson McNaughton
    1994, Science 265:676; Foster Wilson 2006 Nature 440:680;
    reviewed Buzsaki 2015 Hippocampus 25:1073]
4. CA1 pattern completion -- partial cues reactivate complete CA3-CA1
   patterns -- substrate of recollection -- [Marr 1971; Treves Rolls
    1994; Nakazawa et al. 2002 Science 297:211]
5. CA1 → subiculum and direct CA1 → mPFC projections relay hippocampal
   output to extra-hippocampal targets -- [reviewed Cenquizca Swanson
    2007 Brain Res Rev 56:1; Witter et al. 2017 J Neurosci]

INPUTS (from prior_results)
============================
- DentateGyrusPatternSep.dg_output (optional; default 0)
- HippocampalContextProxy.context_id (optional; default 0)
- HippocampalContextProxy.familiarity (optional; default 0.5)
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_amplitude
- MedialSeptumTheta.theta_active
- LocomotionProxy.locomotion_speed
- ArousalRegulator.tonic_level
- SleepWakeFlipFlop.sleep_wake_state
- ValenceTagger.valence_intensity

OUTPUTS (to brain_runner enrichment)
=====================================
- ca1_pyramidal_drive (0.0-1.0): pyramidal output
- place_coding_signal (0.0-1.0): place-cell ensemble engagement
- pattern_completion_strength (0.0-1.0): cue→memory recall
- swr_active (bool): sharp-wave ripple in progress
- theta_phase_index (0.0-1.0): inherited theta phase
- ca1_subiculum_relay (0.0-1.0): CA1→subiculum output
- ca1_mpfc_relay (0.0-1.0): CA1→mPFC direct projection
- ca1_state (str): "encoding" | "retrieval" | "swr_replay" | "quiet"

brain_runner enrichment:
    ca1 = all_results.get("HippocampalCA1Output", {})
    if ca1:
        enrichments["brain_ca1_drive"] = ca1.get("ca1_pyramidal_drive", 0.2)
        enrichments["brain_place_coding"] = ca1.get("place_coding_signal", 0.0)
        enrichments["brain_swr_active"] = ca1.get("swr_active", False)
        enrichments["brain_ca1_state"] = ca1.get("ca1_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA1Output(BrainMechanism):
    BASELINE = 0.20
    SWR_PROBABILITY_THRESHOLD = 0.55
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="HippocampalCA1Output_HippocampalCA1Output",
            human_analog="Hippocampal CA1 pyramidal output / place cells",
            layer="foundational",
        )
        self.state.setdefault("ca1_pyramidal_drive", self.BASELINE)
        self.state.setdefault("place_coding_signal", 0.0)
        self.state.setdefault("pattern_completion_strength", 0.0)
        self.state.setdefault("swr_active", False)
        self.state.setdefault("theta_phase_index", 0.0)
        self.state.setdefault("ca1_subiculum_relay", 0.0)
        self.state.setdefault("ca1_mpfc_relay", 0.0)
        self.state.setdefault("ca1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ca1_drive_target(self, dg_out: float, theta_active: bool, theta_amp: float,
                          arousal: float) -> float:
        """CA1 pyramidal drive -- engaged by DG/CA3 input plus theta state."""
        target = self.BASELINE + dg_out * 0.5
        if theta_active:
            target += theta_amp * 0.3
        target += max(0.0, arousal - 0.4) * 0.2
        return min(1.0, target)

    def _place_coding(self, locomotion: float, theta_active: bool, ca1: float) -> float:
        """Place-coding signal -- most active during locomotion + theta."""
        if not theta_active or locomotion < 0.10:
            return ca1 * 0.3
        return min(1.0, locomotion * 0.5 + theta_amp_safe(theta_active, ca1) * 0.5)

    def _pattern_completion(self, dg_out: float, familiarity: float, ca1: float) -> float:
        """Pattern completion -- cue → full memory recall.
        Engaged when familiar cue + DG/CA3 input.
        """
        if dg_out < 0.15 and familiarity < 0.30:
            return 0.0
        return min(1.0, familiarity * 0.5 + dg_out * 0.3 + ca1 * 0.2)

    def _swr_check(self, sleep_state: str, locomotion: float, theta_active: bool,
                    ca1: float) -> bool:
        """SWR -- sharp-wave ripple. Active during quiet wake (no theta) and NREM
        with sufficient CA1 drive.
        """
        if theta_active or locomotion > 0.20:
            return False
        if sleep_state == "WAKE" and ca1 > 0.40:
            return True
        if sleep_state == "SLEEP" and ca1 > 0.30:
            return True
        return False

    def _ca1_subiculum_relay(self, ca1: float, place: float) -> float:
        """CA1 → subiculum main output."""
        return min(1.0, ca1 * 0.6 + place * 0.4)

    def _ca1_mpfc_relay(self, ca1: float, theta_active: bool, swr: bool) -> float:
        """CA1 → mPFC direct projection."""
        if swr:
            return min(1.0, ca1 * 0.95)  # ripple-coupled high
        if theta_active:
            return min(1.0, ca1 * 0.7)
        return ca1 * 0.4

    def _classify_state(self, swr: bool, place: float, completion: float, ca1: float) -> str:
        if swr:
            return "swr_replay"
        if completion > 0.45:
            return "retrieval"
        if place > 0.40:
            return "encoding"
        if ca1 < 0.25:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg = prior.get("DentateGyrusPatternSep", {})
        dg_out = float(dg.get("dg_output", 0.0))

        ctx = prior.get("HippocampalContextProxy", {})
        familiarity = float(ctx.get("familiarity", 0.5))

        ms = prior.get("MedialSeptumTheta", {})
        theta_phase = float(ms.get("theta_phase", 0.0))
        theta_amp = float(ms.get("theta_amplitude", 0.0))
        theta_active = bool(ms.get("theta_active", False))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- CA1 drive ---
        ca1_target = self._ca1_drive_target(dg_out, theta_active, theta_amp, tonic)
        prev_ca1 = float(self.state.get("ca1_pyramidal_drive", self.BASELINE))
        new_ca1 = self._smooth(prev_ca1, ca1_target)

        # --- Place coding ---
        place = self._place_coding(locomotion, theta_active, new_ca1)
        prev_place = float(self.state.get("place_coding_signal", 0.0))
        new_place = self._smooth(prev_place, place)

        # --- Pattern completion ---
        completion = self._pattern_completion(dg_out, familiarity, new_ca1)
        prev_comp = float(self.state.get("pattern_completion_strength", 0.0))
        new_comp = self._smooth(prev_comp, completion)

        # --- SWR ---
        swr = self._swr_check(sleep_state, locomotion, theta_active, new_ca1)

        # --- Outputs ---
        sub_relay = self._ca1_subiculum_relay(new_ca1, new_place)
        mpfc_relay = self._ca1_mpfc_relay(new_ca1, theta_active, swr)

        # --- State ---
        state = self._classify_state(swr, new_place, new_comp, new_ca1)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ca1_pyramidal_drive"] = round(new_ca1, 4)
        self.state["place_coding_signal"] = round(new_place, 4)
        self.state["pattern_completion_strength"] = round(new_comp, 4)
        self.state["swr_active"] = swr
        self.state["theta_phase_index"] = round(theta_phase, 4)
        self.state["ca1_subiculum_relay"] = round(sub_relay, 4)
        self.state["ca1_mpfc_relay"] = round(mpfc_relay, 4)
        self.state["ca1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ca1_pyramidal_drive": round(new_ca1, 4),
            "place_coding_signal": round(new_place, 4),
            "pattern_completion_strength": round(new_comp, 4),
            "swr_active": swr,
            "theta_phase_index": round(theta_phase, 4),
            "ca1_subiculum_relay": round(sub_relay, 4),
            "ca1_mpfc_relay": round(mpfc_relay, 4),
            "ca1_state": state,
        }


def theta_amp_safe(theta_active: bool, ca1: float) -> float:
    """Helper: returns ca1 if theta active else 0."""
    return ca1 if theta_active else 0.0
