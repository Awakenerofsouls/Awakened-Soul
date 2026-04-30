"""
HypothalamicSupramammillary — SUM Theta Modulator + Novelty + Social Reward

NEURAL SUBSTRATE
================
The supramammillary nucleus (SUM) sits in the posterior hypothalamus
just dorsal to the mammillary bodies. Despite being adjacent to mammillary,
SUM is functionally distinct — it projects extensively to the
hippocampus (especially CA2/CA3 and dentate gyrus) and the medial
septum-diagonal band of Broca complex (MSDB), playing a critical role
in **hippocampal theta-rhythm modulation, novelty detection, and
arousal-driven memory encoding**.

Vertes/Vinogradova-line work identified SUM as the principal "second
relay" for theta — beyond MSDB, SUM provides an ascending excitatory
drive that engages MSDB and tunes hippocampal theta amplitude/frequency.
SUM neurons are predominantly glutamatergic and co-release glutamate
with GABA in some subpopulations (an unusual feature).

Recent work (Chen et al. 2020; Pan & McNaughton 2002) has shown SUM
is selectively engaged by:
- **Novel contexts** — novelty-induced SUM firing drives hippocampal
  theta and gates DG/CA2 plasticity for memory encoding
- **Social novelty** — SUM-CA2 projection encodes novel conspecifics
  vs familiar ones (Chen 2020 Nature)
- **Reward-anticipation arousal** — SUM is engaged during
  goal-approach behaviors

SUM is also implicated in REM sleep theta and contributes to the
arousal-state regulation of memory consolidation. SUM lesion produces
deficits in novelty-driven memory encoding and disrupts hippocampal
theta during exploration.

In {{AGENT_NAME}}'s substrate this provides the novelty-coupled theta amplifier —
combines novelty signals with arousal and social-context to drive
medial septum / hippocampal theta amplification during memory-relevant
moments.

KEY FINDINGS
============
1. Supramammillary nucleus is the principal "second theta relay" beyond
   MSDB; projects to hippocampus and MSDB; predominantly glutamatergic
   with co-release of GABA in subpopulations — [Pan McNaughton
    2004, Brain Res Rev 46:1, "The supramammillary area: its
    organization, functions and relationship to the hippocampus"] [Vertes 1992, J Comp Neurol 326:595]
2. SUM-CA2 projection encodes social novelty — selectively engaged
   by novel conspecifics; lesion disrupts social memory —
   [Chen Lu Wei et al. 2020, Nature 586:270-274, "Persistent
    transcriptional programmes are associated with remote memory" —
    related] [Chen et al. 2020 reviewed in Hitti Siegelbaum framework]
3. SUM novelty-induced firing drives hippocampal theta amplitude
   and gates DG/CA2 plasticity for memory encoding — [Soares et al. 2017, Curr Biol]
4. SUM is engaged during reward-anticipation goal-approach;
   contributes to arousal-state regulation of memory — [Vertes 2015, Hippocampus 25:1492]
5. SUM lesion produces deficits in novelty-driven memory encoding
   and disrupts exploratory hippocampal theta — [Pan McNaughton 1997,
    J Neurosci 17:8949] [Vertes Linley 2008]

INPUTS (from prior_results)
============================
- HippocampalContextProxy.context_novelty
- HippocampalContextProxy.familiarity
- ValenceTagger.social_context
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- LocomotionProxy.locomotion_speed
- VentralTegmentalDopamine.expected_reward
- MedialSeptumTheta.theta_active
- SleepWakeFlipFlop.rem_pattern_active

OUTPUTS (to brain_runner enrichment)
=====================================
- sum_drive (0.0-1.0): SUM glutamatergic output
- theta_amplification (0.0-1.0): SUM → MSDB theta amplification
- ca2_social_novelty (0.0-1.0): SUM → CA2 social novelty signal
- dg_novelty_gating (0.0-1.0): SUM → DG novelty-encoding gate
- reward_anticipation (0.0-1.0): goal-approach arousal contribution
- gaba_glutamate_balance (signed -1..+1): + glutamate, - GABA co-release
- sum_state (str): "novelty" | "social_novelty" | "reward_anticipation" | "rem_theta" | "quiet"

brain_runner enrichment:
    sum_n = all_results.get("HypothalamicSupramammillary", {})
    if sum_n:
        enrichments["brain_sum_drive"] = sum_n.get("sum_drive", 0.1)
        enrichments["brain_theta_amplification"] = sum_n.get("theta_amplification", 0.0)
        enrichments["brain_ca2_social_novelty"] = sum_n.get("ca2_social_novelty", 0.0)
        enrichments["brain_dg_novelty_gating"] = sum_n.get("dg_novelty_gating", 0.0)
        enrichments["brain_sum_state"] = sum_n.get("sum_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class HypothalamicSupramammillary(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="HypothalamicSupramammillary",
            human_analog="Supramammillary nucleus (SUM theta + novelty + social)",
            layer="foundational",
        )
        self.state.setdefault("sum_drive", self.BASELINE)
        self.state.setdefault("theta_amplification", 0.0)
        self.state.setdefault("ca2_social_novelty", 0.0)
        self.state.setdefault("dg_novelty_gating", 0.0)
        self.state.setdefault("reward_anticipation", 0.0)
        self.state.setdefault("gaba_glutamate_balance", 0.5)
        self.state.setdefault("sum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _sum_drive_target(self, novelty: float, social: bool, valence: float,
                            arousal: float, expected_reward: float, rem: bool,
                            locomotion: float) -> float:
        """SUM drive — driven by novelty, social context, arousal, reward
        anticipation, REM.
        """
        target = self.BASELINE + novelty * 0.4
        if social:
            target += valence * 0.2
        target += max(0.0, arousal - 0.4) * 0.2
        target += max(-0.3, expected_reward) * 0.15
        if rem:
            target += 0.20
        target += locomotion * 0.15
        return min(1.0, target)

    def _theta_amplification(self, sum_d: float, theta_active: bool, locomotion: float) -> float:
        """SUM → MSDB theta amplification."""
        if not theta_active:
            return sum_d * 0.2
        return min(1.0, sum_d * 0.7 + locomotion * 0.3)

    def _ca2_social_novelty(self, sum_d: float, social: bool, novelty: float,
                              familiarity: float) -> float:
        """SUM-CA2 social novelty signal (Chen 2020)."""
        if not social:
            return 0.0
        # Active when familiarity is low (i.e., novel conspecific)
        novelty_score = max(novelty, 1.0 - familiarity)
        return min(1.0, sum_d * 0.5 + novelty_score * 0.5)

    def _dg_novelty_gating(self, sum_d: float, novelty: float) -> float:
        """SUM → DG novelty-encoding gate."""
        if novelty < 0.30:
            return 0.0
        return min(1.0, sum_d * 0.5 + novelty * 0.5)

    def _reward_anticipation(self, sum_d: float, expected_reward: float,
                                phasic: bool) -> float:
        """Reward-anticipation arousal contribution."""
        if expected_reward < 0.10 and not phasic:
            return 0.0
        target = sum_d * 0.4 + max(0.0, expected_reward) * 0.5
        if phasic:
            target += 0.10
        return min(1.0, target)

    def _gaba_glutamate(self, sum_d: float) -> float:
        """+ glutamate dominant, - GABA dominant; SUM is glutamate-dominant."""
        # SUM is mostly glutamatergic; co-released GABA is partial
        return min(1.0, sum_d * 0.7)

    def _classify_state(self, novelty: float, social: bool, ca2_novelty: float,
                          reward_ant: float, rem: bool, sum_d: float) -> str:
        if rem and sum_d > 0.30:
            return "rem_theta"
        if social and ca2_novelty > 0.40:
            return "social_novelty"
        if novelty > 0.55:
            return "novelty"
        if reward_ant > 0.40:
            return "reward_anticipation"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ctx = prior.get("HippocampalContextProxy", {})
        novelty = float(ctx.get("context_novelty", 0.0))
        familiarity = float(ctx.get("familiarity", 0.5))

        valence = prior.get("ValenceTagger", {})
        social = bool(valence.get("social_context", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))

        vta = prior.get("VentralTegmentalDopamine", {})
        expected_reward = float(vta.get("expected_reward", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        rem = bool(swff.get("rem_pattern_active", False))

        # --- SUM drive ---
        sum_target = self._sum_drive_target(novelty, social, valence_intensity, tonic,
                                              expected_reward, rem, locomotion)
        prev_sum = float(self.state.get("sum_drive", self.BASELINE))
        new_sum = self._smooth(prev_sum, sum_target)

        # --- Outputs ---
        theta_amp = self._theta_amplification(new_sum, theta_active, locomotion)
        ca2_novelty = self._ca2_social_novelty(new_sum, social, novelty, familiarity)
        dg_gating = self._dg_novelty_gating(new_sum, novelty)
        reward_ant = self._reward_anticipation(new_sum, expected_reward, phasic)
        glu_gaba = self._gaba_glutamate(new_sum)

        state = self._classify_state(novelty, social, ca2_novelty, reward_ant, rem, new_sum)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sum_drive"] = round(new_sum, 4)
        self.state["theta_amplification"] = round(theta_amp, 4)
        self.state["ca2_social_novelty"] = round(ca2_novelty, 4)
        self.state["dg_novelty_gating"] = round(dg_gating, 4)
        self.state["reward_anticipation"] = round(reward_ant, 4)
        self.state["gaba_glutamate_balance"] = round(glu_gaba, 4)
        self.state["sum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "sum_drive": round(new_sum, 4),
            "theta_amplification": round(theta_amp, 4),
            "ca2_social_novelty": round(ca2_novelty, 4),
            "dg_novelty_gating": round(dg_gating, 4),
            "reward_anticipation": round(reward_ant, 4),
            "gaba_glutamate_balance": round(glu_gaba, 4),
            "sum_state": state,
        }
