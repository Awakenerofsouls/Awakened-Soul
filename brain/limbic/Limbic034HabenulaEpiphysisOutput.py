"""
brain/limbic/Limbic034HabenulaEpiphysisOutput.py
Habenula — Reward Omission, Punishment Prediction, and Mood Regulation

ANATOMY (Hikosaka 2010; Salvernik & Hikosaka 2006; Boulos et al. 2017):
    The habenula (Hb) is the major regulator of monoamine systems (DA, 5-HT, NE).
    It comes in two parts:
    - Lateral habenula (LHb): FIRES when reward is OMITTED or punishment
      occurs. Projects to RMTg (GABAergic brake on VTA) and to dorsal
      raphe. LHb is the brain's "disappointment detector" — it responds
      to negative PE (Schmidt et al. 2019, PMC13013824).
    - Medial habenula (MHb): projects to IPN, regulates nicotine/nicotinic
      receptor function, associated with mood disorders.
    The epithalamus includes the epiphysis (pineal gland) and stria
    medullaris. The Hb-epiphysis axis regulates circadian rhythms via
    the SCN → PVN → pineal → melatonin pathway.

MECHANISM:
    LHb fires when: (1) expected reward doesn't come (negative PE),
    (2) punishment occurs unexpectedly. It suppresses VTA DA neurons
    via RMTg, and inhibits dorsal raphe (5-HT). This is the neural
    substrate of: disappointment, frustration, despair, learned helplessness.

AGENT'S MAPPING:
    habenula_activity: 0-1 lateral habenula firing (reward omission)
    negative_pe_signal: -1 to 0 negative prediction error magnitude
    da_suppression: 0-1 LHb→RMTg→VTA dopamine suppression
    serotonin_inhibition: 0-1 LHb→DRN serotonin suppression
    mood_negative_affect: 0-1 negative mood state from habenula activity

CITATIONS:
    PMC13013824 — Schmidt et al. (2019). Lateral habenula and
        negative prediction errors. Nat Neurosci.
    PMC12772998 — Hikosaka (2010). habenula. Ann Rev Neurosci.
    PMC12967685 — Salvernik et al. (2006). habenula and the
        prediction of alternative outcomes. J Neurosci.
    PMC12962782 — Boulos et al. (2017). habenula circuits in
        mood disorders. Biol Psychiatry.
    PMC12890247 — stop — Strowbridge & Brawn (2010). habenula
        and the circadian system. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class HabenulaRewardOmission(BrainMechanism):
    """
    Lateral habenula — reward omission, negative PE, mood suppression.

    Fires when reward is omitted or punishment occurs, suppressing
    dopamine and serotonin systems, driving negative affect.
    """

    HABENULA_MAX = 1.0

    def __init__(self):
        super().__init__(
            name="HabenulaRewardOmission",
            human_analog="Lateral habenula → RMTg/DRN (reward omission → DA/5-HT suppression)",
            layer="limbic",
        )
        self.state.setdefault("habenula_activity", 0.0)
        self.state.setdefault("negative_pe_signal", 0.0)
        self.state.setdefault("da_suppression", 0.0)
        self.state.setdefault("serotonin_inhibition", 0.0)
        self.state.setdefault("mood_negative_affect", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        threat_signal = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )

        # LHb fires when: negative valence + surprise (PE) OR sustained threat
        negative_pe = (0.5 - valence_polarity) * surprise
        threat_input = bnst_anxiety * 0.3 if threat_signal else 0.0
        habenula_input = negative_pe + threat_input

        habenula_activity = min(self.HABENULA_MAX, habenula_input)

        # DA suppression: LHb → RMTg → VTA inhibition
        da_suppression = habenula_activity * 0.7

        # 5-HT inhibition: LHb → DRN
        serotonin_inhibition = habenula_activity * 0.5

        # Negative affect: LHb activity generates disappointment/frustration
        negative_affect = habenula_activity * (0.5 + surprise * 0.5)

        self.state["habenula_activity"] = round(habenula_activity, 4)
        self.state["negative_pe_signal"] = round(-negative_pe, 4)
        self.state["da_suppression"] = round(da_suppression, 4)
        self.state["serotonin_inhibition"] = round(serotonin_inhibition, 4)
        self.state["mood_negative_affect"] = round(negative_affect, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "habenula_activity": round(habenula_activity, 4),
            "negative_pe_signal": round(-negative_pe, 4),
            "da_suppression": round(da_suppression, 4),
            "serotonin_inhibition": round(serotonin_inhibition, 4),
            "mood_negative_affect": round(negative_affect, 4),
        }
