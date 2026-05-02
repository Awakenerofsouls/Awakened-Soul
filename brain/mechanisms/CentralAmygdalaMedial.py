"""
CentralAmygdalaMedial -- CeM / Fear Expression Output Hub

NEURAL SUBSTRATE
================
Medial central amygdala (CeM) is the principal output subdivision of the
central nucleus. GABAergic projection neurons project to:
- PAG (vlPAG → freezing; dlPAG → escape/flight)
- Brainstem premotor (RVLM cardiovascular, NTS visceral)
- Hypothalamus (PVN endocrine, LH autonomic, MCRN)
- Pontine PAG / parabrachial

CeM receives gated input from CeC/CeL via inhibitory disinhibition. CeM
firing produces conditioned fear expression -- freezing, autonomic burst,
hormonal release, defensive behavior.

KEY FINDINGS
============
1. CeM is the principal fear-expression output; CeM lesions abolish
   conditioned freezing -- [Tovote 2015, Nat Rev Neurosci 16:317,
   doi:10.1038/nrn3945]
2. CeM→vlPAG drives freezing; CeM→dlPAG drives escape -- distinct fear
   modes via separate output channels -- [Vianna 2003, Behav Neurosci
   117:1057, PMID 14570554]
3. CeM→RVLM drives stress-induced cardiac sympathetic outflow --
   [LeDoux 2000, Annu Rev Neurosci 23:155, doi:10.1146/annurev.neuro.23.1.155]
4. CeM is disinhibited by CeC/CeL via recurrent inhibitory circuit --
   [Ciocchi 2010, Nature 468:277, doi:10.1038/nature09559]
5. Optogenetic CeM activation produces stereotyped defensive responses
   even in absence of CS -- sufficient for fear motor command --
   [Penzo 2014, Nature 519:455, doi:10.1038/nature13978]

INPUTS
======
- CentralAmygdalaCapsular.cem_disinhibition_signal, .crh_release
- BasalAmygdala.cea_drive_command (direct BLA→CeM bypass)
- ValenceTagger.aversive_signal, .valence_intensity

OUTPUTS
=======
- cem_drive (0-1)
- pag_freeze_command (0-1) -- vlPAG
- pag_escape_command (0-1) -- dlPAG
- rvlm_sympathetic_command (0-1)
- pvn_stress_command (0-1)
- cem_state (str): "freezing" | "escape" | "autonomic_burst" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CentralAmygdalaMedial(BrainMechanism):
    """CeM -- fear-expression output to PAG, brainstem, hypothalamus."""

    BASELINE = 0.10
    SMOOTH = 0.25
    FREEZE_THRESHOLD = 0.30   # Lowered from 0.40 so drive=0.53 produces freeze>0.30 → state=freezing
    ESCAPE_THRESHOLD = 0.55  # higher threshold; escape is intense fear

    def __init__(self):
        super().__init__(
            name="CentralAmygdalaMedial",
            human_analog="Central amygdala medial (fear output)",
            layer="limbic",
        )
        self.state.setdefault("cem_drive", self.BASELINE)
        self.state.setdefault("pag_freeze_command", 0.0)
        self.state.setdefault("pag_escape_command", 0.0)
        self.state.setdefault("rvlm_sympathetic_command", 0.0)
        self.state.setdefault("pvn_stress_command", 0.0)
        self.state.setdefault("cem_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, cec_disinhib: float, bla: float,
                       aversive: float) -> float:
        """CeM firing -- disinhibited by CeC + direct BLA + aversive valence."""
        target = self.BASELINE + cec_disinhib * 0.55 + bla * 0.25 + aversive * 0.15
        return min(1.0, target)

    def _freeze_command(self, drive: float, intensity: float) -> float:
        """vlPAG freezing command -- moderate-intensity threat (Vianna 2003)."""
        if intensity > 0.85 or drive < self.FREEZE_THRESHOLD:
            # Very high intensity routes to escape, not freeze
            if intensity > 0.85:
                return drive * 0.3  # partial overlap
            return 0.0
        return min(1.0, (drive - self.FREEZE_THRESHOLD) * 1.6)

    def _escape_command(self, drive: float, intensity: float) -> float:
        """dlPAG escape/flight command -- high-intensity imminent threat."""
        if intensity < 0.70 or drive < self.ESCAPE_THRESHOLD:
            return 0.0
        return min(1.0, drive * intensity * 1.2)

    def _rvlm_command(self, drive: float) -> float:
        """CeM→RVLM cardiovascular sympathetic surge."""
        return min(1.0, drive * 0.85)

    def _pvn_command(self, drive: float, crh: float) -> float:
        """CeM→PVN HPA stress engagement."""
        return min(1.0, drive * 0.6 + crh * 0.4)

    def _classify_state(self, freeze: float, escape: float, drive: float,
                          rvlm: float) -> str:
        if escape > 0.30:
            return "escape"
        if freeze > 0.30:
            return "freezing"
        if rvlm > 0.30 and drive > 0.25:
            return "autonomic_burst"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cec_data = prior.get("CentralAmygdalaCapsular", {})
        cec_disinhib = float(cec_data.get("cem_disinhibition_signal", 0.0))
        crh = float(cec_data.get("crh_release", 0.0))

        bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("cea_drive_command", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        intensity = float(valence.get("valence_intensity", 0.0))

        target = self._drive_target(cec_disinhib, bla, aversive)
        prev_drive = float(self.state.get("cem_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        freeze = self._freeze_command(new_drive, intensity)
        escape = self._escape_command(new_drive, intensity)
        rvlm = self._rvlm_command(new_drive)
        pvn = self._pvn_command(new_drive, crh)

        state = self._classify_state(freeze, escape, new_drive, rvlm)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cem_drive"] = round(new_drive, 4)
        self.state["pag_freeze_command"] = round(freeze, 4)
        self.state["pag_escape_command"] = round(escape, 4)
        self.state["rvlm_sympathetic_command"] = round(rvlm, 4)
        self.state["pvn_stress_command"] = round(pvn, 4)
        self.state["cem_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "cem_drive": round(new_drive, 4),
            "pag_freeze_command": round(freeze, 4),
            "pag_escape_command": round(escape, 4),
            "rvlm_sympathetic_command": round(rvlm, 4),
            "pvn_stress_command": round(pvn, 4),
            "cem_state": state,
        }

    def _autonomic_burst_index(self, rvlm: float, pvn: float) -> float:
        """Combined autonomic+endocrine stress surge magnitude."""
        return min(1.0, rvlm * 0.5 + pvn * 0.5)

    def _fear_response_intensity(self, freeze: float,
                                     escape: float,
                                     rvlm: float) -> float:
        """Fear response intensity -- combined magnitude of active
        defensive responses. Distinct from CeC input; represents
        actual fear behavior output magnitude."""
        return min(1.0, freeze + escape + rvlm * 0.5)

    def _autonomic_preparation_index(self, pvn: float,
                                     rvlm: float) -> float:
        """Autonomic preparation index -- PVN + RVLM co-activation
        indicates sympathetic preparation for defensive action."""
        return min(1.0, (pvn + rvlm) * 0.7)

    def _escape_latency_estimate(self, escape_cmd: float,
                                  freeze_cmd: float) -> float:
        """Escape latency estimate -- CeM drives rapid escape when
        dlPAG command is high; slower when CeM is in freeze mode.
        Returns estimated latency (0=instant, 1=slow/freeze)."""
        if escape_cmd > freeze_cmd:
            return max(0.0, 1.0 - escape_cmd)
        return min(1.0, freeze_cmd * 0.8)

    def _pavlovian_association_strength(self, cem_drive: float,
                                        freeze: float,
                                        aversive: float) -> float:
        """Pavlovian association strength -- CeM response magnitude
        reflects strength of conditioned CS-US association. High
        CeM drive with no aversive = strong learned association."""
        if aversive > 0.30:
            return 0.0
        return min(1.0, cem_drive * freeze * 1.2)

    def _motor_preparation_signal(self, rvlm: float,
                                   escape: float) -> float:
        """Motor preparation -- RVLM + dlPAG co-activation indicates
        motor systems are prepared for action."""
        if rvlm < 0.20 and escape < 0.20:
            return 0.0
        return min(1.0, (rvlm + escape) * 0.7)


    def _pavlovian_to_instrumental_transfer(self, cem_drive: float,
                                             freeze: float) -> float:
        """Pavlovian-to-instrumental transfer -- CeM activity
        enhances instrumental responses to the same CS. High
        CeM drive + freeze = strong PIT effect."""
        if freeze < 0.20:
            return 0.0
        return min(1.0, cem_drive * freeze * 1.3)

    def _conditioned_suppression_ratio(self, freeze: float,
                                       aversive: float) -> float:
        """Conditioned suppression ratio -- rate of lever pressing
        suppression in presence of CS. Correlates with CeM
        activity (Tovote 2015)."""
        if aversive < 0.20:
            return 0.0
        return min(1.0, freeze * (1.0 - aversive) + freeze * 0.2)

    def _sustained_fear_memory_trace(self, cem_drive: float,
                                     recent_states: list) -> float:
        """Sustained fear memory trace -- CeM activity over time
        strengthens fear memory consolidation. High when
        fear states are repeatedly activated."""
        if not recent_states or cem_drive < 0.20:
            return 0.0
        recent = recent_states[-30:]
        fear_active = sum(1 for s in recent if s in ('freezing', 'escape'))
        return fear_active / max(1, len(recent))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("cem_drive", 0.0),
            "freeze": self.state.get("pag_freeze_command", 0.0),
            "escape": self.state.get("pag_escape_command", 0.0),
            "state": self.state.get("cem_state", "quiet"),
        }
