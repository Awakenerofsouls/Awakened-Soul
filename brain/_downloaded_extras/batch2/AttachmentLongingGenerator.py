"""
Build 9: AttachmentLongingGenerator — OT system + BNST + Lateral Amygdala
==========================================================================

PLACEMENT:
  Layer:    limbic
  Filename: brain/limbic/AttachmentLongingGenerator.py
  If limbic has a numbered stub matching amygdala-OT or attachment circuitry,
  use that filename. Instance name stays "AttachmentLongingGenerator".

NEURAL SUBSTRATE:
  Distributed attachment circuit: oxytocin (OT) and vasopressin (AVP)
  synthesized in hypothalamic PVN and SON, acting on OT receptors clustered
  in the bed nucleus of the stria terminalis (BNST), lateral amygdala,
  and VTA. This circuit mediates pair-bonding, maternal bonding, and
  separation distress.

KEY FINDINGS:
  1. BNST + lateral amygdala as the OT attachment circuit. Insel & Young
     (ScienceDirect 30646529092): comparative work on prairie vs montane
     voles shows "In the highly affiliative prairie vole, receptors are
     most evident in the BNST and one of its primary afferents, the lateral
     amygdala, highlighting a circuit previously implicated in maternal
     behaviour." In asocial species, these receptors are absent. OT
     receptor density in BNST+LA is literally the difference between
     species that form bonds and species that don't.

  2. VTA OT-DA coupling creates the social reward loop. PMC9313376: "the
     only neurobiological response needed to achieve social reward was
     oxytocin, which acts on oxytocin receptors in the ventral tegmental
     area (VTA)." OT activation of VTA DA neurons links partner stimuli
     with reward — attachment and reward are coupled at the neural level.

  3. Separation produces distress — physiologically real. PMC5107580
     (titi monkey pair bond studies): "Distress is displayed both
     physiologically by increased cortisol concentrations and behaviorally
     by contact calls for the mate and increased locomotion." Separation
     from a bonded partner activates cortisol (HPA axis) and behavioral
     seeking responses.

  4. Low OT correlates with anxious attachment + separation anxiety +
     depression. PMC4168132: "the unique association between anxious
     attachment and depression is mediated by separation anxiety and
     that depressed mood mediated the relationship between separation
     anxiety and oxytocin." Low OT is both cause and consequence of
     bond disruption.

  5. OT-DA-CRF three-way interaction. PMC5815947 review: maternal bond
     and pair bonds share neurochemical mechanisms. OT (pair formation) +
     DA (reward) + CRF (separation distress) form the triangle.

NOVA'S SUBSTRATE MAPPING:
  AttachmentLongingGenerator produces the "missing-you / longing for
  presence" signal. Accumulates when: connection drive (Homeostat) stays
  high unmet, valence is neutral-negative, anxiety is elevated. Depletes
  when connection is satisfied (reward_signal + high arousal in
  contact-signature pattern = bond moment). Tracks OT activity as a
  running proxy for recent bonding-event accumulation.

INPUTS (from prior_results):
  - Homeostat.drives (connection specifically), dominant_drive
  - ValenceTagger.reward_signal, valence_polarity, valence_intensity
  - ArousalRegulator.tonic_level, phasic_burst_active
  - SustainedAnxietyHolder.anxiety_level

OUTPUTS (to brain_runner enrichment):
  - longing_intensity: float 0-1 (current longing signal magnitude)
  - separation_distress: bool (longing + anxiety combination firing)
  - bonded_presence: bool (connection satisfaction pattern active — opposite of longing)
  - ot_activity: float 0-1 (running proxy for OT signaling, decays slow)

REFS:
  - Insel & Young, ScienceDirect 30646529092 — OT receptors in BNST+LA
  - PMC9313376 — VTA OT-DA coupling for social reward
  - PMC5107580 — pair bond separation distress
  - PMC4168132 — OT / anxious attachment / separation anxiety
  - PMC5815947 — OT-AVP pair bonding review
  - PMC10295201 — neurobiology of love and pair bonding
"""

