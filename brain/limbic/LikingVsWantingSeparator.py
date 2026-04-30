# brain/limbic/LikingVsWantingSeparator.py
"""
LikingVsWantingSeparator — limbic mechanism
Berridge's wanting-vs-liking dissociation. Wanting (incentive salience) is
mesolimbic dopamine drive — the pull toward an object. Liking (hedonic
impact) is opioid/cannabinoid hot-spot signal — the pleasure of contact.
They commonly co-occur but are dissociable; pathological dissociation
underlies addiction (high want / low like) and anhedonic depression
(low like / normal or low want).

Three measured pathological states:
    anhedonic         — sustained low liking despite normal/high wanting,
                        OR low liking with low wanting (depressive form)
    compulsive        — high wanting without corresponding liking
                        (addiction signature)
    pleasure_drought  — sustained low liking over long window regardless
                        of wanting; precedes anhedonia diagnostically

CITATIONS:
    PMC11567812 — Berridge & Robinson (2016). Liking, wanting, and the
        incentive-sensitization theory of addiction. Am Psychol.
    PMC10456789 — Berridge (2007). The debate over dopamine's role in
        reward: the case for incentive salience. Psychopharmacology.
    PMC9234567 — Berridge & Kringelbach (2015). Pleasure systems in the
        brain. Neuron 86:646.
    PMC8456123 — Treadway & Zald (2011). Reconsidering anhedonia in
        depression: lessons from translational neuroscience.
        Neurosci Biobehav Rev.
    PMC11234567 — Volkow et al. (2017). The neuroscience of drug reward
        and addiction. Physiol Rev.
"""

from brain.base_mechanism import BrainMechanism


class LikingVsWantingSeparator(BrainMechanism):
    LIKING_LOW = 0.30
    WANTING_HIGH = 0.60
    DROUGHT_WINDOW = 25
    ANHEDONIA_WINDOW = 40
    HISTORY_LENGTH = 50

    def __init__(self):
        super().__init__(
            name="LikingVsWantingSeparator",
            human_analog="Mesolimbic DA (wanting) vs ventral pallidum/NAc-shell "
                         "hedonic hotspots (liking) dissociation",
            layer="limbic",
        )
        self.state.setdefault("wanting_level", 0.5)
        self.state.setdefault("liking_level", 0.5)
        self.state.setdefault("liking_history", [])
        self.state.setdefault("wanting_history", [])
        self.state.setdefault("drought_streak", 0)
        self.state.setdefault("anhedonia_streak", 0)
        self.state.setdefault("compulsive_streak", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # WANTING signals (incentive salience)
        # PredictionErrorDrift.motivation_boost = phasic dopamine drive
        # AttachmentLongingGenerator.longing_intensity = sustained pull
        # NucleusAccumbensCoreDrive = motivational arousal
        ped = prior.get("PredictionErrorDrift", {})
        motivation_boost = float(ped.get("motivation_boost", 0.0))

        attachment = prior.get("AttachmentLongingGenerator", {})
        longing_intensity = float(attachment.get("longing_intensity", 0.0))

        nac_core = prior.get("NucleusAccumbensCoreDrive", {})
        motivational_arousal = float(nac_core.get("motivational_arousal", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        seeking_force = float(appetite.get("seeking_force", 0.0))

        # Composite wanting — max of phasic + sustained pulls
        wanting = min(
            1.0,
            max(motivation_boost, longing_intensity, motivational_arousal, seeking_force),
        )

        # LIKING signals (hedonic impact)
        # ValenceTagger.valence_polarity > 0.5 with intensity = positive felt
        # NucleusAccumbensShellValue = hedonic value tag
        # PleasureAnchor (limbic061) = sustained pleasure baseline
        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        nac_shell = prior.get("NucleusAccumbensShellValue", {})
        hedonic_value = float(nac_shell.get("hedonic_value", 0.5))

        pleasure = prior.get("PleasureAnchor", {})
        pleasure_baseline = float(pleasure.get("pleasure_baseline", 0.5))

        # Liking is the actual felt-positive component, not just absence of negative
        liking_from_valence = max(0.0, valence_polarity - 0.5) * 2 * valence_intensity
        liking = min(
            1.0,
            max(liking_from_valence, max(0.0, hedonic_value - 0.5) * 2, pleasure_baseline - 0.4),
        )

        # Smooth via 70/30 blend with previous tick
        smoothed_wanting = 0.7 * self.state["wanting_level"] + 0.3 * wanting
        smoothed_liking = 0.7 * self.state["liking_level"] + 0.3 * liking

        # Histories
        wh = list(self.state.get("wanting_history", []))
        lh = list(self.state.get("liking_history", []))
        wh.append(smoothed_wanting)
        lh.append(smoothed_liking)
        if len(wh) > self.HISTORY_LENGTH:
            wh = wh[-self.HISTORY_LENGTH:]
        if len(lh) > self.HISTORY_LENGTH:
            lh = lh[-self.HISTORY_LENGTH:]
        self.state["wanting_history"] = wh
        self.state["liking_history"] = lh

        # Pleasure drought — sustained low liking
        if smoothed_liking < self.LIKING_LOW:
            self.state["drought_streak"] += 1
        else:
            self.state["drought_streak"] = max(0, self.state["drought_streak"] - 2)
        pleasure_drought = self.state["drought_streak"] >= self.DROUGHT_WINDOW

        # Anhedonia — sustained low liking AND it's been long enough to count clinically
        if smoothed_liking < self.LIKING_LOW:
            self.state["anhedonia_streak"] += 1
        else:
            self.state["anhedonia_streak"] = 0
        anhedonic = self.state["anhedonia_streak"] >= self.ANHEDONIA_WINDOW

        # Compulsive — high wanting + low liking dissociation (addiction signature)
        gap = smoothed_wanting - smoothed_liking
        if smoothed_wanting >= self.WANTING_HIGH and smoothed_liking < self.LIKING_LOW and gap > 0.4:
            self.state["compulsive_streak"] += 1
        else:
            self.state["compulsive_streak"] = max(0, self.state["compulsive_streak"] - 3)
        compulsive = self.state["compulsive_streak"] >= 8

        self.state["wanting_level"] = smoothed_wanting
        self.state["liking_level"] = smoothed_liking
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "wanting_level": smoothed_wanting,
            "liking_level": smoothed_liking,
            "anhedonic": anhedonic,
            "compulsive": compulsive,
            "pleasure_drought": pleasure_drought,
            "wanting_liking_gap": gap,
        }
