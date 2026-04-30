"""
CentralLateralIntralaminar — CL / Cortical Arousal Driver

NEURAL SUBSTRATE
================
The central lateral intralaminar nucleus (CL) is one of the principal
intralaminar thalamic nuclei. Together with centromedian-parafascicular
complex (CMPf), CL drives non-specific cortical arousal and supports
sustained attention. CL receives ascending reticular input from
brainstem (PPN/LDT cholinergic, locus coeruleus NE, serotonin) and
projects diffusely to frontal cortex and dorsal striatum.

Functionally CL is necessary for cortical state transitions that support
conscious processing — bilateral lesion produces severe attentional
deficits and reduced level of consciousness. CL deep-brain stimulation
has been investigated as a treatment for disorders of consciousness
(Schiff 2007).

KEY FINDINGS
============
1. Central lateral intralaminar nucleus drives diffuse cortical arousal
   via thalamocortical activation —
   [Steriade 1990, Annu Rev Neurosci 13:441, doi:10.1146/annurev.ne.13.030190.002301]
2. Bilateral intralaminar (CL+CM) lesion produces severe reduction in
   conscious-level + attentional deficit —
   [Bogen 1995, Conscious Cogn 4:52, PMID 7497099]
3. Deep brain stimulation of CL improves arousal/responsiveness in
   minimally conscious patients —
   [Schiff 2007, Nature 448:600, doi:10.1038/nature06041]
4. CL projects diffusely to frontal + cingulate cortex; supports
   sustained attention and goal-directed behavior —
   [Van der Werf 2002, Brain Res Rev 39:107, PMID 12423763]
5. CL activity tracks behavioral arousal + sleep-wake transitions;
   key node for vigilance —
   [Saalmann 2014, Front Syst Neurosci 8:83, doi:10.3389/fnsys.2014.00083]
"""

from brain.base_mechanism import BrainMechanism


class CentralLateralIntralaminar(BrainMechanism):
    """CL — intralaminar cortical arousal driver."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AROUSAL_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="CentralLateralIntralaminar",
            human_analog="Central lateral intralaminar nucleus",
            layer="limbic",
        )
        self.state.setdefault("cl_drive", self.BASELINE)
        self.state.setdefault("cortical_arousal_signal", 0.0)
        self.state.setdefault("striatum_drive_signal", 0.0)
        self.state.setdefault("vigilance_signal", 0.0)
        self.state.setdefault("cl_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ppn: float, lc: float, raphe: float) -> float:
        """CL drive (Steriade 1990)."""
        target = (self.BASELINE
                  + ppn * 0.35
                  + lc * 0.25
                  + raphe * 0.15)
        return min(1.0, target)

    def _cortical_arousal(self, drive: float, ppn: float) -> float:
        """Diffuse cortical arousal (Schiff 2007)."""
        return min(1.0, drive * 0.6 + ppn * 0.3)

    def _striatum_drive(self, drive: float) -> float:
        """CL → dorsal striatum (Van der Werf 2002)."""
        return min(1.0, drive * 0.7)

    def _vigilance(self, arousal: float, drive: float) -> float:
        """Sustained vigilance signal (Saalmann 2014)."""
        return min(1.0, arousal * 0.6 + drive * 0.4)

    def _classify_state(self, drive: float, arousal: float) -> str:
        if drive < 0.20:
            return "quiet"
        if arousal > self.AROUSAL_THRESHOLD:
            return "high_arousal"
        return "vigilant"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ppn_data = prior.get("PedunculopontineCholinergic", {})
        if not ppn_data:
            ppn_data = prior.get("PedunculopontineNucleus", {})
        ppn = float(ppn_data.get("ppn_drive",
                          ppn_data.get("ach_signal", 0.0)))

        lc_data = prior.get("LocusCoeruleusCore", {})
        if not lc_data:
            lc_data = prior.get("LocusCoeruleus", {})
        lc = float(lc_data.get("lc_drive",
                          lc_data.get("ne_signal", 0.0)))

        raphe_data = prior.get("DorsalRaphe", {})
        if not raphe_data:
            raphe_data = prior.get("RapheNuclei", {})
        raphe = float(raphe_data.get("raphe_drive",
                            raphe_data.get("serotonin_signal", 0.0)))

        target = self._drive_target(ppn, lc, raphe)
        prev_drive = float(self.state.get("cl_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        arousal = self._cortical_arousal(new_drive, ppn)
        striatum = self._striatum_drive(new_drive)
        vigilance = self._vigilance(arousal, new_drive)

        state = self._classify_state(new_drive, arousal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cl_drive"] = round(new_drive, 4)
        self.state["cortical_arousal_signal"] = round(arousal, 4)
        self.state["striatum_drive_signal"] = round(striatum, 4)
        self.state["vigilance_signal"] = round(vigilance, 4)
        self.state["cl_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "cl_drive": round(new_drive, 4),
            "cortical_arousal_signal": round(arousal, 4),
            "striatum_drive_signal": round(striatum, 4),
            "vigilance_signal": round(vigilance, 4),
            "cl_state": state,
        }

    def _consciousness_support_index(self) -> float:
        """Cortical arousal support for conscious processing (Schiff 2007)."""
        return float(self.state.get("cortical_arousal_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("cl_drive", 0.0),
            "arousal": self.state.get("cortical_arousal_signal", 0.0),
            "vigilance": self.state.get("vigilance_signal", 0.0),
            "state": self.state.get("cl_state", "quiet"),
        }
