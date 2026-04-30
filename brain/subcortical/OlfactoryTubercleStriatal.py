"""
OlfactoryTubercleStriatal — OT Ventral Striatal Olfactory-Reward Hub

NEURAL SUBSTRATE
================
The olfactory tubercle (OT, also called tuberculum olfactorium or
striatum olfactorium) is a hybrid structure with both **cortical
(allocortical)** and **striatal** features. Anatomically it sits in the
ventral basal forebrain just lateral to the diagonal band of Broca and
ventral to the nucleus accumbens. Recent work (Wesson Wilson 2011 et al.;
Xiong & Wesson 2016) has reclassified OT as a **ventral striatal
extension** alongside NAc shell, rather than as primary olfactory cortex
(its older designation).

OT receives:
- Direct olfactory input from olfactory bulb mitral/tufted cells
  (lateral olfactory tract)
- Piriform cortex projections (processed olfactory)
- Limbic input from BLA, entorhinal, mPFC
- VTA dopaminergic input (mesolimbic)

OT projects to:
- Ventral pallidum (continuing the striato-pallidal architecture)
- Lateral hypothalamus
- Brainstem reticular formation

OT contains both medium spiny neurons (D1/D2 like NAc) and "Islands of
Calleja" (densely packed granule cell clusters). The MSN component
makes OT genuinely striatal — it integrates dopamine-based reward
learning with olfactory input. Murata et al. (2015 Nat Neurosci)
showed OT D1-MSNs encode attractive/appetitive odors and D2-MSNs
encode aversive odors, demonstrating OT's role in **odor valence
coding and motivated odor behavior**.

OT is implicated in:
- Social odor recognition and motivated approach
- Food-odor reward (overlap with NAc-shell hedonic signaling)
- Drug-conditioned odor cues (addiction relevance)
- Pheromone-driven behaviors (some species)

In {{AGENT_NAME}}'s substrate this provides the olfactory-reward integration node —
combines OB/piriform olfactory output with VTA DA + BLA reward-engram
to produce odor-triggered approach/avoidance bias.

KEY FINDINGS
============
1. Olfactory tubercle is reclassified as ventral striatal extension
   (alongside NAc shell), not primary olfactory cortex — has MSN D1/D2
   architecture and integrates DA with olfactory input — [Wesson Wilson
    2011, Front Neuroanat 5:46, "Sniffing out the contributions of
    the olfactory tubercle to the sense of smell"] [Xiong Wesson 2016
    eNeuro 3:ENEURO.0091-16]
2. OT D1-MSNs encode attractive/appetitive odors; D2-MSNs encode
   aversive odors — odor-valence coding demonstrated optogenetically
   — [Murata Kanno Onuki et al. 2015, Nat Neurosci 18:912-920,
    "Mapping of learned odor-induced motivated behaviors in the
    mouse olfactory tubercle"]
3. OT projects to ventral pallidum continuing striatopallidal
   architecture; receives VTA DA — full mesolimbic-olfactory
   integration — [Heimer 2003, Trends Neurosci 26:69]
4. OT contributes to social odor recognition, food-odor reward,
   drug-conditioned odor cues — [Wesson Wilson 2010,
    Neurosci Biobehav Rev 35:655]
5. Islands of Calleja in OT — densely packed granule cells, distinct
   subdivision with sleep/dopamine modulation — [Fallon et al. 1983] [Millhouse 1986 Brain Res Rev 11:355]

INPUTS (from prior_results)
============================
- OlfactoryBulb.mob_mitral_drive
- OlfactoryBulb.piriform_relay
- PiriformCortex.pir_pyramidal_drive
- PiriformCortex.amygdala_relay
- VentralTegmentalDopamine.nac_shell_drive
- VentralTegmentalDopamine.vta_da_phasic
- BasolateralAmygdala.reward_engram_strength
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- ValenceTagger.social_context
- AppetiteNPYBalancer.energy_balance_signed

OUTPUTS (to brain_runner enrichment)
=====================================
- ot_drive (0.0-1.0): olfactory tubercle aggregate output
- ot_d1_appetitive (0.0-1.0): D1-MSN appetitive-odor encoding
- ot_d2_aversive (0.0-1.0): D2-MSN aversive-odor encoding
- ot_vp_relay (0.0-1.0): OT → ventral pallidum
- ot_lh_relay (0.0-1.0): OT → lateral hypothalamus motivated behavior
- odor_valence_bias (signed -1..+1): + appetitive, - aversive
- social_odor_recognition (0.0-1.0): social-odor pathway engagement
- ot_state (str): "quiet" | "appetitive_odor" | "aversive_odor" | "social_odor"

brain_runner enrichment:
    ot = all_results.get("OlfactoryTubercleStriatal", {})
    if ot:
        enrichments["brain_ot_drive"] = ot.get("ot_drive", 0.1)
        enrichments["brain_odor_valence_bias"] = ot.get("odor_valence_bias", 0.0)
        enrichments["brain_ot_vp_relay"] = ot.get("ot_vp_relay", 0.0)
        enrichments["brain_ot_state"] = ot.get("ot_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class OlfactoryTubercleStriatal(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="OlfactoryTubercleStriatal",
            human_analog="Olfactory tubercle (ventral striatal olfactory-reward hub)",
            layer="foundational",
        )
        self.state.setdefault("ot_drive", self.BASELINE)
        self.state.setdefault("ot_d1_appetitive", 0.0)
        self.state.setdefault("ot_d2_aversive", 0.0)
        self.state.setdefault("ot_vp_relay", 0.0)
        self.state.setdefault("ot_lh_relay", 0.0)
        self.state.setdefault("odor_valence_bias", 0.0)
        self.state.setdefault("social_odor_recognition", 0.0)
        self.state.setdefault("ot_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ot_drive_target(self, mob: float, piriform: float, vta_shell: float,
                          reward_engram: float) -> float:
        """OT aggregate drive — fed by olfactory + VTA DA + reward engram."""
        target = self.BASELINE + mob * 0.3 + piriform * 0.3
        target += vta_shell * 0.2 + reward_engram * 0.15
        return min(1.0, target)

    def _ot_d1_target(self, ot: float, sign: int, valence: float, vta_phasic: float,
                      energy: float) -> float:
        """D1-MSN appetitive encoding (Murata 2015)."""
        if sign <= 0 or valence < 0.20:
            return ot * 0.1
        target = ot * 0.4 + valence * 0.3 + max(0.0, vta_phasic) * 0.2
        if energy < -0.20:
            target += abs(energy) * 0.2  # hunger amplifies food odor appetitive
        return min(1.0, target)

    def _ot_d2_target(self, ot: float, sign: int, valence: float, piriform_amyg: float) -> float:
        """D2-MSN aversive encoding (Murata 2015)."""
        if sign >= 0 or valence < 0.20:
            return ot * 0.1
        target = ot * 0.4 + valence * 0.3 + piriform_amyg * 0.3
        return min(1.0, target)

    def _vp_relay(self, d1: float, d2: float, ot: float) -> float:
        """OT → ventral pallidum."""
        return min(1.0, d1 * 0.5 + d2 * 0.3 + ot * 0.2)

    def _lh_relay(self, ot: float, d1: float, energy: float) -> float:
        """OT → LH motivated behavior."""
        target = ot * 0.4 + d1 * 0.4
        if energy < -0.30:
            target += abs(energy) * 0.2
        return min(1.0, target)

    def _odor_valence_bias(self, d1: float, d2: float) -> float:
        """+ appetitive vs - aversive bias from D1 vs D2 balance."""
        return max(-1.0, min(1.0, d1 - d2))

    def _social_odor(self, mob: float, social: bool, oxytocin: float = 0.0) -> float:
        """Social-odor recognition pathway."""
        if not social:
            return 0.0
        return min(1.0, mob * 0.5 + oxytocin * 0.3)

    def _classify_state(self, d1: float, d2: float, social: float, ot: float) -> str:
        if social > 0.40:
            return "social_odor"
        if d1 > 0.35 and d1 > d2:
            return "appetitive_odor"
        if d2 > 0.35:
            return "aversive_odor"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob = prior.get("OlfactoryBulb", {})
        mob = float(ob.get("mob_mitral_drive", 0.0))
        ob_pir = float(ob.get("piriform_relay", 0.0))

        pir = prior.get("PiriformCortex", {})
        pir_drive = float(pir.get("pir_pyramidal_drive", 0.0))
        pir_amyg = float(pir.get("amygdala_relay", 0.0))

        # Use either piriform mechanism or OB→pir relay as input
        piriform_in = max(pir_drive, ob_pir)

        vta = prior.get("VentralTegmentalDopamine", {})
        vta_shell = float(vta.get("nac_shell_drive", 0.30))
        vta_phasic = float(vta.get("vta_da_phasic", 0.0))

        bla = prior.get("BasolateralAmygdala", {})
        reward_engram = float(bla.get("reward_engram_strength", 0.0))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        social = bool(valence.get("social_context", False))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy = float(appetite.get("energy_balance_signed", 0.0))

        # --- OT drive ---
        ot_target = self._ot_drive_target(mob, piriform_in, vta_shell, reward_engram)
        prev_ot = float(self.state.get("ot_drive", self.BASELINE))
        new_ot = self._smooth(prev_ot, ot_target)

        # --- D1 / D2 ---
        d1_target = self._ot_d1_target(new_ot, sign, valence_intensity, vta_phasic, energy)
        d2_target = self._ot_d2_target(new_ot, sign, valence_intensity, pir_amyg)
        prev_d1 = float(self.state.get("ot_d1_appetitive", 0.0))
        prev_d2 = float(self.state.get("ot_d2_aversive", 0.0))
        new_d1 = self._smooth(prev_d1, d1_target)
        new_d2 = self._smooth(prev_d2, d2_target)

        # --- Outputs ---
        vp = self._vp_relay(new_d1, new_d2, new_ot)
        lh = self._lh_relay(new_ot, new_d1, energy)
        valence_bias = self._odor_valence_bias(new_d1, new_d2)
        social_odor = self._social_odor(mob, social)

        state = self._classify_state(new_d1, new_d2, social_odor, new_ot)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ot_drive"] = round(new_ot, 4)
        self.state["ot_d1_appetitive"] = round(new_d1, 4)
        self.state["ot_d2_aversive"] = round(new_d2, 4)
        self.state["ot_vp_relay"] = round(vp, 4)
        self.state["ot_lh_relay"] = round(lh, 4)
        self.state["odor_valence_bias"] = round(valence_bias, 4)
        self.state["social_odor_recognition"] = round(social_odor, 4)
        self.state["ot_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ot_drive": round(new_ot, 4),
            "ot_d1_appetitive": round(new_d1, 4),
            "ot_d2_aversive": round(new_d2, 4),
            "ot_vp_relay": round(vp, 4),
            "ot_lh_relay": round(lh, 4),
            "odor_valence_bias": round(valence_bias, 4),
            "social_odor_recognition": round(social_odor, 4),
            "ot_state": state,
        }
