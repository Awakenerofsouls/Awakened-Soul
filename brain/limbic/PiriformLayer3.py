"""
PiriformLayer3 — Pir-III / Piriform Cortex Deep Pyramidal Output

NEURAL SUBSTRATE
================
Layer 3 of piriform cortex (Pir-III) houses deep pyramidal cells that
serve as the principal output stage of olfactory cortex. Pir-III
pyramids receive input from Pir-II, recurrent associative input from
ipsi and contralateral piriform, and project to (1) orbitofrontal
cortex via thalamic relay, (2) entorhinal cortex, (3) amygdala, and
(4) endopiriform/cortical association areas.

Pir-III is critical for olfactory hedonic + identity integration —
linking odor representation to value and memory. Pir-III associative
networks contribute to perceptual learning and odor categorization
(Wilson 2003).

KEY FINDINGS
============
1. Piriform layer 3 deep pyramidal cells are principal output neurons
   projecting to OFC, EC, amygdala —
   [Haberly 2001, Chem Senses 26:551, doi:10.1093/chemse/26.5.551]
2. Pir-III associative connections support odor perceptual learning;
   activity-dependent plasticity —
   [Wilson 2003, Annu Rev Neurosci 26:1, doi:10.1146/annurev.neuro.26.041002.131303]
3. Pir-III OFC projection conveys olfactory hedonic value; necessary
   for odor preference learning —
   [Roesch 2007, Cereb Cortex 17:643, doi:10.1093/cercor/bhk009]
4. Pir-III amygdala projection mediates olfactory fear conditioning;
   pathway-specific —
   [Sevelinges 2004, Behav Neurosci 118:79, doi:10.1037/0735-7044.118.1.79]
5. Pir-III recurrent associational fibers create integration bias for
   familiar odors —
   [Yoshida 2017, Cell Reports 18:2031, doi:10.1016/j.celrep.2017.01.075]
"""

from brain.base_mechanism import BrainMechanism


class PiriformLayer3(BrainMechanism):
    """Pir-III — deep pyramidal output of piriform cortex."""

    BASELINE = 0.10
    SMOOTH = 0.20
    OUTPUT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="PiriformLayer3",
            human_analog="Piriform cortex layer 3 (deep)",
            layer="limbic",
        )
        self.state.setdefault("pir3_drive", self.BASELINE)
        self.state.setdefault("ofc_drive_signal", 0.0)
        self.state.setdefault("ec_drive_signal", 0.0)
        self.state.setdefault("amygdala_drive_signal", 0.0)
        self.state.setdefault("hedonic_signal", 0.0)
        self.state.setdefault("recurrent_associative_signal", 0.0)
        self.state.setdefault("pir3_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recurrent_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pir2: float, en: float, recurrent: float) -> float:
        """Pir-III drive (Haberly 2001)."""
        target = (self.BASELINE
                  + pir2 * 0.45
                  + en * 0.20
                  + recurrent * 0.20)
        return min(1.0, target)

    def _ofc(self, drive: float, sign: int, intensity: float) -> float:
        """Pir-III→OFC hedonic value (Roesch 2007)."""
        appetitive = max(0.0, sign * intensity)
        return min(1.0, drive * 0.5 + appetitive * 0.4)

    def _ec(self, drive: float) -> float:
        """Pir-III→EC olfactory memory (Haberly 2001)."""
        return min(1.0, drive * 0.7)

    def _amygdala(self, drive: float, sign: int, intensity: float) -> float:
        """Pir-III→amygdala olfactory fear (Sevelinges 2004)."""
        aversive = max(0.0, -sign * intensity)
        return min(1.0, drive * 0.4 + aversive * 0.6)

    def _hedonic(self, ofc: float, sign: int, intensity: float) -> float:
        """Hedonic valence integration (Roesch 2007)."""
        return min(1.0, ofc * 0.6 + abs(sign) * intensity * 0.4)

    def _recurrent(self, drive: float, prev_trace: float) -> float:
        """Recurrent associative fibers (Yoshida 2017)."""
        if drive < 0.20:
            return prev_trace * 0.85
        return min(1.0, prev_trace * 0.70 + drive * 0.25)

    def _classify_state(self, drive: float, ofc: float, am: float) -> str:
        if drive < 0.20:
            return "quiet"
        if ofc > self.OUTPUT_THRESHOLD:
            return "hedonic_active"
        if am > 0.40:
            return "fear_active"
        return "active_olfactory"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pir2_data = prior.get("PiriformLayer2", {})
        if not pir2_data:
            pir2_data = prior.get("PiriformCortex", {})
        pir2 = float(pir2_data.get("pir2_drive",
                            pir2_data.get("layer3_drive_signal",
                              pir2_data.get("pir_drive", 0.0))))

        en_data = prior.get("EndopiriformNucleus", {})
        en = float(en_data.get("piriform_feedback_command",
                          en_data.get("en_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        prev_recurrent = float(self.state.get("recurrent_trace", 0.0))
        prev_drive = float(self.state.get("pir3_drive", self.BASELINE))

        target = self._drive_target(pir2, en, prev_recurrent)
        new_drive = self._smooth(prev_drive, target)

        recurrent = self._recurrent(new_drive, prev_recurrent)
        ofc = self._ofc(new_drive, sign, intensity)
        ec = self._ec(new_drive)
        am = self._amygdala(new_drive, sign, intensity)
        hedonic = self._hedonic(ofc, sign, intensity)

        state = self._classify_state(new_drive, ofc, am)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pir3_drive"] = round(new_drive, 4)
        self.state["ofc_drive_signal"] = round(ofc, 4)
        self.state["ec_drive_signal"] = round(ec, 4)
        self.state["amygdala_drive_signal"] = round(am, 4)
        self.state["hedonic_signal"] = round(hedonic, 4)
        self.state["recurrent_associative_signal"] = round(recurrent, 4)
        self.state["recurrent_trace"] = round(recurrent, 4)
        self.state["pir3_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pir3_drive": round(new_drive, 4),
            "ofc_drive_signal": round(ofc, 4),
            "ec_drive_signal": round(ec, 4),
            "amygdala_drive_signal": round(am, 4),
            "hedonic_signal": round(hedonic, 4),
            "recurrent_associative_signal": round(recurrent, 4),
            "pir3_state": state,
        }

    def _categorization_index(self) -> float:
        """How well Pir-III categorizes via recurrence (Yoshida 2017)."""
        return float(self.state.get("recurrent_associative_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pir3_drive", 0.0),
            "ofc": self.state.get("ofc_drive_signal", 0.0),
            "hedonic": self.state.get("hedonic_signal", 0.0),
            "state": self.state.get("pir3_state", "quiet"),
        }
