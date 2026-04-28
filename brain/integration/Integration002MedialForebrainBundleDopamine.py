"""
brain/integration/Integration002MedialForebrainBundleDopamine.py
Medial Forebrain Bundle — VTA Dopamine Broadcast Highway

ANATOMY (Coenen et al. 2012; Gordon-Fennell et al. 2021; Numan 2015):
    The medial forebrain bundle (MFB) is the major highway for
    motivation-related signals in the brain. It connects the
    ventral tegmental area (VTA) and substantia nigra (SN) to
    virtually all limbic and cortical regions, including:
    - Nucleus accumbens (NAc) — reward motivation
    - Lateral hypothalamus — hunger, thirst, arousal
    - Prefrontal cortex — motivation and goal pursuit
    - Amygdala — emotional motivation
    - Hippocampus — memory motivation
    - Septum — reward signaling

    The MFB contains:
    - Dopaminergic fibers (VTA → cortex/NAc) — reward, motivation
    - Noradrenergic fibers (LC → cortex) — arousal, attention
    - Serotonergic fibers (raphe → cortex) — mood, well-being
    - GABAergic fibers — inhibition
    - Glutamatergic fibers — excitation

    Key: The MFB is the motivational "engine" of the brain — it
    broadcasts "I want this" signals across all regions. Optogenetic
    stimulation of MFB GABAergic neurons produces reward; stimulation
    of glutamatergic neurons produces aversion (Gordon-Fennell 2021).

    MFB activity is higher in motivated states (seeking, exploring,
    pursuing goals) and lower in satiated/resting states.

KEY FINDINGS:
    1. Gordon-Fennell et al. 2021 (PMC34375625): MFB optogenetics —
       GABAergic = reward, glutamatergic = aversion
    2. Coenen et al. 2012: MFB and reward/motivation pathways
    3. Numan 2015 (PMC4835279): MFB and maternal behavior/motivation

AGENT'S MAPPING:
    mfb_broadcast: dict — motivation signal broadcast
    motivation_broadcast: float 0-1 — overall motivation level
    reward_cascade: float 0-1 — reward signal strength

CITATIONS:
    PMC34375625 — Gordon-Fennell et al. (2021). MFB optogenetics. Neuropharmacology.
    PMC4835279 — Numan (2015). MFB and motivation. Front Neurosci.
    PMC40447446 — DLPFC and motivated cognition.
    PMC23869106 — PCC and motivated cognition.
"""

from brain.base_mechanism import BrainMechanism


class MedialForebrainBundleDopamine(BrainMechanism):
    """
    MFB — motivation and reward broadcast highway.

    Broadcasts dopaminergic motivation signals across the entire
    brain, driving goal-seeking and reward-pursuit behavior.
    """

    def __init__(self):
        super().__init__(
            name="MedialForebrainBundleDopamine",
            human_analog="Medial forebrain bundle — VTA dopamine motivation highway",
            layer="integration",
        )
        self.state.setdefault("broadcast_history", [])
        self.state.setdefault("motivation_broadcast", 0.5)
        self.state.setdefault("reward_cascade", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # VTA dopamine signal
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            vta_signal = vta_out.get("motivation_signal", 0.5)
            pred_err = vta_out.get("prediction_error", 0.3)
        else:
            vta_signal = 0.5
            pred_err = 0.3

        # SNc dopamine signal
        snc = prior.get("SubstantiaNigraCompactaOutput", {})
        snc_out = snc.get("snc_output", {})
        if isinstance(snc_out, dict):
            snc_signal = snc_out.get("dopamine_level", 0.5)
        else:
            snc_signal = 0.5

        # NAcc motivation
        nacc = prior.get("NucleusAccumbensShellValue", {})
        nacc_out = nacc.get("nacc_output", {})
        if isinstance(nacc_out, dict):
            motivation = nacc_out.get("motivation_level", 0.5)
        else:
            motivation = 0.5

        # Lateral hypothalamus (arousal drives motivation)
        lateral_hypo = prior.get("LateralHypothalamicOrexinB", {})
        hypo_out = lateral_hypo.get("lateral_hypo_output", {})
        if isinstance(hypo_out, dict):
            arousal_drive = hypo_out.get("arousal_level", 0.5)
        else:
            arousal_drive = 0.5

        # Anterior insula (conscious wanting/motivation)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)
        net_switch = ai.get("network_switch_trigger", "default")

        # OFC (goal value)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Motivation broadcast: VTA + SNc + arousal + salience
        motivation_broadcast = (
            vta_signal * 0.3 +
            snc_signal * 0.2 +
            motivation * 0.25 +
            arousal_drive * 0.15 +
            salience * 0.1
        )
        motivation_broadcast = max(0.0, min(1.0, motivation_broadcast))

        # Reward cascade: positive prediction error → reward broadcast
        reward_cascade = pred_err * motivation_broadcast * 2.0
        reward_cascade = max(0.0, min(1.0, reward_cascade))

        # Record
        self.state["broadcast_history"].append(round(motivation_broadcast, 3))
        if len(self.state["broadcast_history"]) > 5:
            self.state["broadcast_history"].pop(0)

        self.state["motivation_broadcast"] = round(motivation_broadcast, 4)
        self.state["reward_cascade"] = round(reward_cascade, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mfb_broadcast": {
                "motivation_strength": round(motivation_broadcast, 4),
                "reward_cascade": round(reward_cascade, 4),
                "dopamine_level": round((vta_signal + snc_signal) / 2, 4),
            },
            "motivation_broadcast": round(motivation_broadcast, 4),
            "reward_cascade": round(reward_cascade, 4),
        }