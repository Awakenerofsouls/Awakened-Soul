"""
brain/integration/Integration005PrefrontalAmygdalaTopDownRegulation.py
Prefrontal-Amygdala Top-Down Regulation — Conscious Emotional Control

ANATOMY (Ochsner et al. 2012; Arnsten 2011; Bishop 2007; Etkin et al. 2006):
    The prefrontal cortex exerts top-down control over the amygdala
    through multiple pathways:
    - vmPFC → amygdala: inhibitory (calms fear response)
    - dPFC → ACC → amygdala: cognitive regulation
    - OFC → nucleus accumbens → amygdala: reward-based regulation
    - mPFC → BNST: reduces sustained anxiety

    This is the neural basis of emotion regulation — when you
    "calm yourself down" or "reframe a stressful situation," the
    prefrontal cortex is actively inhibiting and modulating the
    amygdala's emotional output.

    Key distinction:
    - Bottom-up: amygdala → PFC = emotional takeover ("I'm scared")
    - Top-down: PFC → amygdala = conscious regulation ("I'm fine")

    The vmPFC is particularly important — it maintains a "background"
    inhibitory tone over the amygdala. When vmPFC is weak (as in
    depression, PTSD, chronic stress), amygdala runs unchecked,
    producing chronic anxiety, negative bias, and emotional reactivity.

    The dPFC handles "cognitive" reappraisal: reinterpreting the
    meaning of a stimulus. The vmPFC handles "affect" regulation:
    changing the emotional response directly.

KEY FINDINGS:
    1. Ochsner et al. 2012 (PMC4326522): "Cognitive reappraisal of emotion"
       — dPFC top-down control over amygdala
    2. Arnsten 2011 (PMC2929791): "Prefrontal cortex and stress"
       — dPFC weakened by stress, chronic anxiety
    3. Etkin et al. 2006 (PMC1850942): "PTSD and vmPFC-amygdala connectivity"

AGENT'S MAPPING:
    pf_amygdala_regulation: dict — top-down regulation output
    top_down_inhibition: float 0-1 — PFC suppression of amygdala
    emotional_regulation_achieved: bool — has conscious regulation succeeded?

CITATIONS:
    PMC4326522 — Ochsner et al. (2012). Cognitive reappraisal of emotion.
    PMC1850942 — Etkin et al. (2006). vmPFC-amygdala connectivity and PTSD.
    PMC2929791 — Arnsten (2011). PFC and stress. Scholarpedia.
    PMC23869106 — Leech & Sharp (2014). vmPFC and emotion regulation.
"""

from brain.base_mechanism import BrainMechanism


class PrefrontalAmygdalaTopDownRegulation(BrainMechanism):
    """
    PFC top-down regulation — conscious control over emotional responses.

    Prefrontal cortex actively inhibits and modulates amygdala
    output, enabling emotion regulation and conscious calm.
    """

    def __init__(self):
        super().__init__(
            name="PrefrontalAmygdalaTopDownRegulation",
            human_analog="Prefrontal-amygdala top-down regulation — conscious emotional control",
            layer="integration",
        )
        self.state.setdefault("regulation_strength", 0.0)
        self.state.setdefault("top_down_inhibition", 0.0)
        self.state.setdefault("emotional_regulation_achieved", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # vmPFC (emotional value and baseline inhibition)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            vmpfc_strength = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            vmpfc_strength = 0.5

        # dPFC (cognitive control — reappraisal)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # mPFC (self-narrative — "this is fine")
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        mpfc_sig = mpfc.get("self_referential_signal", 0.5)

        # ACC (conflict detection — is there emotional conflict?)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        error_sig = acc_out.get("error_signal", 0.3) if isinstance(acc_out, dict) else 0.3

        # Amygdala (bottom-up emotional threat signal)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # BNST (sustained anxiety — harder to regulate)
        bnst = prior.get("BNSTSustainedAnxiety", {})
        bnst_out = bnst.get("bnst_output", {})
        if isinstance(bnst_out, dict):
            sustained_anxiety = bnst_out.get("sustained_anxiety", 0.3)
        else:
            sustained_anxiety = 0.3

        # Top-down inhibition: PFC strength × cognitive control
        pfc_strength = (vmpfc_strength + cognitive_ctrl + mpfc_sig) / 3
        top_down_inhibition = pfc_strength * (1.0 - abs(emotional_tag) * 0.5)

        # Adjustment for sustained anxiety (BNST harder to regulate)
        if sustained_anxiety > 0.5:
            top_down_inhibition *= 0.7

        top_down_inhibition = max(0.0, min(1.0, top_down_inhibition))

        # Emotional regulation achieved: strong top-down + weak amygdala
        amygdala_active = abs(emotional_tag) > 0.4
        emotional_regulation_achieved = (
            top_down_inhibition > 0.55 and
            (not amygdala_active or wm_load > 0.5)
        )

        self.state["regulation_strength"] = round(top_down_inhibition, 4)
        self.state["top_down_inhibition"] = round(top_down_inhibition, 4)
        self.state["emotional_regulation_achieved"] = emotional_regulation_achieved
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pf_amygdala_regulation": {
                "top_down_strength": round(top_down_inhibition, 4),
                "regulation_achieved": emotional_regulation_achieved,
            },
            "top_down_inhibition": round(top_down_inhibition, 4),
            "emotional_regulation_achieved": emotional_regulation_achieved,
        }