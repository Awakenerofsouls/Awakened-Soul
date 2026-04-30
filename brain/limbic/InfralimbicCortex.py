"""
InfralimbicCortex -- IL / Fear Extinction Hub

NEURAL SUBSTRATE
================
Infralimbic cortex (IL, ventral mPFC, rodent area 25) sits ventral to PL.
Functionally OPPOSITE to PL: IL drives fear EXTINCTION while PL drives
fear EXPRESSION. Both share mPFC location but project to different
amygdala targets.

IL projection neurons:
- → ITC clusters (drives feedforward inhibition of CeA)
- → Accessory basal amygdala (extinction neurons)
- → BA extinction neuron population (Herry 2008)
- → CeL-off / PKCδ+ interneurons

Milad & Quirk 2002 demonstrated IL neurons signal extinction memory:
fire to CS only during extinction recall (not original conditioning).
Critical for safety learning + recall.

KEY FINDINGS
============
1. IL neurons signal memory for fear extinction; fire to CS only during
   extinction recall -- [Milad 2002, Nature 420:70, doi:10.1038/nature01138]
2. IL→ITC pathway drives feedforward inhibition of CeA during
   extinction expression -- [Berretta 2005, Neuroscience 132:943,
   PMID 15857800]
3. Pharmacological stimulation of IL after fear conditioning
   facilitates subsequent extinction; converse for PL --
   [Sotres-Bayon 2010, Neuron 76:804, doi:10.1016/j.neuron.2012.09.028]
4. Bidirectional optogenetic mPFC control: IL stim enhances extinction,
   PL stim enhances fear -- [Vidal-Gonzalez 2006, Learn Mem 13:728,
   doi:10.1101/lm.306106]
5. IL-deficient PTSD patients show impaired extinction recall;
   structural + functional IL abnormalities -- [Milad 2009, Biol
   Psychiatry 66:1075, doi:10.1016/j.biopsych.2009.06.026]

INPUTS
======
- HippocampalCA1Output.ca1_drive (context-extinction binding)
- AccessoryBasalAmygdala.aba_drive
- ValenceTagger.valence_sign, .valence_intensity
- DorsalRapheSerotonin.dr_drive (5HT extinction support)
- LocusCoeruleusCore.lc_tonic_firing

OUTPUTS
=======
- il_drive (0-1)
- extinction_signal (0-1)
- itc_drive_command (0-1)
- aba_drive_command (0-1)
- safety_recall_signal (0-1)
- il_state (str): "extinction_active" | "safety_recall" |
  "extinction_consolidating" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class InfralimbicCortex(BrainMechanism):
    """IL -- fear extinction + safety memory mPFC hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    EXTINCTION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="InfralimbicCortex",
            human_analog="Infralimbic cortex (fear extinction)",
            layer="limbic",
        )
        self.state.setdefault("il_drive", self.BASELINE)
        self.state.setdefault("extinction_signal", 0.0)
        self.state.setdefault("itc_drive_command", 0.0)
        self.state.setdefault("aba_drive_command", 0.0)
        self.state.setdefault("safety_recall_signal", 0.0)
        self.state.setdefault("il_state", "quiet")
        self.state.setdefault("extinction_consolidation", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ca1: float, aba: float, dr: float,
                       appetitive: float, lc: float, sign_int: int) -> float:
        """IL firing -- driven by hippocampal context + safety signals."""
        target = self.BASELINE + ca1 * 0.25 + aba * 0.25 + dr * 0.20
        target += appetitive * 0.20
        # IL prefers low-to-moderate LC tonic for extinction encoding
        if lc < 0.65:
            target += max(0.0, lc - 0.20) * 0.10
        return min(1.0, target)

    def _extinction_signal(self, drive: float, ca1: float,
                             prev_consolidation: float) -> float:
        """Extinction signal -- fires when context predicts safety
        (Milad 2002 IL neurons fire to CS during extinction recall).
        Strong when consolidation memory present + context match.
        """
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + ca1 * 0.3 + prev_consolidation * 0.2)

    def _itc_command(self, drive: float, extinction: float) -> float:
        """IL→ITC feedforward inhibition (Berretta 2005)."""
        return min(1.0, drive * 0.5 + extinction * 0.5)

    def _aba_command(self, drive: float) -> float:
        """IL→ABA extinction-encoding amygdala drive."""
        return min(1.0, drive * 0.85)

    def _safety_recall(self, extinction: float, ca1: float) -> float:
        """Safety recall signal -- extinction memory engaged in matching context."""
        if ca1 < 0.20:
            return 0.0
        return min(1.0, extinction * 0.6 + ca1 * 0.4)

    def _classify_state(self, drive: float, extinction: float,
                          safety_recall: float, consolidation: float) -> str:
        if safety_recall > 0.30:
            return "safety_recall"
        if extinction > self.EXTINCTION_THRESHOLD:
            return "extinction_active"
        if consolidation > 0.20 and drive > 0.20:
            return "extinction_consolidating"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        aba_data = prior.get("AccessoryBasalAmygdala", {})
        aba = float(aba_data.get("aba_drive", 0.0))

        dr_data = prior.get("DorsalRapheSerotonin", {})
        dr = float(dr_data.get("dr_drive", dr_data.get("serotonin_drive", 0.30)))

        valence = prior.get("ValenceTagger", {})
        sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        appetitive = max(0.0, sign * intensity)

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc = float(lc_data.get("lc_tonic_firing", 0.20))

        target = self._drive_target(ca1, aba, dr, appetitive, lc, sign)
        prev_drive = float(self.state.get("il_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_consolidation = float(self.state.get("extinction_consolidation", 0.0))

        extinction = self._extinction_signal(new_drive, ca1, prev_consolidation)
        itc_cmd = self._itc_command(new_drive, extinction)
        aba_cmd = self._aba_command(new_drive)
        safety_recall = self._safety_recall(extinction, ca1)

        # Slowly accumulate consolidation when extinction is active
        if extinction > 0.30:
            new_consolidation = min(1.0, prev_consolidation * 0.998 + 0.005)
        else:
            new_consolidation = prev_consolidation * 0.998

        state = self._classify_state(new_drive, extinction, safety_recall,
                                       new_consolidation)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["il_drive"] = round(new_drive, 4)
        self.state["extinction_signal"] = round(extinction, 4)
        self.state["itc_drive_command"] = round(itc_cmd, 4)
        self.state["aba_drive_command"] = round(aba_cmd, 4)
        self.state["safety_recall_signal"] = round(safety_recall, 4)
        self.state["extinction_consolidation"] = round(new_consolidation, 4)
        self.state["il_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "il_drive": round(new_drive, 4),
            "extinction_signal": round(extinction, 4),
            "itc_drive_command": round(itc_cmd, 4),
            "aba_drive_command": round(aba_cmd, 4),
            "safety_recall_signal": round(safety_recall, 4),
            "il_state": state,
        }

    def _ptsd_extinction_deficit(self) -> float:
        """Proxy for PTSD-like extinction recall deficit (Milad 2009).

        Returns 0-0.5 indicating severity of extinction consolidation
        impairment. High values suggest PTSD-like extinction failure.
        """
        return max(0.0, 0.5 - self.state.get("extinction_consolidation", 0.0))

    def _extinction_strength_index(self, recent_states: list) -> float:
        """Extinction strength -- proportion of recent ticks in extinction
        states. Higher = stronger extinction memory trace.

        Milad 2009 showed extinction recall correlates with IL activation
        during CS exposure. Stronger extinction = more IL engagement.
        """
        if not recent_states:
            return 0.0
        recent = recent_states[-30:]
        active = sum(1 for s in recent if s in (
            "extinction_active", "safety_recall",
            "extinction_consolidating"
        ))
        return active / max(1, len(recent))

    def _fear_renewal_risk(self, ca1: float, extinction: float,
                             consolidation: float) -> float:
        """Fear renewal risk -- context mismatch increases renewal.

        Renewal (Bouton 2002): extinguished fear returns when CS is presented
        in a context different from extinction. High CA1 (new context) +
        low consolidation + low extinction = high renewal risk.
        """
        if ca1 < 0.30:
            return 0.0
        if consolidation > 0.40:
            return 0.0
        risk = ca1 * (1.0 - consolidation) * (1.0 - extinction)
        return min(1.0, risk * 2.0)

    def _context_generalization_window(self, ca1: float, recent_states: list,
                                        extinction: float) -> float:
        """Context generalization -- can the extinction memory transfer to
        novel contexts? Based on CA1 pattern separation + IL engagement.

        Strong generalization requires: high CA1 (pattern completion),
        sustained IL activation, and established consolidation.
        """
        if not recent_states or ca1 < 0.20:
            return 0.0
        recent = recent_states[-30:]
        il_active = sum(1 for s in recent if "extinction" in s or "safety" in s)
        if il_active / max(1, len(recent)) < 0.50:
            return 0.0
        return min(1.0, ca1 * extinction * 0.8 + ca1 * 0.2)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("il_drive", 0.0),
            "extinction": self.state.get("extinction_signal", 0.0),
            "safety_recall": self.state.get("safety_recall_signal", 0.0),
            "state": self.state.get("il_state", "quiet"),
        }
