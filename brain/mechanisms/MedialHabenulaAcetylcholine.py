"""
MedialHabenulaAcetylcholine -- Medial Habenula Cholinergic Anxiety/Withdrawal Hub

NEURAL SUBSTRATE
================
The medial habenula (MHb) is the smaller, medial division of the
epithalamic habenula complex, anatomically and functionally distinct
from the lateral habenula. The MHb contains primarily cholinergic
neurons in its ventral subnucleus (along with substance-P-positive
neurons in the dorsal subnucleus) and is densely populated with
nicotinic acetylcholine receptors (nAChRs), particularly α5β4-containing
subtypes that distinguish MHb from most other brain regions.

The MHb projects via the fasciculus retroflexus to the interpeduncular
nucleus (IPN), where MHb cholinergic terminals release both ACh and
glutamate. The MHb-IPN axis is the principal cholinergic pathway from
limbic forebrain to brainstem and is critical for the regulation of
fear, anxiety, mood, and the somatic and affective signs of nicotine
withdrawal.

MHb cholinergic neurons robustly express nAChRs and respond strongly
to nicotine. Chronic nicotine exposure produces nAChR upregulation and
desensitization in the MHb-IPN axis; abrupt nicotine cessation unmasks
a state of cholinergic imbalance that drives nicotine withdrawal anxiety.
Silencing MHb cholinergic neurons alleviates withdrawal anxiety in
nicotine-dependent mice; activating them is anxiogenic.

The MHb also responds to stress and is implicated in mood regulation --
the superior subpart of the MHb projects to IPN to suppress anxiety in
some contexts, indicating bidirectional roles. MHb dysfunction is linked
to mood-associated disorders and substance dependence.

In the agent's substrate this provides the cholinergic anxiety/withdrawal
modulator -- a slow tonic ACh drive to IPN/brainstem that scales with
chronic stress, prior nicotine-like reinforcement loops, and acute
nAChR engagement.

KEY FINDINGS
============
1. MHb cholinergic neurons regulate anxiety during nicotine withdrawal
   via nicotinic acetylcholine receptors -- silencing alleviates,
   activating provokes -- [Pang et al. 2016, Neuropharmacology 107:294,
    "Habenula cholinergic neurons regulate anxiety during nicotine
    withdrawal via nicotinic acetylcholine receptors" PMC4982553]
2. MHb-IPN circuitry is critical in addiction, anxiety, and mood
   regulation -- connects limbic forebrain to brainstem via fasciculus
   retroflexus -- [McLaughlin Dani De Biasi 2017, J Neurochem,
    "The medial habenula and interpeduncular nucleus circuitry is
    critical in addiction, anxiety, and mood regulation" PMC6740332]
3. MHb superior subpart projection to IPN suppresses anxiety --
   bidirectional roles within MHb -- [Mol Psychiatry 2025
    doi:10.1038/s41380-025-02964-8, "The neural pathway from the
    superior subpart of the medial habenula to the interpeduncular
    nucleus suppresses anxiety"]
4. nAChRs in MHb-IPN pathway modulate reward, aversion, and emotion --
   [Ciscato et al. 2025, Eur J Neurosci doi:10.1111/ejn.70352,
    "Nicotinic Receptors in the Medial Habenula to Interpeduncular
    Nucleus Pathway"]
5. Anxiety and nicotine dependence share neural substrates in the
   habenulo-interpeduncular axis -- [Antolin-Fontes et al. 2016,
    Trends Pharmacol Sci, "Anxiety and Nicotine Dependence: Emerging
    Role of the Habenulo-Interpeduncular Axis" PMC5258775]

INPUTS (from prior_results)
============================
- ValenceTagger.valence_intensity
- ValenceTagger.threat_signal
- StressActivationAxis.stress_active
- StressActivationAxis.cortisol_level
- LateralHabenulaAversion.lhb_drive
- DorsalRapheSerotonin.serotonin_drive
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- mhb_ach_drive (0.0-1.0): MHb cholinergic output
- ipn_recruitment (0.0-1.0): downstream IPN engagement
- nachr_engagement (0.0-1.0): predicted nAChR activation
- anxiety_modulation (signed -1..+1): + provokes anxiety, - suppresses
- substance_p_drive (0.0-1.0): dorsal MHb SP output
- mhb_state (str): "quiet" | "engaged" | "anxiogenic" | "anxiolytic"

brain_runner enrichment:
    mhb = all_results.get("MedialHabenulaAcetylcholine", {})
    if mhb:
        enrichments["brain_mhb_ach"] = mhb.get("mhb_ach_drive", 0.2)
        enrichments["brain_ipn_recruit"] = mhb.get("ipn_recruitment", 0.2)
        enrichments["brain_anxiety_mod"] = mhb.get("anxiety_modulation", 0.0)
        enrichments["brain_mhb_state"] = mhb.get("mhb_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedialHabenulaAcetylcholine(BrainMechanism):
    BASELINE_ACH = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="MedialHabenulaAcetylcholine",
            human_analog="Medial habenula cholinergic anxiety/withdrawal hub",
            layer="foundational",
        )
        self.state.setdefault("mhb_ach_drive", self.BASELINE_ACH)
        self.state.setdefault("ipn_recruitment", 0.20)
        self.state.setdefault("nachr_engagement", 0.20)
        self.state.setdefault("anxiety_modulation", 0.0)
        self.state.setdefault("substance_p_drive", 0.10)
        self.state.setdefault("mhb_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ach_target(self, threat: bool, cortisol: float, lhb: float, valence: float) -> float:
        """MHb ACh -- engaged by stress, threat, and LHb activity (Pang 2016)."""
        target = self.BASELINE_ACH
        if threat:
            target += valence * 0.3
        if cortisol > 0.55:
            target += (cortisol - 0.5) * 0.4
        target += lhb * 1.2  # LHb-MHb coupling
        return min(1.0, target)

    def _ipn_recruitment(self, ach: float, sp: float) -> float:
        """IPN recruitment -- both ACh and SP drive IPN."""
        return min(1.0, ach * 0.7 + sp * 0.3)

    def _nachr_engagement(self, ach: float) -> float:
        """nAChR engagement -- α5β4 receptors in MHb-IPN axis."""
        return min(1.0, ach * 1.05)

    def _anxiety_modulation(self, ipn: float, threat: bool, valence: float) -> float:
        """Net anxiety modulation -- anxiogenic when MHb-IPN strongly engaged
        with stress, mildly anxiolytic via superior MHb subnucleus
        (Mol Psychiatry 2025) at moderate baseline.
        """
        if threat:
            return min(1.0, ipn * 0.7)  # anxiogenic
        # Mild baseline tonic -- anxiolytic effect of normal MHb activity
        if 0.15 < ipn < 0.40:
            return -0.10
        if ipn > 0.55:
            return min(1.0, ipn * 0.5)
        return 0.0

    def _substance_p_target(self, threat: bool, valence: float, cortisol: float) -> float:
        """Dorsal MHb substance P -- engaged by threat and chronic stress."""
        target = 0.10
        if threat:
            target += valence * 0.4
        if cortisol > 0.6:
            target += (cortisol - 0.5) * 0.3
        return min(1.0, target)

    def _tolerance_index(self, nachr: float) -> float:
        """Accumulated nicotine tolerance from persistent nAChR saturation.
        Chronic high nachr engagement reduces MHb-IPN signaling efficiency
        (Pang 2016). Tolerance builds slowly and decays slowly via slow EMA.
        """
        prev = float(self.state.get("tolerance_index", 0.0))
        # Target: proportion of time nachr is elevated
        target = nachr * 0.4
        # Slow EMA decay: tolerance dissipates ~12x more slowly than it builds
        return 0.92 * prev + 0.08 * target

    def _classify_state(self, ach: float, anxiety_mod: float) -> str:
        if anxiety_mod > 0.30:
            return "anxiogenic"
        if anxiety_mod < -0.05:
            return "anxiolytic"
        if ach > 0.40:
            return "engaged"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        threat = bool(valence.get("threat_signal", False))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        lhb_data = prior.get("LateralHabenulaAversion", {})
        lhb = float(lhb_data.get("lhb_drive", 0.0))

        # --- ACh drive ---
        ach_target = self._ach_target(threat, cortisol, lhb, valence_intensity)
        prev_ach = float(self.state.get("mhb_ach_drive", self.BASELINE_ACH))
        new_ach = self._smooth(prev_ach, ach_target)

        # --- Substance P drive (dorsal MHb) ---
        sp_target = self._substance_p_target(threat, valence_intensity, cortisol)
        prev_sp = float(self.state.get("substance_p_drive", 0.10))
        new_sp = self._smooth(prev_sp, sp_target)

        # --- IPN recruitment ---
        ipn_target = self._ipn_recruitment(new_ach, new_sp)
        prev_ipn = float(self.state.get("ipn_recruitment", 0.20))
        new_ipn = self._smooth(prev_ipn, ipn_target)

        # --- nAChR engagement ---
        nachr = self._nachr_engagement(new_ach)

        # --- Anxiety modulation ---
        anxiety_mod = self._anxiety_modulation(new_ipn, threat, valence_intensity)

        # --- State ---
        state = self._classify_state(new_ach, anxiety_mod)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mhb_ach_drive"] = round(new_ach, 4)
        self.state["ipn_recruitment"] = round(new_ipn, 4)
        self.state["nachr_engagement"] = round(nachr, 4)
        self.state["anxiety_modulation"] = round(anxiety_mod, 4)
        self.state["substance_p_drive"] = round(new_sp, 4)
        self.state["mhb_state"] = state
        self.state["recent_states"] = recent
        fr_eng = max(0.0, min(1.0, (new_ach + new_ipn) * 0.5))
        if state == "WithdrawalActive":
            fr_eng = min(1.0, fr_eng + 0.20)
        self.state["fr_engagement"] = round(fr_eng, 4)
        self.state["tolerance_index"] = round(self._tolerance_index(nachr), 4)
        self.state["withdrawal_proxy"] = float(state == "WithdrawalActive")
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mhb_ach_drive": round(new_ach, 4),
            "ipn_recruitment": round(new_ipn, 4),
            "nachr_engagement": round(nachr, 4),
            "anxiety_modulation": round(anxiety_mod, 4),
            "substance_p_drive": round(new_sp, 4),
            "mhb_state": state,
            "fr_engagement": round(fr_eng, 4),
            "nicotine_withdrawal_proxy": (state == "WithdrawalActive"),
        }
