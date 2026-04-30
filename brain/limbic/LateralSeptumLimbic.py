"""
LateralSeptumLimbic -- Lateral Septum Anxiety / Stress / Social Modulator

NEURAL SUBSTRATE
================
The lateral septum (LS) is a major limbic relay sitting between the
cingulate cortex above and the medial septum and diagonal band below.
LS contains predominantly GABAergic projection neurons divided into
dorsal, intermediate, and ventral subdivisions. LS receives a massive
glutamatergic input from hippocampal CA1/CA3 and subiculum (the
principal hippocampal extra-cortical output), plus inputs from mPFC,
amygdala (especially BLA and CeA), and brainstem monoaminergic nuclei.

LS projects to MS-DBB (modulating theta), to lateral hypothalamus,
to VTA, to PAG, and to BNST. Through these projections LS gates
hippocampal output to subcortical structures and modulates anxiety,
stress responses, social behavior, and feeding.

The classical "septal rage" lesion finding established LS as
anti-aggression / anti-defensive -- septal lesion produces
hyperreactivity, fear, and aggression. Modern optogenetic dissection
has refined this: LS is bidirectional and population-specific. Anthony
et al. (2014, Cell) showed LS CRF receptor 2-expressing neurons
control persistent fear, with activation prolonging fear and silencing
attenuating it. Wong et al. (2016) showed LS GABA projections to LH
suppress feeding (LS-LH stop signal).

LS also participates in social behaviors -- LS lesion produces social
deficits, and LS oxytocin signaling supports pair bonding (Lukas et al.
2011). Recent work shows LS has dedicated subpopulations for distinct
threats -- predator vs conspecific aggression -- projecting to distinct
hypothalamic targets.

In Nova's substrate this provides the hippocampus-driven anxiety and
defensive modulator -- converts hippocampal context output, BLA
emotional drives, and stress signals into LS-routed gating of
hypothalamic / VTA / PAG defensive and motivational targets.

KEY FINDINGS
============
1. Lateral septum CRF-receptor-2 expressing neurons control persistent
   fear -- activation prolongs fear, silencing attenuates -- [Anthony et al.
    2014, Cell 156:522-536, "Control of stress-induced persistent
    anxiety by an extra-amygdala septohypothalamic circuit"]
2. LS GABA projection to lateral hypothalamus suppresses feeding --
   "stop eating" pathway from LS-LH -- [Wong et al. 2016, Cell
    167:961-972, "Effective Modulation of Male Aggression through
    Lateral Septum to Medial Hypothalamus Projection"]
3. Septal lesions produce hyperreactivity, fear, and aggression
   ("septal rage") -- classic dis-inhibition phenotype -- [Brady Nauta
    1953 J Comp Physiol Psychol; reviewed Sheehan et al. 2004]
4. LS oxytocin signaling supports pair bonding and social recognition --
   [Lukas et al. 2011, Neuropsychopharmacology 36:2159; reviewed
    Donaldson Young 2008 Science]
5. LS distinct subpopulations encode predator vs conspecific threat --
   targeted projections to VMHdm vs VMHvl -- [reviewed Tsuneoka
    Funato 2021 Front Cell Neurosci]

INPUTS (from prior_results)
============================
- HippocampalContextProxy.subiculum_output (optional; default 0)
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- ValenceTagger.social_context
- ValenceTagger.valence_sign
- StressActivationAxis.cortisol_level
- StressActivationAxis.stress_active
- CRHStressDispatcher.crh_drive
- BasolateralAmygdala.bla_excitatory_drive
- OxytocinSynthesisHub.oxytocin_release
- AppetiteNPYBalancer.energy_balance_signed

OUTPUTS (to brain_runner enrichment)
=====================================
- ls_drive (0.0-1.0): overall LS GABA output
- crfr2_persistent_fear (0.0-1.0): LS-CRFR2 chronic-fear circuit
- ls_lh_feeding_brake (0.0-1.0): LS→LH stop-eating projection
- ls_aggression_modulation (signed -1..+1): + suppress, - permit
- social_recognition_drive (0.0-1.0): LS-OT social signal
- ls_state (str): "quiet" | "persistent_fear" | "feeding_brake" | "social_engaged" | "aggression_suppressed"

brain_runner enrichment:
    ls = all_results.get("LateralSeptumLimbic", {})
    if ls:
        enrichments["brain_ls_drive"] = ls.get("ls_drive", 0.2)
        enrichments["brain_crfr2_fear"] = ls.get("crfr2_persistent_fear", 0.0)
        enrichments["brain_ls_feeding_brake"] = ls.get("ls_lh_feeding_brake", 0.0)
        enrichments["brain_ls_state"] = ls.get("ls_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LateralSeptumLimbic(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="LateralSeptumLimbic",
            human_analog="Lateral septum (anxiety/stress/social/feeding modulator)",
            layer="foundational",
        )
        self.state.setdefault("ls_drive", self.BASELINE)
        self.state.setdefault("crfr2_persistent_fear", 0.0)
        self.state.setdefault("ls_lh_feeding_brake", 0.0)
        self.state.setdefault("ls_aggression_modulation", 0.0)
        self.state.setdefault("social_recognition_drive", 0.0)
        self.state.setdefault("ls_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ls_drive_target(self, subiculum: float, bla: float, cortisol: float,
                          stress: bool) -> float:
        """LS drive -- driven by hippocampal/BLA + stress signals."""
        target = self.BASELINE + subiculum * 0.4 + bla * 0.3
        target += max(0.0, cortisol - 0.4) * 0.3
        if stress:
            target += 0.10
        return min(1.0, target)

    def _crfr2_fear(self, ls: float, crh: float, stress: bool, threat: bool) -> float:
        """LS CRFR2 persistent-fear circuit (Anthony 2014)."""
        if not (stress or threat):
            return ls * 0.2
        target = crh * 0.5 + ls * 0.3
        if threat:
            target += 0.10
        return min(1.0, target)

    def _feeding_brake(self, ls: float, energy_balance: float) -> float:
        """LS→LH stop-eating projection (Wong 2016).
        Engaged when satiated/positive energy balance with active LS.
        """
        if energy_balance < 0.0:
            return 0.0
        return min(1.0, ls * 0.5 + energy_balance * 0.5)

    def _aggression_modulation(self, ls: float, threat: bool, social: bool,
                                cortisol: float) -> float:
        """LS aggression modulation. Septal lesion = aggression; intact LS suppresses."""
        if not (threat and social):
            return 0.0
        # + = suppression, - = permits aggression
        target = ls * 0.7 - max(0.0, cortisol - 0.65) * 0.4
        return max(-1.0, min(1.0, target))

    def _social_recognition(self, oxytocin: float, social: bool, ls: float) -> float:
        """LS oxytocin social recognition (Lukas 2011)."""
        if not social:
            return 0.0
        return min(1.0, oxytocin * 0.6 + ls * 0.3)

    def _classify_state(self, crfr2: float, feeding_brake: float, agg_mod: float,
                         social: float, ls: float) -> str:
        if crfr2 > 0.45:
            return "persistent_fear"
        if feeding_brake > 0.40:
            return "feeding_brake"
        if social > 0.40:
            return "social_engaged"
        if agg_mod > 0.40:
            return "aggression_suppressed"
        if ls < 0.25:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hipp = prior.get("HippocampalContextProxy", {})
        subiculum = float(hipp.get("subiculum_output", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        social = bool(valence.get("social_context", False))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))
        stress_active = bool(stress.get("stress_active", False))

        crh_data = prior.get("CRHStressDispatcher", {})
        crh = float(crh_data.get("crh_drive", 0.30))

        bla = prior.get("BasolateralAmygdala", {})
        bla_drive = float(bla.get("bla_excitatory_drive", 0.0))

        ot = prior.get("OxytocinSynthesisHub", {})
        oxytocin = float(ot.get("oxytocin_release", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))

        # --- LS drive ---
        ls_target = self._ls_drive_target(subiculum, bla_drive, cortisol, stress_active)
        prev_ls = float(self.state.get("ls_drive", self.BASELINE))
        new_ls = self._smooth(prev_ls, ls_target)

        # --- CRFR2 persistent fear ---
        crfr2 = self._crfr2_fear(new_ls, crh, stress_active, threat)
        prev_crfr2 = float(self.state.get("crfr2_persistent_fear", 0.0))
        new_crfr2 = self._smooth(prev_crfr2, crfr2)

        # --- Feeding brake ---
        feeding_brake = self._feeding_brake(new_ls, energy_balance)
        prev_brake = float(self.state.get("ls_lh_feeding_brake", 0.0))
        new_brake = self._smooth(prev_brake, feeding_brake)

        # --- Aggression modulation ---
        agg_mod = self._aggression_modulation(new_ls, threat, social, cortisol)

        # --- Social recognition ---
        social_rec = self._social_recognition(oxytocin, social, new_ls)
        prev_social = float(self.state.get("social_recognition_drive", 0.0))
        new_social = self._smooth(prev_social, social_rec)

        # --- State ---
        state = self._classify_state(new_crfr2, new_brake, agg_mod, new_social, new_ls)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ls_drive"] = round(new_ls, 4)
        self.state["crfr2_persistent_fear"] = round(new_crfr2, 4)
        self.state["ls_lh_feeding_brake"] = round(new_brake, 4)
        self.state["ls_aggression_modulation"] = round(agg_mod, 4)
        self.state["social_recognition_drive"] = round(new_social, 4)
        self.state["ls_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ls_drive": round(new_ls, 4),
            "crfr2_persistent_fear": round(new_crfr2, 4),
            "ls_lh_feeding_brake": round(new_brake, 4),
            "ls_aggression_modulation": round(agg_mod, 4),
            "social_recognition_drive": round(new_social, 4),
            "ls_state": state,
        }
