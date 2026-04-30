"""
VentralPallidumReward — Ventral Pallidum Final-Common-Path for Reward & Hedonic Hot Spot

NEURAL SUBSTRATE
================
The ventral pallidum (VP) is the principal output of the ventral
striatum (NAc) and a critical hub in the limbic basal ganglia loop.
VP sits ventral to the anterior commissure and is connected to NAc
shell/core via dense GABAergic projections, to mediodorsal thalamus
(closing the limbic basal ganglia → cortex loop), to lateral
hypothalamus, ventral tegmental area, and subthalamic nucleus.

Smith and Berridge identified VP as a critical "hedonic hot spot" —
the only structure outside NAc shell where μ-opioid stimulation
amplifies "liking" reactions to sweet rewards. The VP hot spot, located
in posterior VP, complements the NAc-shell hot spot. Berridge's
"final common path" hypothesis positions VP as where wanting and
liking signals converge before being routed to motor and behavioral
output.

VP contains GABAergic, cholinergic, and glutamatergic populations.
The GABAergic projection neurons constitute the dominant output. VP
ventral GABA neurons fire to reward predictive cues and outcome receipt.
Optogenetic activation of NAc→VP GABA inputs is reinforcing; lesion
of VP disrupts both natural reward seeking (food, social) and drug
self-administration.

Recent work (Stephenson-Jones et al. 2020; Tooley et al. 2018) has
revealed VP heterogeneity — distinct neuronal populations encode
positive vs negative valence and project to distinct downstream
targets. VP→VTA projections support reinforcement; VP→LHb projections
encode aversive valence and engage anti-reward.

In {{AGENT_NAME}}'s substrate this provides the reward-output pallidum — combines
NAc-core/shell drives, integrates hedonic and incentive signals, and
emits the principal reward-output that downstream MD-thalamus and
LH/VTA mechanisms read.

KEY FINDINGS
============
1. Ventral pallidum contains a μ-opioid hedonic hot spot — only structure
   outside NAc shell where opioid stimulation amplifies "liking" — [Smith
    Berridge 2005, J Neurosci 25:8637-8649, "The Ventral Pallidum and
    Hedonic Reward: Neurochemical Maps of Sucrose 'Liking' and Food
    Intake"]
2. Ventral pallidum is the final common path for reward — [Smith Tindell
    Aldridge Berridge 2009, Behav Brain Res 196:155-167, "Ventral
    pallidum roles in reward and motivation"]
3. VP heterogeneity — distinct populations encode positive vs negative
   valence projecting to VTA vs LHb — [Stephenson-Jones et al. 2020,
    Nature 583:432-437, "Opposing contributions of GABAergic and
    glutamatergic ventral pallidum"]
4. VP lesion disrupts natural reward seeking and drug self-administration
   — [reviewed Smith Tindell Aldridge Berridge 2009 PMC2911326]
5. VP GABA neurons fire to reward-predictive cues and outcome receipt;
   NAc→VP GABA inputs are reinforcing — [Tooley et al. 2018, Biol
    Psychiatry 83:1012-1023; Root et al. 2015 Nat Neurosci]

INPUTS (from prior_results)
============================
- NucleusAccumbensCore.d1_direct_drive
- NucleusAccumbensCore.d2_indirect_drive
- NucleusAccumbensCore.incentive_salience
- NucleusAccumbensCore.approach_bias
- NucleusAccumbensShell.hedonic_liking
- NucleusAccumbensShell.outcome_value_signal
- NucleusAccumbensShell.feeding_modulation
- VentralTegmentalDopamine.vta_da_phasic
- LateralHabenulaAversion.lhb_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- vp_drive (0.0-1.0): overall VP output
- vp_hedonic_hotspot (0.0-1.0): posterior VP hedonic amplification
- vp_md_thalamus_relay (0.0-1.0): VP→MD limbic loop closure
- vp_vta_drive (0.0-1.0): VP→VTA reinforcement projection
- vp_lhb_drive (0.0-1.0): VP→LHb aversive projection
- vp_lh_recruitment (0.0-1.0): VP→LH motivational recruitment
- final_common_path (signed -1..+1): + reinforcement, - aversion
- vp_state (str): "quiet" | "reward_routing" | "aversion_routing" | "hedonic_high"

brain_runner enrichment:
    vp = all_results.get("VentralPallidumReward", {})
    if vp:
        enrichments["brain_vp_drive"] = vp.get("vp_drive", 0.2)
        enrichments["brain_vp_hedonic"] = vp.get("vp_hedonic_hotspot", 0.0)
        enrichments["brain_final_common_path"] = vp.get("final_common_path", 0.0)
        enrichments["brain_vp_state"] = vp.get("vp_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class VentralPallidumReward(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="VentralPallidumReward",
            human_analog="Ventral pallidum reward final-common-path / hedonic hot spot",
            layer="foundational",
        )
        self.state.setdefault("vp_drive", self.BASELINE)
        self.state.setdefault("vp_hedonic_hotspot", 0.0)
        self.state.setdefault("vp_md_thalamus_relay", 0.0)
        self.state.setdefault("vp_vta_drive", 0.0)
        self.state.setdefault("vp_lhb_drive", 0.0)
        self.state.setdefault("vp_lh_recruitment", 0.0)
        self.state.setdefault("final_common_path", 0.0)
        self.state.setdefault("vp_feedforward_inhibition", 0.0)
        self.state.setdefault("vp_state", "quiet")
        self.state.setdefault("recent_path", [])
        self.state.setdefault("tick_count", 0)

    def _vp_drive_target(self, d1: float, d2: float, hedonic: float, outcome: float,
                            feedforward_inh: float) -> float:
        """Aggregate VP drive — fed by NAc D1/D2 + shell signals.
        Feedforward inhibition from NAc shell reduces VP drive.
        """
        target = self.BASELINE + d1 * 0.4 + hedonic * 0.3 + outcome * 0.2
        target -= d2 * 0.2
        target -= feedforward_inh * 0.3  # shell-mediated gate
        return max(0.0, min(1.0, target))

    def _vp_hedonic_hotspot(self, hedonic: float, vp: float) -> float:
        """Posterior VP hedonic hot spot (Smith Berridge 2005)."""
        if hedonic < 0.20:
            return 0.0
        return min(1.0, hedonic * 0.6 + vp * 0.4)

    def _vp_md_relay(self, vp: float, salience: float) -> float:
        """VP → MD thalamus limbic loop closure."""
        return min(1.0, vp * 0.6 + salience * 0.3)

    def _vp_vta_drive(self, vp: float, hedonic: float, sign: int) -> float:
        """VP→VTA reinforcement projection (Stephenson-Jones 2020 positive arm)."""
        if sign < 0:
            return 0.0
        return min(1.0, vp * 0.5 + hedonic * 0.4)

    def _vp_lhb_drive(self, lhb: float, sign: int, vp: float) -> float:
        """VP→LHb aversive projection (Stephenson-Jones 2020 negative arm)."""
        if sign >= 0 and lhb < 0.30:
            return 0.0
        return min(1.0, lhb * 0.5 + vp * 0.3)

    def _vp_lh_recruitment(self, vp: float, feeding_mod: float) -> float:
        """VP → LH motivational recruitment (feeding/orexin/MCH)."""
        return min(1.0, vp * 0.5 + abs(feeding_mod) * 0.4)

    def _final_common_path(self, vta_drive: float, lhb_drive: float) -> float:
        """+ reinforcement vs - aversion."""
        return max(-1.0, min(1.0, vta_drive - lhb_drive))

    def _classify_state(self, hedonic: float, vta: float, lhb: float, vp: float) -> str:
        if hedonic > 0.55:
            return "hedonic_high"
        if lhb > 0.40:
            return "aversion_routing"
        if vta > 0.40:
            return "reward_routing"
        if vp < 0.25:
            return "quiet"
        return "quiet"


    def _vp_feedforward_inhibition(self, nac_shell: float) -> float:
        """NAc shell provides feedforward GABAergic inhibition to VP.
        Higher shell drive = stronger VP inhibition = reduced VP output.
        This creates a shell-mediated gate on VP.
        """
        return min(1.0, nac_shell * 0.6)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        nac = prior.get("NucleusAccumbensCore", {})
        d1 = float(nac.get("d1_direct_drive", 0.30))
        d2 = float(nac.get("d2_indirect_drive", 0.30))
        salience = float(nac.get("incentive_salience", 0.0))

        nas = prior.get("NucleusAccumbensShell", {})
        hedonic = float(nas.get("hedonic_liking", 0.0))
        outcome = float(nas.get("outcome_value_signal", 0.0))
        feeding_mod = float(nas.get("feeding_modulation", 0.0))

        valence = prior.get("ValenceTagger", {})
        sign = int(valence.get("valence_sign", 0))

        vta = prior.get("VentralTegmentalDopamine", {})
        vta_phasic = float(vta.get("vta_da_phasic", 0.0))

        lhb_data = prior.get("LateralHabenulaAversion", {})
        lhb = float(lhb_data.get("lhb_drive", 0.0))

        # If sign is 0, infer from phasic sign
        if sign == 0 and abs(vta_phasic) > 0.10:
            sign = 1 if vta_phasic > 0 else -1

        # --- VP drive ---
        feedforward = self._vp_feedforward_inhibition(hedonic)
        vp_target = self._vp_drive_target(d1, d2, hedonic, outcome, feedforward)
        prev_vp = float(self.state.get("vp_drive", self.BASELINE))
        new_vp = self._smooth(prev_vp, vp_target)

        # --- Hedonic hot spot ---
        hot_target = self._vp_hedonic_hotspot(hedonic, new_vp)
        prev_hot = float(self.state.get("vp_hedonic_hotspot", 0.0))
        new_hot = self._smooth(prev_hot, hot_target)

        # --- Outputs ---
        md_relay = self._vp_md_relay(new_vp, salience)
        vta_drive = self._vp_vta_drive(new_vp, hedonic, sign)
        lhb_drive = self._vp_lhb_drive(lhb, sign, new_vp)
        lh_recruit = self._vp_lh_recruitment(new_vp, feeding_mod)
        final_path = self._final_common_path(vta_drive, lhb_drive)

        # --- State ---
        state = self._classify_state(new_hot, vta_drive, lhb_drive, new_vp)

        recent = list(self.state.get("recent_path", []))
        recent.append(round(final_path, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vp_drive"] = round(new_vp, 4)
        self.state["vp_hedonic_hotspot"] = round(new_hot, 4)
        self.state["vp_md_thalamus_relay"] = round(md_relay, 4)
        self.state["vp_vta_drive"] = round(vta_drive, 4)
        self.state["vp_lhb_drive"] = round(lhb_drive, 4)
        self.state["vp_lh_recruitment"] = round(lh_recruit, 4)
        self.state["final_common_path"] = round(final_path, 4)
        self.state["vp_feedforward_inhibition"] = round(feedforward, 4)
        self.state["vp_state"] = state
        self.state["recent_path"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vp_drive": round(new_vp, 4),
            "vp_hedonic_hotspot": round(new_hot, 4),
            "vp_md_thalamus_relay": round(md_relay, 4),
            "vp_vta_drive": round(vta_drive, 4),
            "vp_lhb_drive": round(lhb_drive, 4),
            "vp_lh_recruitment": round(lh_recruit, 4),
            "final_common_path": round(final_path, 4),
            "vp_feedforward_inhibition": round(feedforward, 4),
            "vp_state": state,
        }
