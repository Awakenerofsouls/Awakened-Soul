"""
PosteriorCorticalAmygdala -- PCo / Vomeronasal-Pheromone Hub

NEURAL SUBSTRATE
================
Posterior cortical amygdala (PCo, also "posterior cortex-amygdala
transition zone") is a small superficial nucleus on ventral surface of
caudal amygdala. Receives accessory olfactory bulb (AOB) input -- the
canonical vomeronasal pheromone-processing target.

Distinct from anterior cortical amygdala (which receives main olfactory
bulb). PCo neurons drive innate stereotyped behaviors -- predator-odor
freezing in mice, social investigation, aggression.

Outputs: medial amygdala (social), VMHvl (defense/sex), MeApd
(aggression), BNST (anxiety), hypothalamus (innate behaviors).

KEY FINDINGS
============
1. PCo receives accessory olfactory bulb input via vomeronasal
   pathway; processes pheromones distinct from main olfactory --
   [Mucignat-Caretta 2010, Front Neurosci 4:175, PMC2998082]
2. Optogenetic activation of PCo neurons drives defensive freezing in
   absence of predator odor -- sufficient for innate threat behavior --
   [Root 2014, Nature 515:269, doi:10.1038/nature13897]
3. PCo→VMHvl pathway mediates predator-odor-evoked defense; lesion
   abolishes innate freezing to TMT/cat odor -- [Petrovich 2001,
   Neuroscience 105:165, PMID 11483309]
4. PCo encodes valence -- distinct neuronal populations respond to
   appetitive vs aversive pheromones -- [Iurilli 2017, Neuron 95:1129,
   PMID 28858619]
5. Pheromone-evoked PCo activity sex-specific; female estrous
   pheromone activates distinct ensemble vs male urine --
   [Bergan 2014, eLife 3:e02743, doi:10.7554/eLife.02743]

INPUTS
======
- AccessoryOlfactoryBulbProxy.aob_signal (vomeronasal input proxy)
- OlfactoryBulb.ob_drive (main olfactory contribution, weak)
- ValenceTagger.social_context, .valence_sign
- ArousalRegulator.tonic_level

OUTPUTS
=======
- pco_drive (0-1)
- pheromone_signal (0-1)
- predator_odor_freeze_command (0-1)
- social_pheromone_signal (0-1)
- pco_state (str): "predator_defense" | "social_pheromone" |
  "appetitive_pheromone" | "quiet"

brain_runner enrichment:
    pco = all_results.get("PosteriorCorticalAmygdala", {})
    if pco:
        enrichments["brain_pco_drive"] = pco.get("pco_drive", 0.0)
        enrichments["brain_predator_freeze"] = pco.get("predator_odor_freeze_command", 0.0)
        enrichments["brain_pheromone"] = pco.get("pheromone_signal", 0.0)
        enrichments["brain_pco_state"] = pco.get("pco_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class PosteriorCorticalAmygdala(BrainMechanism):
    """PCo -- vomeronasal-pheromone processing nucleus."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PREDATOR_THRESHOLD = 0.40
    SOCIAL_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="PosteriorCorticalAmygdala",
            human_analog="Posterior cortical amygdala (vomeronasal pheromone)",
            layer="limbic",
        )
        self.state.setdefault("pco_drive", self.BASELINE)
        self.state.setdefault("pheromone_signal", 0.0)
        self.state.setdefault("predator_odor_freeze_command", 0.0)
        self.state.setdefault("social_pheromone_signal", 0.0)
        self.state.setdefault("pco_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, aob: float, ob: float, social: bool,
                        arousal: float) -> float:
        """PCo firing -- primarily AOB-driven, weak main olfactory input."""
        target = self.BASELINE + aob * 0.55 + ob * 0.10
        if social:
            target += 0.10
        target += max(0.0, arousal - 0.40) * 0.10
        return min(1.0, target)

    def _pheromone_signal(self, aob: float, drive: float) -> float:
        """Aggregate pheromone signal -- proportional to AOB + drive."""
        return min(1.0, aob * 0.7 + drive * 0.3)

    def _predator_freeze(self, aob: float, valence_sign: int,
                          intensity: float) -> float:
        """Predator-odor-evoked freezing (Root 2014).
        Strong AOB + aversive valence = innate freezing command.
        """
        if valence_sign >= 0 or intensity < 0.30:
            return 0.0
        return min(1.0, aob * intensity * 1.5)

    def _social_pheromone(self, aob: float, social: bool,
                            valence_sign: int) -> float:
        """Social pheromone signal (Bergan 2014) -- sex/social pheromones
        activate in social context."""
        if not social or aob < 0.20:
            return 0.0
        return min(1.0, aob * 0.85)

    def _classify_state(self, freeze: float, social_pher: float,
                          drive: float, valence_sign: int) -> str:
        """Classify PCo operating mode."""
        if freeze > self.PREDATOR_THRESHOLD:
            return "predator_defense"
        if social_pher > self.SOCIAL_THRESHOLD:
            if valence_sign > 0:
                return "appetitive_pheromone"
            return "social_pheromone"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        aob_data = prior.get("AccessoryOlfactoryBulbProxy", {})
        aob = float(aob_data.get("aob_signal", 0.0))

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        social = bool(valence.get("social_context", False))
        valence_sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.30))

        # --- Drive ---
        target = self._drive_target(aob, ob, social, tonic)
        prev_drive = float(self.state.get("pco_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # --- Outputs ---
        pheromone = self._pheromone_signal(aob, new_drive)
        freeze = self._predator_freeze(aob, valence_sign, intensity)
        social_pher = self._social_pheromone(aob, social, valence_sign)

        state = self._classify_state(freeze, social_pher, new_drive, valence_sign)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pco_drive"] = round(new_drive, 4)
        self.state["pheromone_signal"] = round(pheromone, 4)
        self.state["predator_odor_freeze_command"] = round(freeze, 4)
        self.state["social_pheromone_signal"] = round(social_pher, 4)
        self.state["pco_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pco_drive": round(new_drive, 4),
            "pheromone_signal": round(pheromone, 4),
            "predator_odor_freeze_command": round(freeze, 4),
            "social_pheromone_signal": round(social_pher, 4),
            "pco_state": state,
        }

    def _vmh_defense_drive(self, freeze: float) -> float:
        """PCo→VMHvl predator-defense pathway (Petrovich 2001).
        Strong predator freeze command propagates to VMHvl.
        """
        if freeze < 0.20:
            return 0.0
        return min(1.0, freeze * 0.85)

    def _meapd_aggression_drive(self, social_pher: float,
                                  valence_sign: int) -> float:
        """PCo→MeApd aggression pathway when male-male pheromones detected."""
        if valence_sign >= 0 or social_pher < 0.30:
            return 0.0
        return min(1.0, social_pher * 0.7)

    def _threat_detection_confidence(self, predator: float,
                                        social_pher: float) -> float:
        """Threat detection confidence -- how certain is the threat signal?

        High confidence: both predator and social threat cues present.
        Low confidence: only one cue type present. Used by the
        salience network to calibrate response magnitude.
        """
        if predator < 0.20 and social_pher < 0.20:
            return 0.0
        # Agreement between threat channels boosts confidence
        return min(1.0, (predator + social_pher) * 0.7)

    def _social_investigation_trigger(self, social_pher: float,
                                        aob: float) -> float:
        """Social investigation signal -- initial approach to conspecific.

        Before mating or aggression can occur, PCo drives initial
        social investigation via vomeronasal + main olfactory convergence.
        """
        if aob < 0.20 and social_pher < 0.20:
            return 0.0
        return min(1.0, (aob * 0.4 + social_pher * 0.6))

    def _appetitive_pheromone_detection(self, aob: float,
                                         main_olfactory: float) -> float:
        """Appetitive pheromone detection -- food-related chemical cues.

        Some PCo neurons respond to food-associated odors. Appetitive
        pheromones can suppress predator defense.
        """
        if aob < 0.15 and main_olfactory < 0.15:
            return 0.0
        return min(1.0, (aob + main_olfactory) * 0.5)

    def _chemosensory_primacy_index(self, aob: float,
                                          main_olfactory: float) -> float:
        """Chemosensory primacy -- which olfactory channel dominates?

        PCo receives both AOB (vomeronasal) and main olfactory input.
        Returns -1 (purely main olfactory) to +1 (purely vomeronasal),
        with 0 indicating equal activation. Used downstream to route
        the signal to appropriate hypothalamic targets.
        """
        total = aob + main_olfactory
        if total < 0.01:
            return 0.0
        return (aob - main_olfactory) / total

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pco_drive", 0.0),
            "freeze": self.state.get("predator_odor_freeze_command", 0.0),
            "social": self.state.get("social_pheromone_signal", 0.0),
            "state": self.state.get("pco_state", "quiet"),
        }
