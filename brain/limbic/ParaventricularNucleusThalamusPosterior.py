"""
ParaventricularNucleusThalamusPosterior — pPVT / Aversion-Biased Salience Hub

NEURAL SUBSTRATE
================
Posterior paraventricular nucleus of the thalamus (pPVT) is the
aversion-biased counterpart to anterior PVT. pPVT preferentially encodes
threat cues, fear-related context, and stress signals, projecting to
central amygdala (CeA), BNST, and BLA — versus aPVT's preferential
NAc/mPFC projection.

Penzo 2015 demonstrated pPVT→CeA projections are critical for
fear-memory storage and retrieval. pPVT activity also tracks chronic
stress: pPVT silencing reduces fear-related freezing, and pPVT
hyperactivity is observed in chronic stress models. pPVT thus serves as
a thalamic relay for ongoing aversive salience.

KEY FINDINGS
============
1. Posterior PVT projects preferentially to CeA, BLA, and BNST;
   aversion-biased relative to anterior PVT —
   [Li 2008, Front Neuroanat 2:6, doi:10.3389/neuro.05.006.2008]
2. pPVT→CeA projection essential for fear memory storage and
   retrieval; selective silencing reduces freezing —
   [Penzo 2015, Nature 519:455, doi:10.1038/nature13978]
3. pPVT is engaged by chronic stress; persistent hyperactivity
   following repeated stressor exposure —
   [Bhatnagar 2002, Brain Res 957:52, PMID 12443978]
4. pPVT activity gates fear extinction; lesion impairs extinction
   learning —
   [Padilla-Coreano 2012, J Neurosci 32:11305, doi:10.1523/JNEUROSCI.0860-12.2012]
5. pPVT integrates hypothalamic stress signals + amygdaloid input;
   midline thalamic stress hub —
   [Hsu 2014, Front Behav Neurosci 8:73, doi:10.3389/fnbeh.2014.00073]
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularNucleusThalamusPosterior(BrainMechanism):
    """pPVT — posterior aversion-biased thalamic hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AVERSIVE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="ParaventricularNucleusThalamusPosterior",
            human_analog="Posterior paraventricular thalamus (pPVT)",
            layer="limbic",
        )
        self.state.setdefault("ppvt_drive", self.BASELINE)
        self.state.setdefault("cea_drive_signal", 0.0)
        self.state.setdefault("bnst_drive_signal", 0.0)
        self.state.setdefault("fear_memory_signal", 0.0)
        self.state.setdefault("chronic_stress_load", 0.0)
        self.state.setdefault("ppvt_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, hyp: float, bla: float, intensity: float,
                       sign: int) -> float:
        """pPVT drive (Hsu 2014)."""
        aversive = max(0.0, -sign * intensity)
        target = (self.BASELINE
                  + hyp * 0.25
                  + bla * 0.25
                  + aversive * 0.30)
        return min(1.0, target)

    def _cea_drive(self, drive: float, aversive: float) -> float:
        """pPVT→CeA fear pathway (Penzo 2015)."""
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _bnst_drive(self, drive: float, aversive: float) -> float:
        """pPVT→BNST anxiety pathway (Li 2008)."""
        return min(1.0, drive * 0.4 + aversive * 0.6)

    def _fear_memory(self, cea: float, bla: float) -> float:
        """Fear memory storage signal (Penzo 2015)."""
        return min(1.0, cea * 0.6 + bla * 0.4)

    def _chronic_stress(self, prev_stress: float, drive: float,
                         aversive: float) -> float:
        """Chronic stress accumulator (Bhatnagar 2002)."""
        if drive < 0.30 or aversive < 0.20:
            return prev_stress * 0.95
        return min(1.0, prev_stress * 0.97 + aversive * 0.05)

    def _classify_state(self, drive: float, aversive: float,
                         chronic: float) -> str:
        if drive < 0.20:
            return "quiet"
        if chronic > 0.50:
            return "chronic_stress"
        if aversive > self.AVERSIVE_THRESHOLD:
            return "fear_active"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hyp_data = prior.get("HypothalamicLateral", {})
        if not hyp_data:
            hyp_data = prior.get("LateralHypothalamus", {})
        if not hyp_data:
            hyp_data = prior.get("DorsomedialHypothalamus", {})
        hyp = float(hyp_data.get("lh_drive",
                          hyp_data.get("dmh_drive",
                            hyp_data.get("hypothalamus_drive", 0.0))))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        aversive = max(0.0, -sign * intensity)

        target = self._drive_target(hyp, bla, intensity, sign)
        prev_drive = float(self.state.get("ppvt_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        cea = self._cea_drive(new_drive, aversive)
        bnst = self._bnst_drive(new_drive, aversive)
        fear_mem = self._fear_memory(cea, bla)
        prev_stress = float(self.state.get("chronic_stress_load", 0.0))
        chronic = self._chronic_stress(prev_stress, new_drive, aversive)

        state = self._classify_state(new_drive, aversive, chronic)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ppvt_drive"] = round(new_drive, 4)
        self.state["cea_drive_signal"] = round(cea, 4)
        self.state["bnst_drive_signal"] = round(bnst, 4)
        self.state["fear_memory_signal"] = round(fear_mem, 4)
        self.state["chronic_stress_load"] = round(chronic, 4)
        self.state["ppvt_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ppvt_drive": round(new_drive, 4),
            "cea_drive_signal": round(cea, 4),
            "bnst_drive_signal": round(bnst, 4),
            "fear_memory_signal": round(fear_mem, 4),
            "chronic_stress_load": round(chronic, 4),
            "ppvt_state": state,
        }

    def _extinction_resistance(self) -> float:
        """How resistant fear memory is to extinction (Padilla-Coreano 2012)."""
        return float(self.state.get("fear_memory_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ppvt_drive", 0.0),
            "cea": self.state.get("cea_drive_signal", 0.0),
            "chronic": self.state.get("chronic_stress_load", 0.0),
            "state": self.state.get("ppvt_state", "quiet"),
        }
