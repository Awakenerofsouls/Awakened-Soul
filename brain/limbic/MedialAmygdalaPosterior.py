"""
MedialAmygdalaPosterior -- MeApd / Sexually Dimorphic Social-Aggression Hub

NEURAL SUBSTRATE
================
Posterior medial amygdala (MeApd) is the principal subdivision processing
chemosensory + social signals from the AOB pathway. Sexually dimorphic in
volume + connectivity -- larger in males. Distinct from anterior medial
amygdala (MeAv) which is more autonomic.

Inputs: AOB (vomeronasal), main olfactory cortical amygdala, BNST
feedback, hypothalamic feedback (PVN, VMH).

Outputs: VMHvl (sex/aggression), VMHdm (defense), BNST-Po (sexually
dimorphic), AHN (anterior hypothalamic, defense), MPOA (sexual behavior).

Choi 2005 demonstrated that Lhx6+ MeApd neurons mediate sexually dimorphic
innate behaviors via labeled-line projections to hypothalamus.

KEY FINDINGS
============
1. Lhx6+ MeApd neurons project to VMHvl (sex behavior) vs VMHdm
   (defense); pheromones activate distinct subpopulations --
   [Choi 2005, Neuron 46:647, doi:10.1016/j.neuron.2005.04.011]
2. MeApd is sexually dimorphic; male volume > female; testosterone-
   sensitive -- [Cooke 2007, Neuroscience 144:1, PMID 17029796]
3. MeApd inactivation prevents male mating + male-male aggression in
   mice -- [Hong 2014, Cell 158:1348, doi:10.1016/j.cell.2014.07.049]
4. MeApd→MPOA pathway drives mounting; MeApd→VMHvl→PAG drives
   aggression -- [Lin 2011, Nature 470:221, doi:10.1038/nature09736]
5. Female MeApd activated by male pheromones; estrous-cycle modulated
   sexual receptivity -- [Bergan 2014, eLife 3:e02743, PMC4060438]

INPUTS
======
- PosteriorCorticalAmygdala.pheromone_signal, .social_pheromone_signal
- AccessoryOlfactoryBulbProxy.aob_signal
- ValenceTagger.social_context, .valence_sign
- HypothalamicSupramammillary.ca2_social_novelty
- EstrogenProxy.estrogen_level (default 0.5)
- TestosteroneProxy.testosterone_level (default 0.5)

OUTPUTS
=======
- meapd_drive (0-1)
- mating_command (0-1)
- aggression_command (0-1)
- vmhvl_command (0-1)
- vmhdm_command (0-1)
- meapd_state (str): "mating" | "aggression" | "social_appraisal" | "quiet"

brain_runner enrichment:
    meapd = all_results.get("MedialAmygdalaPosterior", {})
    if meapd:
        enrichments["brain_meapd_drive"] = meapd.get("meapd_drive", 0.0)
        enrichments["brain_mating_cmd"] = meapd.get("mating_command", 0.0)
        enrichments["brain_aggression_cmd"] = meapd.get("aggression_command", 0.0)
        enrichments["brain_meapd_state"] = meapd.get("meapd_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedialAmygdalaPosterior(BrainMechanism):
    """MeApd -- sexually dimorphic social/sex/aggression hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AGGRESSION_THRESHOLD = 0.40
    MATING_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="MedialAmygdalaPosterior",
            human_analog="Medial amygdala posterior (sex/aggression dimorphic)",
            layer="limbic",
        )
        self.state.setdefault("meapd_drive", self.BASELINE)
        self.state.setdefault("mating_command", 0.0)
        self.state.setdefault("aggression_command", 0.0)
        self.state.setdefault("vmhvl_command", 0.0)
        self.state.setdefault("vmhdm_command", 0.0)
        self.state.setdefault("meapd_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pco_pher: float, aob: float, social: bool,
                       social_novelty: float) -> float:
        """MeApd firing -- pheromone-driven, social-context-gated."""
        target = self.BASELINE + pco_pher * 0.40 + aob * 0.25
        if social:
            target += 0.15
        target += social_novelty * 0.20
        return min(1.0, target)

    def _mating_command(self, drive: float, valence_sign: int,
                          estrogen: float, social: bool) -> float:
        """Mating command (Lin 2011 MeApd→MPOA)."""
        if not social or valence_sign <= 0:
            return 0.0
        return min(1.0, drive * 0.6 + estrogen * 0.4)

    def _aggression_command(self, drive: float, valence_sign: int,
                              testosterone: float, social: bool) -> float:
        """Aggression command (Hong 2014, Lin 2011)."""
        if not social or valence_sign >= 0:
            return 0.0
        return min(1.0, drive * 0.55 + testosterone * 0.45)

    def _vmhvl_command(self, mating: float, aggression: float) -> float:
        """VMHvl receives both mating + aggression signals (Choi 2005)."""
        return min(1.0, mating * 0.5 + aggression * 0.5)

    def _vmhdm_command(self, drive: float, valence_sign: int,
                         intensity: float) -> float:
        """VMHdm defense command -- predator/threat valence (Choi 2005)."""
        if valence_sign >= 0:
            return 0.0
        return min(1.0, drive * intensity * 1.2)

    def _classify_state(self, mating: float, aggression: float,
                          drive: float, social: bool) -> str:
        if aggression > self.AGGRESSION_THRESHOLD:
            return "aggression"
        if mating > self.MATING_THRESHOLD:
            return "mating"
        if social and drive > 0.20:
            return "social_appraisal"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pco_data = prior.get("PosteriorCorticalAmygdala", {})
        pco_pher = float(pco_data.get("pheromone_signal", 0.0))
        social_pher = float(pco_data.get("social_pheromone_signal", 0.0))

        aob_data = prior.get("AccessoryOlfactoryBulbProxy", {})
        aob = float(aob_data.get("aob_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        social = bool(valence.get("social_context", False))
        valence_sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))

        sum_data = prior.get("HypothalamicSupramammillary", {})
        social_novelty = float(sum_data.get("ca2_social_novelty", 0.0))

        estrogen_data = prior.get("EstrogenProxy", {})
        estrogen = float(estrogen_data.get("estrogen_level", 0.5))

        testosterone_data = prior.get("TestosteroneProxy", {})
        testosterone = float(testosterone_data.get("testosterone_level", 0.5))

        # --- Drive ---
        target = self._drive_target(pco_pher, aob, social, social_novelty)
        prev_drive = float(self.state.get("meapd_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # --- Outputs ---
        mating = self._mating_command(new_drive, valence_sign, estrogen, social)
        aggression = self._aggression_command(new_drive, valence_sign,
                                                testosterone, social)
        vmhvl_cmd = self._vmhvl_command(mating, aggression)
        vmhdm_cmd = self._vmhdm_command(new_drive, valence_sign, intensity)

        state = self._classify_state(mating, aggression, new_drive, social)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["meapd_drive"] = round(new_drive, 4)
        self.state["mating_command"] = round(mating, 4)
        self.state["aggression_command"] = round(aggression, 4)
        self.state["vmhvl_command"] = round(vmhvl_cmd, 4)
        self.state["vmhdm_command"] = round(vmhdm_cmd, 4)
        self.state["meapd_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "meapd_drive": round(new_drive, 4),
            "mating_command": round(mating, 4),
            "aggression_command": round(aggression, 4),
            "vmhvl_command": round(vmhvl_cmd, 4),
            "vmhdm_command": round(vmhdm_cmd, 4),
            "meapd_state": state,
        }

    def _hormone_modulation(self, estrogen: float, testosterone: float) -> float:
        """Hormonal modulation of MeApd activity (Cooke 2007 dimorphism).

        Returns a 0-1 factor reflecting current hormonal state.
        Higher values reflect estrus-elevated estrogen or high testosterone,
        both of which amplify MeApd social signal processing.
        """
        return (estrogen + testosterone) / 2.0

    def _dominance_hierarchy_signal(self, aggression: float,
                                     mating: float) -> float:
        """Dominance hierarchy signal -- aggression vs mating competition.

        In social groups, MeApd encodes status-relevant signals. High
        aggression without mating drive suggests dominance assertion.
        High mating drive in presence of competitor = social competition.
        """
        if aggression > 0.40:
            return min(1.0, aggression - mating * 0.3)
        return 0.0

    def _estrous_cycle_modulation(self, estrogen: float,
                                    progesterone: float) -> float:
        """Estrous cycle modulation of female MeApd responsivity.

        Bergan 2014: estrous cycle modulates female MeApd response to
        male pheromones. High estrogen = high receptivity; progesterone
        attenuates estrogen facilitation.
        """
        if estrogen < 0.30:
            return 0.0
        return max(0.0, min(1.0, estrogen - progesterone * 0.3))

    def _social_recognition_memory(self, social_pher: float,
                                     meapd_drive: float,
                                     social_novelty: float) -> float:
        """Social recognition memory signal -- familiar vs novel conspecific.

        Hong 2014 showed MeApd is required for social recognition.
        High social novelty + high pheromone drive = active recognition.
        """
        if social_pher < 0.20:
            return 0.0
        familiarity = 1.0 - min(1.0, social_novelty)
        return min(1.0, social_pher * meapd_drive * familiarity)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("meapd_drive", 0.0),
            "mating": self.state.get("mating_command", 0.0),
            "aggression": self.state.get("aggression_command", 0.0),
            "state": self.state.get("meapd_state", "quiet"),
        }
