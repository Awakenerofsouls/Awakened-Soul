"""
AnteriorOlfactoryNucleus — AON / Bilateral Olfactory Bridge

NEURAL SUBSTRATE
================
The anterior olfactory nucleus (AON, also "anterior olfactory cortex")
sits at the rostral end of the olfactory cortex, immediately caudal to
the olfactory bulb. Receives bidirectional input from olfactory bulb
mitral/tufted cells. AON is the principal substrate for:
- Bilateral olfactory integration via anterior commissure
- Top-down feedback to OB (gain control on incoming odor signals)
- Odor recognition memory + familiarity
- Social olfactory recognition (rodents)

Three subdivisions: pars externa (lateral, AOB-adjacent), pars principalis
(main subdivision), and dorsal/ventral subregions. Pyramidal projection
neurons + GABAergic interneurons.

Outputs: bilateral OB feedback, piriform cortex, olfactory tubercle,
amygdala (via lateral olfactory tract collaterals).

KEY FINDINGS
============
1. AON pars externa is the principal bilateral olfactory integrator;
   contralateral connections via anterior commissure permit binaural
   odor comparison — [Yan 2008, J Neurosci 28:1683, PMID 18272689]
2. AON top-down projection to OB granule cells provides gain control
   on incoming odor signals; activity-dependent plasticity —
   [Markopoulos 2012, Neuron 76:1175, doi:10.1016/j.neuron.2012.10.028]
3. AON is critical for social olfactory recognition memory in rodents;
   selective lesion impairs familiarity discrimination —
   [Kogan 2000, Hippocampus 10:47, PMID 10706226]
4. AON neurons encode odor identity at single-cell resolution; population
   code distinct from OB — [Brunjes 2005, Brain Res Rev 50:305, PMID 16229896]
5. AON shows activity-dependent plasticity to repeated odor exposure;
   familiarity coding distinct from PIRiform cortex —
   [Kay 2003, Trends Neurosci 26:480, PMID 12948660]

INPUTS
======
- OlfactoryBulb.ob_drive
- PiriformCortex.pir_drive (feedback)
- AmygdalaCorticalAnterior.aco_drive (when present)
- ArousalRegulator.tonic_level

OUTPUTS
=======
- aon_drive (0-1)
- bilateral_integration_signal (0-1)
- ob_feedback_command (0-1) — top-down gain control
- olfactory_familiarity_signal (0-1)
- aon_state (str): "novel_odor" | "familiar_odor" |
  "social_recognition" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteriorOlfactoryNucleus(BrainMechanism):
    """AON — bilateral olfactory bridge + top-down OB feedback."""

    BASELINE = 0.10
    SMOOTH = 0.20
    NOVEL_THRESHOLD = 0.50
    FAMILIAR_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="AnteriorOlfactoryNucleus",
            human_analog="Anterior olfactory nucleus (bilateral olfactory)",
            layer="limbic",
        )
        self.state.setdefault("aon_drive", self.BASELINE)
        self.state.setdefault("bilateral_integration_signal", 0.0)
        self.state.setdefault("ob_feedback_command", 0.0)
        self.state.setdefault("olfactory_familiarity_signal", 0.0)
        self.state.setdefault("aon_state", "quiet")
        self.state.setdefault("recent_odors", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, pir: float, aco: float,
                       arousal: float) -> float:
        """AON firing — driven by OB primarily, modulated by feedback."""
        target = self.BASELINE + ob * 0.55 + pir * 0.20 + aco * 0.15
        target += max(0.0, arousal - 0.40) * 0.10
        return min(1.0, target)

    def _bilateral_integration(self, drive: float, ob: float) -> float:
        """Bilateral olfactory integration via anterior commissure
        (Yan 2008)."""
        return min(1.0, drive * 0.6 + ob * 0.4)

    def _ob_feedback(self, drive: float, familiarity: float) -> float:
        """Top-down OB granule-cell gain control (Markopoulos 2012)."""
        return min(1.0, drive * 0.5 + familiarity * 0.5)

    def _familiarity(self, ob: float, recent: list) -> float:
        """Olfactory familiarity (Kay 2003 activity-dependent plasticity)."""
        if ob < 0.20:
            return 0.5  # neutral
        if not recent:
            return 0.10
        similar = sum(1 for o in recent[-30:] if abs(o - ob) < 0.15)
        return min(1.0, 0.30 + similar * 0.05)

    def _classify_state(self, drive: float, familiarity: float, aco: float) -> str:
        if drive < 0.15:
            return "quiet"
        if aco > 0.40:
            return "social_recognition"
        if familiarity < 0.20:
            return "novel_odor"
        if familiarity > self.FAMILIAR_THRESHOLD:
            return "familiar_odor"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive", 0.0))

        pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir_drive", 0.0))

        aco_data = prior.get("AmygdalaCorticalAnterior", {})
        aco = float(aco_data.get("aco_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        target = self._drive_target(ob, pir, aco, arousal)
        prev_drive = float(self.state.get("aon_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        recent = list(self.state.get("recent_odors", []))
        familiarity = self._familiarity(ob, recent)
        bilateral = self._bilateral_integration(new_drive, ob)
        feedback = self._ob_feedback(new_drive, familiarity)

        if ob > 0.20:
            recent.append(round(ob, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        state = self._classify_state(new_drive, familiarity, aco)

        self.state["aon_drive"] = round(new_drive, 4)
        self.state["bilateral_integration_signal"] = round(bilateral, 4)
        self.state["ob_feedback_command"] = round(feedback, 4)
        self.state["olfactory_familiarity_signal"] = round(familiarity, 4)
        self.state["aon_state"] = state
        self.state["recent_odors"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aon_drive": round(new_drive, 4),
            "bilateral_integration_signal": round(bilateral, 4),
            "ob_feedback_command": round(feedback, 4),
            "olfactory_familiarity_signal": round(familiarity, 4),
            "aon_state": state,
        }

    def _social_recognition_index(self, aco: float, familiarity: float) -> float:
        """Social olfactory recognition (Kogan 2000)."""
        return min(1.0, aco * 0.6 + familiarity * 0.4)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("aon_drive", 0.0),
            "familiarity": self.state.get("olfactory_familiarity_signal", 0.0),
            "feedback": self.state.get("ob_feedback_command", 0.0),
            "state": self.state.get("aon_state", "quiet"),
        }
