"""
PaleocorticalAmygdala — Olfactory-Limbic Boundary

NEURAL SUBSTRATE
================
The paleocortical amygdala (encompassing nucleus of the lateral
olfactory tract, NLOT, and adjacent cortical-amygdaloid transition
zones) is part of the most evolutionarily ancient amygdala — the
"olfactory amygdala" — receiving direct mitral cell input from
olfactory bulb. Distinct from basolateral and central amygdala (which
are pallial), paleocortical amygdala has cortical-like layered
architecture and processes innate olfactory valence (food/predator
odors).

Functionally, paleocortical amygdala mediates innate (unlearned)
olfactory responses — defensive freezing to predator odors (Root 2014),
attractive responses to sexual pheromones, and rapid odor-fear linking.
This is a "labeled-line" innate olfactory affect circuit.

KEY FINDINGS
============
1. Paleocortical amygdala is part of olfactory amygdala receiving
   direct LOT input; cortical-like layered architecture —
   [Swanson 1998, Trends Neurosci 21:323, PMID 9720596]
2. Posterolateral cortical amygdala neurons mediate innate predator-
   odor freezing; necessary for unlearned defensive response —
   [Root 2014, Nature 515:269, doi:10.1038/nature13897]
3. Paleocortical amygdala / NLOT projects to BLA, central amygdala,
   and hypothalamus —
   [Pro-Sistiaga 2007, J Comp Neurol 504:346, doi:10.1002/cne.21455]
4. Innate appetitive odor (food) responses depend on paleocortical
   amygdala input to lateral hypothalamus —
   [Cadiz-Moretti 2014, Brain Struct Funct 219:1761, doi:10.1007/s00429-013-0588-5]
5. Paleocortical amygdala is evolutionarily ancient olfactory limbic
   structure conserved in vertebrates —
   [Martinez-Garcia 2007, Brain Behav Evol 70:209, doi:10.1159/000105488]
"""

from brain.base_mechanism import BrainMechanism


class PaleocorticalAmygdala(BrainMechanism):
    """Paleocortical amygdala — innate olfactory valence."""

    BASELINE = 0.10
    SMOOTH = 0.20
    INNATE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="PaleocorticalAmygdala",
            human_analog="Paleocortical amygdala (olfactory boundary)",
            layer="limbic",
        )
        self.state.setdefault("pca_drive", self.BASELINE)
        self.state.setdefault("innate_fear_signal", 0.0)
        self.state.setdefault("innate_appetitive_signal", 0.0)
        self.state.setdefault("bla_drive_signal", 0.0)
        self.state.setdefault("hypothalamic_drive_signal", 0.0)
        self.state.setdefault("pca_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, pir: float, predator_odor: float) -> float:
        """Paleocortical drive (Swanson 1998)."""
        target = (self.BASELINE
                  + ob * 0.40
                  + pir * 0.20
                  + predator_odor * 0.20)
        return min(1.0, target)

    def _innate_fear(self, drive: float, predator_odor: float,
                      sign: int, intensity: float) -> float:
        """Innate predator-odor fear (Root 2014)."""
        aversive = max(0.0, -sign * intensity)
        return min(1.0, drive * 0.4 + predator_odor * 0.4 + aversive * 0.2)

    def _innate_appetitive(self, drive: float, food_odor: float,
                             sign: int, intensity: float) -> float:
        """Innate food/sexual odor response (Cadiz-Moretti 2014)."""
        appetitive = max(0.0, sign * intensity)
        return min(1.0, drive * 0.4 + food_odor * 0.4 + appetitive * 0.2)

    def _bla_drive(self, drive: float, fear: float) -> float:
        """Paleocortical→BLA (Pro-Sistiaga 2007)."""
        return min(1.0, drive * 0.5 + fear * 0.4)

    def _hypothalamic_drive(self, drive: float, appetitive: float) -> float:
        """Paleocortical→hypothalamus (Cadiz-Moretti 2014)."""
        return min(1.0, drive * 0.4 + appetitive * 0.5)

    def _classify_state(self, drive: float, fear: float,
                          appetitive: float) -> str:
        if drive < 0.20:
            return "quiet"
        if fear > self.INNATE_THRESHOLD:
            return "innate_fear"
        if appetitive > self.INNATE_THRESHOLD:
            return "innate_attraction"
        return "active_olfactory"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive",
                          ob_data.get("ob_output", 0.0)))

        pir_data = prior.get("PiriformLayer3", {})
        if not pir_data:
            pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir3_drive",
                          pir_data.get("pir_drive", 0.0)))

        predator_data = prior.get("OlfactoryBulb", {})
        predator_odor = float(predator_data.get("predator_odor_signal", 0.0))
        food_odor = float(predator_data.get("food_odor_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(ob, pir, predator_odor)
        prev_drive = float(self.state.get("pca_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        fear = self._innate_fear(new_drive, predator_odor, sign, intensity)
        appetitive = self._innate_appetitive(new_drive, food_odor, sign, intensity)
        bla = self._bla_drive(new_drive, fear)
        hypo = self._hypothalamic_drive(new_drive, appetitive)

        state = self._classify_state(new_drive, fear, appetitive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pca_drive"] = round(new_drive, 4)
        self.state["innate_fear_signal"] = round(fear, 4)
        self.state["innate_appetitive_signal"] = round(appetitive, 4)
        self.state["bla_drive_signal"] = round(bla, 4)
        self.state["hypothalamic_drive_signal"] = round(hypo, 4)
        self.state["pca_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pca_drive": round(new_drive, 4),
            "innate_fear_signal": round(fear, 4),
            "innate_appetitive_signal": round(appetitive, 4),
            "bla_drive_signal": round(bla, 4),
            "hypothalamic_drive_signal": round(hypo, 4),
            "pca_state": state,
        }

    def _ancient_circuit_engagement(self) -> float:
        """Engagement of evolutionary olfactory circuit (Martinez-Garcia 2007)."""
        return max(float(self.state.get("innate_fear_signal", 0.0)),
                    float(self.state.get("innate_appetitive_signal", 0.0)))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pca_drive", 0.0),
            "fear": self.state.get("innate_fear_signal", 0.0),
            "appetitive": self.state.get("innate_appetitive_signal", 0.0),
            "state": self.state.get("pca_state", "quiet"),
        }
