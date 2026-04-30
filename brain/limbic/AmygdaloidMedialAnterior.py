"""
AmygdaloidMedialAnterior — MeAa / Anterior Medial Amygdala / Autonomic-Limbic

NEURAL SUBSTRATE
================
Anterior subdivision of medial amygdala (MeAa, also "anterodorsal") sits
rostral to MeAp (posterior). Functionally distinct: MeAa is more
autonomic-/visceral-coupled and less sexually dimorphic than MeAp. Both
receive AOB input but project differently.

Outputs: BNST (extended amygdala), hypothalamic autonomic targets
(PVN, DMH), brainstem autonomic premotor (RVLM, NTS feedback),
periaqueductal gray.

Functional role: convergent visceral + chemosensory integration for
autonomic-affective coupling. Distinct from MeAp's reproductive/social
focus.

KEY FINDINGS
============
1. Medial amygdala anterior vs posterior subdivisions: anterior is more
   autonomic, posterior more sexually dimorphic + reproductive —
   [Canteras 1995, J Comp Neurol 360:213, doi:10.1002/cne.903600203]
2. MeAa receives convergent visceral + chemosensory input; integrates
   with autonomic outputs — [Choi 2005, Neuron 46:647, doi:10.1016/j.neuron.2005.04.011]
3. MeA → BNST → autonomic axis; sustained autonomic activation —
   [Dong 2001, J Comp Neurol 432:307, PMID 11246211]
4. MeAa lesions impair autonomic responses to chemosensory threats —
   [Pardo-Bellver 2012, Front Neuroanat 6:33, doi:10.3389/fnana.2012.00033]
5. MeAa population codes for stress-stimulus valence at single-cell
   resolution; distinct ensembles for predator vs conspecific —
   [Bergan 2014, eLife 3:e02743, doi:10.7554/eLife.02743]

INPUTS
======
- AccessoryOlfactoryBulbProxy.aob_signal
- PosteriorCorticalAmygdala.pheromone_signal
- ParabrachialTasteVisceral.parabrachial_signal
- ValenceTagger.aversive_signal, .valence_sign

OUTPUTS
=======
- meaa_drive (0-1)
- bnst_command (0-1) — extended amygdala output
- pvn_autonomic_command (0-1)
- valence_population_code (-1 to 1)
- meaa_state (str): "predator_autonomic" | "stress_autonomic" |
  "social_autonomic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AmygdaloidMedialAnterior(BrainMechanism):
    """MeAa — autonomic-coupled medial amygdala anterior subdivision."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AUTONOMIC_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="AmygdaloidMedialAnterior",
            human_analog="Medial amygdala anterior (autonomic-limbic)",
            layer="limbic",
        )
        self.state.setdefault("meaa_drive", self.BASELINE)
        self.state.setdefault("bnst_command", 0.0)
        self.state.setdefault("pvn_autonomic_command", 0.0)
        self.state.setdefault("valence_population_code", 0.0)
        self.state.setdefault("meaa_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, aob: float, pco_pher: float, parabrachial: float,
                       aversive: float) -> float:
        target = self.BASELINE + aob * 0.30 + pco_pher * 0.25
        target += parabrachial * 0.20 + aversive * 0.20
        return min(1.0, target)

    def _bnst_command(self, drive: float, aversive: float) -> float:
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _pvn_autonomic(self, drive: float, parabrachial: float) -> float:
        return min(1.0, drive * 0.6 + parabrachial * 0.4)

    def _valence_code(self, aversive: float, valence_sign: int,
                        intensity: float) -> float:
        if valence_sign == 0:
            return 0.0
        return max(-1.0, min(1.0, valence_sign * intensity))

    def _classify_state(self, drive: float, aversive: float,
                          valence_sign: int, social: bool) -> str:
        if drive < 0.20:
            return "quiet"
        if aversive > self.AUTONOMIC_THRESHOLD and not social:
            return "predator_autonomic"
        if aversive > 0.30:
            return "stress_autonomic"
        if social and drive > 0.30:
            return "social_autonomic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        aob_data = prior.get("AccessoryOlfactoryBulbProxy", {})
        aob = float(aob_data.get("aob_signal", 0.0))

        pco_data = prior.get("PosteriorCorticalAmygdala", {})
        pco_pher = float(pco_data.get("pheromone_signal", 0.0))

        pb_data = prior.get("ParabrachialTasteVisceral", {})
        parabrachial = float(pb_data.get("parabrachial_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        social = bool(valence.get("social_context", False))

        target = self._drive_target(aob, pco_pher, parabrachial, aversive)
        prev_drive = float(self.state.get("meaa_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        bnst_cmd = self._bnst_command(new_drive, aversive)
        pvn_cmd = self._pvn_autonomic(new_drive, parabrachial)
        valence_code = self._valence_code(aversive, valence_sign, intensity)

        state = self._classify_state(new_drive, aversive, valence_sign, social)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["meaa_drive"] = round(new_drive, 4)
        self.state["bnst_command"] = round(bnst_cmd, 4)
        self.state["pvn_autonomic_command"] = round(pvn_cmd, 4)
        self.state["valence_population_code"] = round(valence_code, 4)
        self.state["meaa_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "meaa_drive": round(new_drive, 4),
            "bnst_command": round(bnst_cmd, 4),
            "pvn_autonomic_command": round(pvn_cmd, 4),
            "valence_population_code": round(valence_code, 4),
            "meaa_state": state,
        }

    def _autonomic_load(self, recent_states: list) -> float:
        if not recent_states:
            return 0.0
        autonomic = sum(1 for s in recent_states[-50:]
                          if s in ("predator_autonomic", "stress_autonomic"))
        return autonomic / max(1, len(recent_states[-50:]))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("meaa_drive", 0.0),
            "bnst": self.state.get("bnst_command", 0.0),
            "pvn": self.state.get("pvn_autonomic_command", 0.0),
            "state": self.state.get("meaa_state", "quiet"),
        }
