"""
LateralHabenulaAversion -- Lateral Habenula Negative Reward / Aversion Hub

NEURAL SUBSTRATE
================
The lateral habenula (LHb) is a small bilateral epithalamic nucleus that
sits dorsal to the thalamus and is connected to the basal forebrain via
the stria medullaris and to the midbrain via the fasciculus retroflexus.
It is the principal "anti-reward" / aversion node of the mammalian brain
and a core driver of negative reward prediction error (RPE) signaling.

The canonical computational role of the LHb is opposite to that of VTA
dopamine neurons. Matsumoto and Hikosaka (2007) showed in primates that
LHb neurons are excited by stimuli predicting absence of reward (or
punishment) and inhibited by stimuli predicting presence of reward.
LHb signaling thus carries negative RPE.

The LHb's key downstream relay is the rostromedial tegmental nucleus
(RMTg, also called the tail of the VTA), a GABAergic structure that
densely innervates VTA dopamine neurons. LHb glutamatergic projections
excite RMTg, which then inhibits VTA DA neurons. This LHb→RMTg→VTA
disynaptic pathway converts positive-going LHb activity into the dip in
VTA DA firing seen for reward omission. LHb also projects directly to
DRN serotonergic neurons and modulates 5-HT-mediated behavioral state.

LHb dysfunction is implicated in depression and learned helplessness --
overactive LHb suppresses VTA dopamine, producing anhedonia. Bursting
LHb neurons (NMDA-dependent) appear to drive the depressive phenotype
in animal models, and LHb is a target of ketamine's rapid antidepressant
action.

In {{AGENT_NAME}}'s substrate this provides the anti-reward / aversion negative-PE
channel that suppresses VTA DA when expected reward is omitted or
explicit punishment is delivered.

KEY FINDINGS
============
1. LHb neurons are excited by stimuli predicting absence of reward (or
   punishment) and inhibited by stimuli predicting presence of reward --
   inverse of VTA DA neurons -- [Matsumoto Hikosaka 2007, Nature
    447:1111-1115, "Lateral habenula as a source of negative reward
    signals in dopamine neurons"]
2. RMTg (rostromedial tegmental nucleus) relays LHb negative reward
   signals to VTA DA neurons via GABAergic inhibition -- [Hong et al.
    2011, J Neurosci 31:11457-11471, "Negative Reward Signals from the
    Lateral Habenula to Dopamine Neurons Are Mediated by Rostromedial
    Tegmental Nucleus in Primates" PMC3315151]
3. LHb activity scales with reward prediction error magnitude -- encodes
   step-by-step changes -- [reviewed PMC9641246, "Lateral habenula
    neurons signal step-by-step changes of reward prediction"]
4. LHb both responds to and learns aversive/reward associations --
   bidirectional encoding -- [reviewed Nature Translational Psychiatry
    2021 doi:10.1038/s41398-021-01774-0, "Reward and aversion encoding
    in the lateral habenula for innate and learned behaviours"]
5. LHb learning shapes both aversion and reward responses through
   experience-dependent plasticity -- [Lecca et al. 2017 eLife 6:e23045,
    "Learning shapes the aversion and reward responses of lateral
    habenula neurons"]

INPUTS (from prior_results)
============================
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- ValenceTagger.threat_signal
- VentralTegmentalDopamine.expected_reward
- VentralTegmentalDopamine.vta_da_phasic
- DescendingPainGate.expected_pain_modulation
- StressActivationAxis.cortisol_level
- DorsalRapheSerotonin.serotonin_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- lhb_drive (0.0-1.0): LHb glutamatergic output
- rmtg_drive (0.0-1.0): RMTg GABA → VTA inhibition relay
- negative_rpe (signed -1..0): negative-going RPE signal
- vta_inhibition (0.0-1.0): predicted VTA DA suppression
- drn_suppression (0.0-1.0): LHb → DRN suppression
- helplessness_marker (bool): chronic LHb hyperactivity
- lhb_state (str): "quiet" | "negative_pe" | "burst" | "chronic_engaged"

brain_runner enrichment:
    lhb = all_results.get("LateralHabenulaAversion", {})
    if lhb:
        enrichments["brain_lhb_drive"] = lhb.get("lhb_drive", 0.2)
        enrichments["brain_rmtg_drive"] = lhb.get("rmtg_drive", 0.2)
        enrichments["brain_negative_rpe"] = lhb.get("negative_rpe", 0.0)
        enrichments["brain_lhb_state"] = lhb.get("lhb_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LateralHabenulaAversion(BrainMechanism):
    BASELINE_LHB = 0.20
    BURST_THRESHOLD = 0.65
    HELPLESSNESS_TICKS = 80
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="LateralHabenulaAversion",
            human_analog="Lateral habenula negative reward / aversion hub",
            layer="foundational",
        )
        self.state.setdefault("lhb_drive", self.BASELINE_LHB)
        self.state.setdefault("rmtg_drive", 0.20)
        self.state.setdefault("negative_rpe", 0.0)
        self.state.setdefault("vta_inhibition", 0.0)
        self.state.setdefault("drn_suppression", 0.0)
        self.state.setdefault("helplessness_marker", False)
        self.state.setdefault("lhb_state", "quiet")
        self.state.setdefault("high_lhb_streak", 0)
        self.state.setdefault("recent_lhb", [])
        self.state.setdefault("tick_count", 0)

    def _negative_rpe(self, vta_phasic: float, expected: float, valence_sign: int,
                      valence_intensity: float, expected_pain: float) -> float:
        """Negative RPE -- LHb fires for reward omission and punishment.
        Captured as: -min(0, RPE) plus aversion drive.
        """
        # If VTA phasic is negative, LHb mirrors it (positive → activation)
        rpe_neg = max(0.0, -vta_phasic)
        # Direct aversion signal
        if valence_sign < 0:
            rpe_neg = max(rpe_neg, valence_intensity * 0.7)
        # Pain prediction also drives LHb
        rpe_neg += max(0.0, expected_pain) * 0.3
        return min(1.0, rpe_neg)

    def _lhb_drive_target(self, neg_rpe: float, threat: bool, cortisol: float) -> float:
        """LHb drive target -- scales with negative RPE and chronic stress."""
        target = self.BASELINE_LHB + neg_rpe * 0.7
        if threat:
            target += 0.10
        if cortisol > 0.65:
            target += (cortisol - 0.5) * 0.3  # chronic stress potentiates LHb
        return min(1.0, target)

    def _rmtg_drive(self, lhb_drive: float) -> float:
        """RMTg GABA relay -- Hong 2011 LHb→RMTg→VTA pathway."""
        return min(1.0, lhb_drive * 1.05)

    def _vta_inhibition(self, rmtg: float) -> float:
        """Predicted VTA DA inhibition produced by LHb→RMTg engagement."""
        return min(1.0, rmtg * 0.95)

    def _drn_suppression(self, lhb_drive: float, valence_sign: int) -> float:
        """LHb → DRN suppression -- engaged with negative valence."""
        if valence_sign >= 0:
            return lhb_drive * 0.3
        return min(1.0, lhb_drive * 0.7)

    def _detect_helplessness(self, streak: int) -> bool:
        return streak > self.HELPLESSNESS_TICKS

    def _classify_state(self, lhb: float, neg_rpe: float, helpless: bool) -> str:
        if helpless:
            return "chronic_engaged"
        if lhb > self.BURST_THRESHOLD:
            return "burst"
        if neg_rpe > 0.3:
            return "negative_pe"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))
        threat = bool(valence.get("threat_signal", False))

        vta = prior.get("VentralTegmentalDopamine", {})
        vta_phasic = float(vta.get("vta_da_phasic", 0.0))
        expected = float(vta.get("expected_reward", 0.0))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        # --- Negative RPE ---
        neg_rpe = self._negative_rpe(vta_phasic, expected, valence_sign,
                                      valence_intensity, expected_pain)

        # --- LHb drive target ---
        lhb_target = self._lhb_drive_target(neg_rpe, threat, cortisol)
        prev_lhb = float(self.state.get("lhb_drive", self.BASELINE_LHB))
        new_lhb = self._smooth(prev_lhb, lhb_target)

        # --- RMTg relay ---
        rmtg = self._rmtg_drive(new_lhb)
        prev_rmtg = float(self.state.get("rmtg_drive", 0.20))
        new_rmtg = self._smooth(prev_rmtg, rmtg)

        # --- VTA inhibition prediction ---
        vta_inh = self._vta_inhibition(new_rmtg)

        # --- DRN suppression ---
        drn_supp = self._drn_suppression(new_lhb, valence_sign)

        # --- Helplessness detection (chronic high LHb) ---
        prev_streak = int(self.state.get("high_lhb_streak", 0))
        if new_lhb > 0.55:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        helpless = self._detect_helplessness(streak)

        # --- State classification ---
        state = self._classify_state(new_lhb, neg_rpe, helpless)

        recent = list(self.state.get("recent_lhb", []))
        recent.append(round(new_lhb, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["lhb_drive"] = round(new_lhb, 4)
        self.state["rmtg_drive"] = round(new_rmtg, 4)
        self.state["negative_rpe"] = round(-neg_rpe, 4)  # signed negative
        self.state["vta_inhibition"] = round(vta_inh, 4)
        self.state["drn_suppression"] = round(drn_supp, 4)
        self.state["helplessness_marker"] = helpless
        self.state["lhb_state"] = state
        self.state["high_lhb_streak"] = streak
        self.state["recent_lhb"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        avg_drive = round(sum(recent)/len(recent), 4) if recent else 0.0
        self.state["avg_drive_60t"] = avg_drive
        volatility = round(sum(abs(lhb - avg_drive) for lhb in recent)/len(recent), 4) if len(recent) > 1 else 0.0
        self.state["lhb_volatility"] = volatility
        self.state["helplessness_marker"] = helpless
        self.state["helplessness_streak"] = streak
        self.state["lhb_peak_60t"] = round(max(recent), 4) if recent else 0.0
        self.state["lhb_trough_60t"] = round(min(recent), 4) if recent else 0.0
        self.persist_state()

        return {
            "lhb_drive": round(new_lhb, 4),
            "rmtg_drive": round(new_rmtg, 4),
            "negative_rpe": round(-neg_rpe, 4),
            "vta_inhibition": round(vta_inh, 4),
            "drn_suppression": round(drn_supp, 4),
            "helplessness_marker": helpless,
            "lhb_state": state,
            "high_lhb_streak": streak,
        }
