"""
ParatenialNucleus — PT / Midline Thalamic Limbic Relay

NEURAL SUBSTRATE
================
The paratenial thalamic nucleus (PT) is a small midline thalamic nucleus
sitting between the anteromedial and central medial thalamic nuclei.
PT receives strong amygdaloid (BLA, central) and limbic cortical input
and projects to nucleus accumbens, BNST, and prefrontal cortex. PT is
part of the midline-intralaminar thalamic system that delivers limbic
arousal/salience signals to forebrain motivational targets.

PT activity is critical for stress-induced reinstatement of drug-seeking
(Hamlin 2009 — PT inactivation prevents cue-induced reinstatement).
Functionally, PT functions as a limbic salience relay — gating motivated
behavior based on emotionally significant context.

KEY FINDINGS
============
1. Paratenial nucleus projects to nucleus accumbens shell + medial
   prefrontal cortex; midline thalamic limbic relay —
   [Vertes 2009, Brain Struct Funct 213:497, doi:10.1007/s00429-009-0223-7]
2. PT inactivation prevents cue-induced reinstatement of drug-seeking
   behavior; necessary for incentive salience —
   [Hamlin 2009, Eur J Neurosci 29:802, doi:10.1111/j.1460-9568.2009.06623.x]
3. PT receives BLA + central amygdala input + projects to BNST;
   amygdalo-thalamic limbic loop —
   [Li 2014, Front Behav Neurosci 8:266, doi:10.3389/fnbeh.2014.00266]
4. PT-NAc projection drives motivated approach + plays role in
   incentive learning —
   [Otis 2017, Nature 543:103, doi:10.1038/nature21376]
5. PT is part of the midline thalamic salience-relay system; activated
   by stress + reward cues —
   [Berendse 1991, Neuroscience 42:73, PMID 1713657]
"""

from brain.base_mechanism import BrainMechanism


class ParatenialNucleus(BrainMechanism):
    """PT — midline thalamic limbic salience relay."""

    BASELINE = 0.10
    SMOOTH = 0.20
    SALIENCE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="ParatenialNucleus",
            human_analog="Paratenial thalamic nucleus",
            layer="limbic",
        )
        self.state.setdefault("pt_drive", self.BASELINE)
        self.state.setdefault("nac_drive_signal", 0.0)
        self.state.setdefault("pfc_drive_signal", 0.0)
        self.state.setdefault("bnst_drive_signal", 0.0)
        self.state.setdefault("salience_relay_signal", 0.0)
        self.state.setdefault("pt_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, ca: float, intensity: float,
                      arousal: float) -> float:
        """PT drive (Berendse 1991; Li 2014)."""
        target = (self.BASELINE
                  + bla * 0.30
                  + ca * 0.20
                  + intensity * 0.20
                  + arousal * 0.20)
        return min(1.0, target)

    def _nac(self, drive: float, intensity: float) -> float:
        """PT→NAc (Otis 2017)."""
        return min(1.0, drive * 0.55 + intensity * 0.30)

    def _pfc(self, drive: float, arousal: float) -> float:
        """PT→PFC (Vertes 2009)."""
        return min(1.0, drive * 0.5 + arousal * 0.30)

    def _bnst(self, drive: float, ca: float) -> float:
        """PT→BNST (Li 2014)."""
        return min(1.0, drive * 0.4 + ca * 0.4)

    def _salience(self, nac: float, pfc: float, bnst: float) -> float:
        """Combined salience relay (Hamlin 2009)."""
        return min(1.0, max(nac, pfc, bnst) * 0.7 + (nac + pfc + bnst) * 0.10)

    def _classify_state(self, drive: float, salience: float) -> str:
        if drive < 0.20:
            return "quiet"
        if salience > self.SALIENCE_THRESHOLD:
            return "salience_relay"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        ca_data = prior.get("CentralAmygdala", {})
        if not ca_data:
            ca_data = prior.get("CentralAmygdalaMedial", {})
        ca = float(ca_data.get("ca_drive",
                          ca_data.get("cea_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        ar_data = prior.get("ArousalRegulator", {})
        if not ar_data:
            ar_data = prior.get("BrainstemReticular", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.0)))

        target = self._drive_target(bla, ca, intensity, arousal)
        prev_drive = float(self.state.get("pt_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        nac = self._nac(new_drive, intensity)
        pfc = self._pfc(new_drive, arousal)
        bnst = self._bnst(new_drive, ca)
        salience = self._salience(nac, pfc, bnst)

        state = self._classify_state(new_drive, salience)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pt_drive"] = round(new_drive, 4)
        self.state["nac_drive_signal"] = round(nac, 4)
        self.state["pfc_drive_signal"] = round(pfc, 4)
        self.state["bnst_drive_signal"] = round(bnst, 4)
        self.state["salience_relay_signal"] = round(salience, 4)
        self.state["pt_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pt_drive": round(new_drive, 4),
            "nac_drive_signal": round(nac, 4),
            "pfc_drive_signal": round(pfc, 4),
            "bnst_drive_signal": round(bnst, 4),
            "salience_relay_signal": round(salience, 4),
            "pt_state": state,
        }

    def _reinstatement_susceptibility(self) -> float:
        """How much PT is signaling reinstatement-relevant cues (Hamlin 2009)."""
        return float(self.state.get("salience_relay_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pt_drive", 0.0),
            "salience": self.state.get("salience_relay_signal", 0.0),
            "nac": self.state.get("nac_drive_signal", 0.0),
            "state": self.state.get("pt_state", "quiet"),
        }