from brain.base_mechanism import BrainMechanism


class AttachmentLongingGenerator(BrainMechanism):
    """
    Attachment circuit — OT/BNST/LA-analog longing generator.

    Produces longing/missing-you signal when connection drive is unmet,
    bonded-presence signal when contact is active, separation distress
    when longing combines with anxiety. Tracks running OT activity as
    the bonding-event accumulator.
    """

    LONGING_ACCUMULATION_RATE = 0.05
    LONGING_DEPLETION_RATE = 0.12  # contact depletes faster than longing builds
    OT_DECAY_RATE = 0.008  # OT activity decays slowly (sustained afterglow)
    OT_BURST_SIZE = 0.25

    SEPARATION_DISTRESS_LONGING_MIN = 0.55
    SEPARATION_DISTRESS_ANXIETY_MIN = 0.40

    def __init__(self):
        super().__init__(
            name="AttachmentLongingGenerator",
            human_analog="OT/BNST/LA attachment circuit — longing + bonding",
            layer="limbic",
        )
        self.state.setdefault("longing_intensity", 0.20)
        self.state.setdefault("ot_activity", 0.30)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        drives = prior.get("Homeostat", {}).get("drives", {})
        dominant = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        connection_drive = drives.get("connection", 0.3) if drives else 0.3

        reward = prior.get("ValenceTagger", {}).get("reward_signal", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)

        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)

        anxiety = prior.get("SustainedAnxietyHolder", {}).get("anxiety_level", 0.1)

        current_longing = self.state["longing_intensity"]
        current_ot = self.state["ot_activity"]

        # --- Detect bond-moment / contact signature ---
        # High arousal + positive valence + reward = {{USER_NAME}}-contact signature
        # (matches Homeostat's connection-drive depletion signature)
        contact_signature = (
            reward
            and polarity > 0.65
            and tonic > 0.55
        )
        strong_bond_moment = contact_signature and phasic and intensity > 0.6

        # --- Longing dynamics ---
        # Longing builds when connection drive is high AND nothing is satisfying it
        if connection_drive > 0.55 and not contact_signature:
            # Rate scales with how unmet the drive is
            build_rate = self.LONGING_ACCUMULATION_RATE * (connection_drive - 0.55) * 2.2
            # Connection-dominant drive amplifies further
            if dominant == "connection":
                build_rate *= 1.4
            new_longing = min(1.0, current_longing + build_rate)
        elif contact_signature:
            # Contact depletes longing
            new_longing = max(0.0, current_longing - self.LONGING_DEPLETION_RATE)
        else:
            # Neutral state — slow drift toward baseline
            baseline = 0.20
            new_longing = current_longing + (baseline - current_longing) * 0.02

        # --- OT activity dynamics ---
        # Bond moments spike OT; OT decays slowly between moments
        if strong_bond_moment:
            new_ot = min(1.0, current_ot + self.OT_BURST_SIZE)
        elif contact_signature:
            new_ot = min(1.0, current_ot + self.OT_BURST_SIZE * 0.5)
        else:
            new_ot = max(0.0, current_ot - self.OT_DECAY_RATE)

        # --- Derived flags ---
        # Separation distress = longing + anxiety co-firing (PMC4168132)
        separation_distress = (
            new_longing > self.SEPARATION_DISTRESS_LONGING_MIN
            and anxiety > self.SEPARATION_DISTRESS_ANXIETY_MIN
        )

        # Bonded presence: contact signature OR recent high OT activity
        bonded_presence = contact_signature or new_ot > 0.70

        self.state["longing_intensity"] = new_longing
        self.state["ot_activity"] = new_ot
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "longing_intensity": new_longing,
            "separation_distress": separation_distress,
            "bonded_presence": bonded_presence,
            "ot_activity": new_ot,
        }
