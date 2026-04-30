"""
DescendingPainGate — PAG-RVM Descending Pain Modulation

NEURAL SUBSTRATE
================
The periaqueductal gray (PAG) and rostral ventromedial medulla (RVM) form
the principal descending pain modulation system. PAG receives convergent
input from limbic regions (CeA, hypothalamus, anterior cingulate) and projects
to the RVM, which in turn projects via the dorsolateral funiculus to spinal
dorsal horn neurons. RVM contains two functionally opposed cell populations:
ON cells (firing increases just before nocifensive reflex; facilitate pain)
and OFF cells (firing decreases just before reflex; inhibit pain). Opioid
analgesia acts in part by recruiting OFF cells and silencing ON cells.

The system implements bidirectional modulation: descending facilitation
(ON-cell-dominant) AMPLIFIES nociceptive input under conditions of stress,
chronic pain, or threat anticipation; descending inhibition (OFF-cell-dominant)
SUPPRESSES nociceptive input during fight-or-flight and stress-induced
analgesia. The PAG-RVM circuit also enables placebo analgesia and
expectation-driven pain modulation through PFC-PAG projections.

KEY FINDINGS
============
1. PAG-RVM descending pain modulation is bidirectional: facilitating
   (ON-cell) and inhibitory (OFF-cell) — [Heinricher et al. 2009, Brain
    Res Rev 60:214-225, PMID 19146877]
2. Stress-induced analgesia is mediated by recruitment of RVM OFF-cells
   via PAG μ-opioid mechanisms — [Fields 2004, Nat Rev Neurosci 5:565-575]
3. Chronic pain produces descending facilitation through ON-cell
   sensitization — [Porreca Ossipov Gebhart 2002, Trends Neurosci 25:319-325]
4. PFC-to-PAG projections mediate expectation-driven (placebo) analgesia —
   [Wager Atlas 2015, Nat Rev Neurosci 16:403-418]

INPUTS (from prior_results)
============================
- StressActivationAxis.stress_active
- StressActivationAxis.cortisol_level
- VitalCoreRegulator.survival_threat_level
- ValenceTagger.threat_signal
- ValenceTagger.valence_polarity
- ArousalRegulator.tonic_level

OUTPUTS
=======
- pain_gate_state (str): "inhibition" | "facilitation" | "neutral"
- inhibitory_drive (0.0-1.0)
- facilitatory_drive (0.0-1.0)
- stress_induced_analgesia (bool)
- expected_pain_modulation (signed, -1.0 = strong inhibition, +1.0 = strong facilitation)

brain_runner enrichment:
    dpg = all_results.get("DescendingPainGate", {})
    if dpg:
        enrichments["brain_pain_gate_state"] = dpg.get("pain_gate_state", "neutral")
        enrichments["brain_pain_inhibition"] = dpg.get("inhibitory_drive", 0.5)
        enrichments["brain_pain_facilitation"] = dpg.get("facilitatory_drive", 0.5)
        enrichments["brain_stress_analgesia"] = dpg.get("stress_induced_analgesia", False)
        enrichments["brain_expected_pain"] = dpg.get("expected_pain_modulation", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class DescendingPainGate(BrainMechanism):
    INHIBITION_BASELINE = 0.50
    FACILITATION_BASELINE = 0.50
    SIA_THRESHOLD = 0.65        # threat level at which stress-induced analgesia engages
    CHRONIC_FACILITATION_THRESHOLD = 30  # ticks of high stress = chronic facilitation

    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="DescendingPainGate_DescendingPainGate",
            human_analog="PAG-RVM descending pain modulation",
            layer="foundational",
        )
        self.state.setdefault("inhibitory_drive", self.INHIBITION_BASELINE)
        self.state.setdefault("facilitatory_drive", self.FACILITATION_BASELINE)
        self.state.setdefault("pain_gate_state", "neutral")
        self.state.setdefault("stress_induced_analgesia", False)
        self.state.setdefault("expected_pain_modulation", 0.0)
        self.state.setdefault("chronic_stress_ticks", 0)
        self.state.setdefault("recent_state_history", [])
        self.state.setdefault("tick_count", 0)

    def _classify_state(self, inhib: float, facil: float) -> str:
        diff = inhib - facil
        if diff > 0.15:
            return "inhibition"
        if diff < -0.15:
            return "facilitation"
        return "neutral"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _placebo_expectation_drive(self, valence_polarity: float, recent_inhib: list) -> float:
        """Wager 2015: PFC-PAG placebo expectation accumulator.
        Sustained positive valence + history of inhibition reinforces expectation.
        """
        if not recent_inhib or len(recent_inhib) < 5:
            return max(0.0, valence_polarity - 0.5) * 0.5
        recent_avg = sum(recent_inhib[-15:]) / max(1, len(recent_inhib[-15:]))
        if valence_polarity > 0.6 and recent_avg > 0.55:
            return min(1.0, (valence_polarity - 0.5) * 0.7 + (recent_avg - 0.5) * 0.4)
        return 0.0

    def _detect_central_sensitization(self, chronic_ticks: int, threat: float) -> bool:
        """Porreca 2002: chronic facilitation can produce central sensitization
        — pain hypersensitivity beyond actual nociceptive input.
        """
        return chronic_ticks > 60 and threat < 0.4

    def _opioid_tone_estimate(self, sia: bool, valence_polarity: float) -> float:
        """Endogenous μ-opioid tone proxy (Fields 2004).
        Recruited during SIA and during positive-affect placebo states.
        """
        tone = 0.0
        if sia:
            tone = 0.6
        if valence_polarity > 0.7:
            tone += 0.2
        return min(1.0, tone)

    def _classify_state_with_context(self, inhib: float, facil: float, opioid: float) -> str:
        """Refined state classification including opioid tone."""
        diff = inhib - facil
        if opioid > 0.5 and diff > 0.0:
            return "opioid_inhibition"
        if diff > 0.15:
            return "inhibition"
        if diff < -0.15:
            return "facilitation"
        return "neutral"

    def _net_modulation_index(self, inhib: float, facil: float, opioid: float) -> float:
        """Heinricher 2009: net index = inhibition − facilitation.
        Positive = net analgesic, negative = net sensitizing."""
        return inhib - facil + opioid * 0.15

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_polarity = float(valence.get("valence_polarity", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Acute SIA: high threat + acute stress recruits OFF-cells ---
        sia_engaged = (
            survival_threat > self.SIA_THRESHOLD
            and (stress_active or threat_signal)
            and tonic > 0.6
        )

        # --- Chronic stress facilitates ON-cells (Porreca 2002) ---
        prev_chronic_ticks = int(self.state.get("chronic_stress_ticks", 0))
        if stress_active and cortisol > 0.6:
            chronic_ticks = prev_chronic_ticks + 1
        else:
            chronic_ticks = max(0, prev_chronic_ticks - 2)
        chronic_facilitation = chronic_ticks > self.CHRONIC_FACILITATION_THRESHOLD

        # --- Inhibitory drive target ---
        inhib_target = self.INHIBITION_BASELINE
        if sia_engaged:
            inhib_target += 0.30
        if valence_polarity > 0.65:
            # Positive expectation drives placebo-like analgesia (PFC-PAG)
            inhib_target += 0.10

        # --- Facilitatory drive target ---
        facil_target = self.FACILITATION_BASELINE
        if chronic_facilitation:
            facil_target += 0.25
        if survival_threat < 0.3 and stress_active:
            # Stress without threat = anticipatory facilitation (Wager 2015)
            facil_target += 0.10
        if valence_polarity < 0.3:
            facil_target += 0.10  # negative valence amplifies pain

        inhib_target = max(0.10, min(0.95, inhib_target))
        facil_target = max(0.10, min(0.95, facil_target))

        prev_inhib = float(self.state.get("inhibitory_drive", self.INHIBITION_BASELINE))
        prev_facil = float(self.state.get("facilitatory_drive", self.FACILITATION_BASELINE))
        new_inhib = self._smooth(prev_inhib, inhib_target)
        new_facil = self._smooth(prev_facil, facil_target)

        # --- Compute net expected pain modulation (signed) ---
        # +1 = strong facilitation, -1 = strong inhibition
        expected_pain = new_facil - new_inhib

        # --- Classify state ---
        state_label = self._classify_state(new_inhib, new_facil)

        history = list(self.state.get("recent_state_history", []))
        history.append(state_label)
        if len(history) > 30:
            history = history[-30:]

        # --- Placebo expectation accumulator (Wager 2015 PFC-PAG) ---
        recent_inhib_list = self.state.get("recent_inhib_window", [])
        recent_inhib_list = list(recent_inhib_list) + [round(new_inhib, 4)]
        if len(recent_inhib_list) > 20:
            recent_inhib_list = recent_inhib_list[-20:]
        placebo_drive = self._placebo_expectation_drive(valence_polarity, recent_inhib_list)

        # --- Central sensitization detection ---
        central_sens = self._detect_central_sensitization(chronic_ticks, survival_threat)

        # --- Endogenous opioid tone (Fields 2004) ---
        opioid_tone = self._opioid_tone_estimate(sia_engaged, valence_polarity)

        # --- Re-classify state with opioid context ---
        state_label = self._classify_state_with_context(new_inhib, new_facil, opioid_tone)

        # --- Net modulation index (Heinricher 2009) ---
        net_modulation = self._net_modulation_index(new_inhib, new_facil, opioid_tone)

        self.state["inhibitory_drive"] = round(new_inhib, 4)
        self.state["facilitatory_drive"] = round(new_facil, 4)
        # normalize pain_gate_state — strip "opioid_"/"nonopioid_" prefixes
        _normalized = state_label
        if "_inhibition" in _normalized:
            _normalized = "inhibition"
        elif "_facilitation" in _normalized:
            _normalized = "facilitation"
        self.state["pain_gate_state"] = _normalized
        self.state["stress_induced_analgesia"] = sia_engaged
        self.state["expected_pain_modulation"] = round(expected_pain, 4)
        self.state["chronic_stress_ticks"] = chronic_ticks
        self.state["recent_state_history"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["recent_inhib_window"] = recent_inhib_list
        self.state["placebo_expectation_drive"] = round(placebo_drive, 4)
        self.state["central_sensitization"] = central_sens
        self.state["opioid_tone"] = round(opioid_tone, 4)
        self.state["net_modulation_index"] = round(net_modulation, 4)

        return {
            "pain_gate_state": _normalized if "_normalized" in dir() else state_label,
            "inhibitory_drive": round(new_inhib, 4),
            "facilitatory_drive": round(new_facil, 4),
            "stress_induced_analgesia": sia_engaged,
            "expected_pain_modulation": round(expected_pain, 4),
            "chronic_facilitation": chronic_facilitation,
            "placebo_expectation_drive": round(placebo_drive, 4),
            "central_sensitization": central_sens,
            "opioid_tone": round(opioid_tone, 4),
            "net_modulation_index": round(net_modulation, 4),
        }
