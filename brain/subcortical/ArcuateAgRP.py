"""
ArcuateAgRP — AgRP/NPY Hunger Neurons / Arcuate Hypothalamus

NEURAL SUBSTRATE
================
Agouti-related peptide (AgRP)/neuropeptide-Y (NPY) co-expressing neurons
of the arcuate nucleus of the hypothalamus are the canonical "hunger
neurons." They are activated by negative energy balance (low leptin,
high ghrelin), and rapidly drive feeding behavior on optogenetic
activation. They counter the anorexigenic POMC neurons that occupy the
adjacent arcuate cell population.

AgRP neurons release three transmitters at PVN MC4R targets: GABA (fast
inhibition), NPY (slower, NPY-Y1/Y5 receptors), and AgRP itself (an
inverse agonist at MC4R, lifting alpha-MSH-mediated tone). Net effect:
strong PVN inhibition → release of feeding behavior + suppression of
metabolic energy expenditure.

Key projection targets: PVN (feeding + neuroendocrine), BNST (motivation),
PBN (taste/satiation), LHA (motivated behavior), PAG (defensive
suppression). AgRP firing is rapidly suppressed by sensory food cues
even before consumption — anticipatory satiation signal (Chen 2015,
Betley 2015).

Aponte 2011 demonstrated channelrhodopsin activation of AgRP neurons
evokes voracious feeding within minutes; Krashes 2011 showed DREADD
activation produced same effect. Selective ablation of AgRP neurons in
adult mice produces lethal anorexia (Luquet 2005) — proving AgRP is
necessary, not just sufficient, for normal feeding.

KEY FINDINGS
============
1. Optogenetic activation of arcuate AgRP neurons evokes voracious feeding within minutes; sufficient for hunger drive — [Aponte Y 2011, Nat Neurosci 14:351, doi:10.1038/nn.2739]
2. DREADD chemogenetic activation of AgRP neurons recapitulates feeding effect; durable hours of food intake — [Krashes MJ 2011, J Clin Invest 121:1424, doi:10.1172/JCI46229]
3. AgRP neurons release GABA + NPY + AgRP at PVN MC4R targets; inverse agonism at MC4R — [Cone RD 2005, Nat Neurosci 8:571, doi:10.1038/nn1455]
4. AgRP activity rapidly suppressed by sensory food cues before consumption; anticipatory satiation signal — [Chen Y 2015, Cell 160:829, doi:10.1016/j.cell.2015.01.033]
5. Adult-onset AgRP neuron ablation produces lethal anorexia; AgRP necessary for feeding — [Luquet S 2005, Science 310:683, doi:10.1126/science.1115524]

INPUTS
======
- AppetiteNPYBalancer.hunger_signal — homeostatic hunger
- VitalCoreRegulator.vital_drive (low when energy depleted)
- ArcuatePOMC.pomc_alpha_msh_drive — anorexigenic counter (mutual antagonism)
- ValenceTagger.aversive_signal — predator/threat suppresses
- ArousalRegulator.tonic_level

OUTPUTS
=======
- agrp_drive (0-1) — net AgRP firing
- pvn_inhibition (0-1) — GABA + AgRP at MC4R
- npy_release (0-1)
- feeding_motivation (0-1)
- pbn_satiation_command (0-1)
- agrp_state (str): "hunger_active" | "anticipatory_suppression" |
  "satiated" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ArcuateAgRP(BrainMechanism):
    """AgRP/NPY arcuate neurons — hunger driver."""

    BASELINE = 0.10
    SMOOTH = 0.20
    HUNGER_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="ArcuateAgRP",
            human_analog="Arcuate AgRP/NPY hunger neurons",
            layer="subcortical",
        )
        self.state.setdefault("agrp_drive", self.BASELINE)
        self.state.setdefault("pvn_inhibition", 0.0)
        self.state.setdefault("npy_release", 0.0)
        self.state.setdefault("feeding_motivation", 0.0)
        self.state.setdefault("pbn_satiation_command", 0.0)
        self.state.setdefault("agrp_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("food_cue_anticipation", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, hunger: float, vital: float, pomc: float,
                       threat: float, food_cue: float) -> float:
        """AgRP drive — hunger + low vital, antagonized by POMC + threat,
        rapidly suppressed by food cues (Chen 2015 anticipatory).
        """
        # Hunger and energy depletion drive AgRP up
        excitation = hunger * 0.55 + max(0.0, 0.5 - vital) * 0.40
        # POMC antagonism (Cone 2005 mutual)
        pomc_inhibition = pomc * 0.35
        # Anticipatory food-cue suppression (Chen 2015) — fast, before eating
        food_cue_suppression = food_cue * 0.50
        # Predator/threat suppresses feeding
        threat_suppression = threat * 0.30
        target = (self.BASELINE + excitation
                    - pomc_inhibition - food_cue_suppression
                    - threat_suppression)
        return max(0.0, min(1.0, target))

    def _pvn_inhibition(self, drive: float) -> float:
        """AgRP→PVN GABA + AgRP-MC4R inverse agonism (Aponte 2011)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.85)

    def _npy(self, drive: float) -> float:
        """NPY co-release at PVN, BNST, LHA targets."""
        return min(1.0, drive * 0.80)

    def _feeding_motivation(self, drive: float, hunger: float) -> float:
        """Behavioral feeding drive (Krashes 2011)."""
        return min(1.0, drive * 0.6 + hunger * 0.4)

    def _pbn_satiation(self, drive: float, food_cue: float) -> float:
        """AgRP→PBN suppresses satiation neurons (releases feeding)."""
        if food_cue > 0.30:
            return drive * 0.30  # food cue rapidly cuts AgRP→PBN tone
        return min(1.0, drive * 0.7)

    def _classify_state(self, drive: float, food_cue: float,
                         hunger: float) -> str:
        if drive < 0.15:
            return "satiated" if hunger < 0.20 else "quiet"
        if food_cue > 0.40:
            return "anticipatory_suppression"
        if drive > self.HUNGER_THRESHOLD:
            return "hunger_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        appetite = prior.get("AppetiteNPYBalancer", {})
        hunger = float(appetite.get("hunger_signal", 0.0))

        vital_data = prior.get("VitalCoreRegulator", {})
        vital = float(vital_data.get("vital_drive", 0.5))

        pomc_data = prior.get("ArcuatePOMC", {})
        pomc = float(pomc_data.get("pomc_alpha_msh_drive",
                            pomc_data.get("alpha_msh_release", 0.0)))

        valence = prior.get("ValenceTagger", {})
        threat = float(valence.get("aversive_signal", 0.0))

        # food_cue: any salient appetitive olfactory/visual signal
        ot_data = prior.get("OlfactoryTubercleStriatal", {})
        ob_data = prior.get("OlfactoryBulb", {})
        food_cue = max(float(ot_data.get("ot_drive", 0.0)),
                          float(ob_data.get("food_odor_signal", 0.0)))

        target = self._drive_target(hunger, vital, pomc, threat, food_cue)
        prev_drive = float(self.state.get("agrp_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        pvn_inhib = self._pvn_inhibition(new_drive)
        npy = self._npy(new_drive)
        motivation = self._feeding_motivation(new_drive, hunger)
        pbn = self._pbn_satiation(new_drive, food_cue)

        state = self._classify_state(new_drive, food_cue, hunger)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["agrp_drive"] = round(new_drive, 4)
        self.state["pvn_inhibition"] = round(pvn_inhib, 4)
        self.state["npy_release"] = round(npy, 4)
        self.state["feeding_motivation"] = round(motivation, 4)
        self.state["pbn_satiation_command"] = round(pbn, 4)
        self.state["food_cue_anticipation"] = round(food_cue, 4)
        self.state["agrp_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "agrp_drive": round(new_drive, 4),
            "pvn_inhibition": round(pvn_inhib, 4),
            "npy_release": round(npy, 4),
            "feeding_motivation": round(motivation, 4),
            "pbn_satiation_command": round(pbn, 4),
            "agrp_state": state,
        }

    def _starvation_index(self, hunger: float, vital: float) -> float:
        """Combined starvation pressure (Luquet 2005)."""
        return min(1.0, hunger * 0.5 + max(0.0, 0.5 - vital) * 1.0)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("agrp_drive", 0.0),
            "feeding": self.state.get("feeding_motivation", 0.0),
            "pvn_inhib": self.state.get("pvn_inhibition", 0.0),
            "state": self.state.get("agrp_state", "quiet"),
        }
