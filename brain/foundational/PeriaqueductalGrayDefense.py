"""
PeriaqueductalGrayDefense — PAG Defensive Behavior Coordinator

NEURAL SUBSTRATE
================
The periaqueductal gray (PAG) is a column of grey matter surrounding
the cerebral aqueduct in the midbrain. Functionally organized into
four longitudinal columns with distinct defensive behavior assignments
(Bandler & Shipley 1994; Carrive 1993):

- **Dorsomedial PAG (dmPAG)** — passive coping, conditioned freezing
- **Dorsolateral PAG (dlPAG)** — active escape, predator-imminent
  flight; sympathoexcitation, hypertension
- **Lateral PAG (lPAG)** — confrontational defense, fight, flight
- **Ventrolateral PAG (vlPAG)** — passive immobility (tonic
  immobility), parasympathetic dominance, pain modulation, opioid
  analgesia

Tovote 2016 reviewed the molecular + circuit logic of PAG-mediated
defensive behaviors. The PAG receives convergent input from amygdala
(CeA → vlPAG = freezing), hypothalamus (VMH → dlPAG = escape), and
cortex (mPFC → vlPAG = top-down regulation). PAG outputs to brainstem
premotor (NRM, gigantocellular reticular), spinal cord, and autonomic
nuclei, executing the defensive behavior selected by upstream inputs.

Bandler 2000 framework: predator-imminent threats engage dlPAG/lPAG
(active defense — escape, fight); inescapable threats engage vlPAG
(freezing, opioid analgesia, "playing dead").

KEY FINDINGS
============
1. Bandler & Shipley four-column PAG organization for distinct defensive responses; foundational anatomy — [Bandler R 1994, Trends Neurosci 17:379, doi:10.1016/0166-2236(94)90047-7]
2. Tovote review of midbrain circuits for defensive behavior; PAG as principal output coordinator — [Tovote P 2015, Nat Rev Neurosci 16:317, doi:10.1038/nrn3945]
3. CeA → vlPAG drives freezing; dlPAG/lPAG drive escape/fight; circuit specificity — [Tovote P 2016, Nature 534:206, doi:10.1038/nature17996]
4. Bandler functional organization of PAG: active vs passive defensive coping strategies — [Bandler R 2000, Brain Res Bull 53:95, doi:10.1016/S0361-9230(00)00313-0]
5. PAG opioid-mediated descending pain inhibition; vlPAG-RVM-spinal pathway — [Carrive P 1993, Behav Brain Res 58:27, doi:10.1016/0166-4328(93)90087-7]

INPUTS (from prior_results)
============================
- CentralAmygdalaMedial.cea_drive (freezing driver to vlPAG)
- VentromedialHypothalamus.vmhdm_defense_drive (escape to dlPAG)
- VentromedialPrefrontalCortex.vmpfc_drive (top-down regulation)
- ValenceTagger.aversive_signal, .threat_signal
- ParabigeminalEscapeRelay.pbgn_drive (escape relay)

OUTPUTS (to brain_runner enrichment)
=====================================
- pag_drive (0-1)
- dmpag_passive_freeze (0-1)
- dlpag_escape_command (0-1)
- lpag_fight_command (0-1)
- vlpag_immobility_analgesia (0-1)
- descending_pain_inhibition (0-1) — vlPAG → RVM analgesic command
- defensive_state (str): "passive_freeze" | "active_escape" | "fight" |
  "tonic_immobility" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PeriaqueductalGrayDefense(BrainMechanism):
    """PAG four-column defensive behavior coordinator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    DEFENSE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="PeriaqueductalGrayDefense",
            human_analog="Periaqueductal gray (defensive coordinator)",
            layer="foundational",
        )
        self.state.setdefault("pag_drive", self.BASELINE)
        self.state.setdefault("dmpag_passive_freeze", 0.0)
        self.state.setdefault("dlpag_escape_command", 0.0)
        self.state.setdefault("lpag_fight_command", 0.0)
        self.state.setdefault("vlpag_immobility_analgesia", 0.0)
        self.state.setdefault("descending_pain_inhibition", 0.0)
        self.state.setdefault("defensive_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, cea: float, vmh: float, vmpfc: float,
                       aversive: float) -> float:
        """PAG drive — convergent input (Bandler 1994, Tovote 2015)."""
        target = (self.BASELINE + cea * 0.30 + vmh * 0.25
                    + aversive * 0.25 - vmpfc * 0.10)
        return max(0.0, min(1.0, target))

    def _vlpag_freeze(self, drive: float, cea: float,
                       inescapable: bool) -> float:
        """Ventrolateral PAG freeze + tonic immobility (Tovote 2016 —
        CeA → vlPAG)."""
        if drive < 0.20:
            return 0.0
        # vlPAG is the dominant freeze column when amygdala drives it
        base = drive * 0.4 + cea * 0.5
        if inescapable:
            base += 0.15
        return min(1.0, base)

    def _dlpag_escape(self, drive: float, vmh: float,
                       imminent: bool) -> float:
        """Dorsolateral PAG escape command (Bandler 2000 active defense)."""
        if drive < 0.20:
            return 0.0
        base = drive * 0.4 + vmh * 0.5
        if imminent:
            base += 0.15
        return min(1.0, base)

    def _lpag_fight(self, drive: float, vmh: float, intensity: float) -> float:
        """Lateral PAG fight/confrontation."""
        if drive < 0.30:
            return 0.0
        return min(1.0, drive * 0.4 + vmh * 0.3 + intensity * 0.3)

    def _dmpag_passive(self, drive: float, vmpfc: float) -> float:
        """Dorsomedial PAG conditioned freezing — top-down vmPFC regulated."""
        if drive < 0.20:
            return 0.0
        # Higher vmPFC = more passive coping, less arousal
        return min(1.0, drive * 0.5 + vmpfc * 0.3)

    def _descending_pain(self, vlpag: float) -> float:
        """vlPAG → RVM → spinal cord analgesia (Carrive 1993 opioid)."""
        return min(1.0, vlpag * 0.85)

    def _classify_state(self, dlpag: float, lpag: float, vlpag: float,
                          dmpag: float) -> str:
        max_v = max(dlpag, lpag, vlpag, dmpag)
        if max_v < 0.30:
            return "quiet"
        if vlpag > self.DEFENSE_THRESHOLD and vlpag >= dlpag:
            if vlpag > 0.60:
                return "tonic_immobility"
            return "passive_freeze"
        if dlpag > self.DEFENSE_THRESHOLD:
            return "active_escape"
        if lpag > self.DEFENSE_THRESHOLD:
            return "fight"
        if dmpag > self.DEFENSE_THRESHOLD:
            return "passive_freeze"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cea_data = prior.get("CentralAmygdalaMedial", {})
        if not cea_data:
            cea_data = prior.get("CentralAmygdala", {})
        cea = float(cea_data.get("cea_drive",
                          cea_data.get("ca_drive", 0.0)))

        vmh_data = prior.get("VentromedialHypothalamus", {})
        vmh = float(vmh_data.get("vmhdm_defense_drive",
                          vmh_data.get("vmh_drive", 0.0)))

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive",
                            vmpfc_data.get("amygdala_inhibition", 0.0)))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        intensity = float(valence.get("valence_intensity", 0.0))

        # Heuristic: imminent threat = high VMH + high aversive
        imminent = (vmh > 0.50 and aversive > 0.50)
        # Inescapable threat = high CeA + low vmh (no escape route)
        inescapable = (cea > 0.50 and vmh < 0.30)

        target = self._drive_target(cea, vmh, vmpfc, aversive)
        prev_drive = float(self.state.get("pag_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        vlpag = self._vlpag_freeze(new_drive, cea, inescapable)
        dlpag = self._dlpag_escape(new_drive, vmh, imminent)
        lpag = self._lpag_fight(new_drive, vmh, intensity)
        dmpag = self._dmpag_passive(new_drive, vmpfc)
        pain_inhib = self._descending_pain(vlpag)

        state = self._classify_state(dlpag, lpag, vlpag, dmpag)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pag_drive"] = round(new_drive, 4)
        self.state["dmpag_passive_freeze"] = round(dmpag, 4)
        self.state["dlpag_escape_command"] = round(dlpag, 4)
        self.state["lpag_fight_command"] = round(lpag, 4)
        self.state["vlpag_immobility_analgesia"] = round(vlpag, 4)
        self.state["descending_pain_inhibition"] = round(pain_inhib, 4)
        self.state["defensive_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pag_drive": round(new_drive, 4),
            "dmpag_passive_freeze": round(dmpag, 4),
            "dlpag_escape_command": round(dlpag, 4),
            "lpag_fight_command": round(lpag, 4),
            "vlpag_immobility_analgesia": round(vlpag, 4),
            "descending_pain_inhibition": round(pain_inhib, 4),
            "defensive_state": state,
        }

    def _trauma_proxy(self, recent_states: list) -> float:
        """Sustained tonic_immobility = trauma freezing proxy
        (Carrive 1993 vlPAG opioid-mediated)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        ti = sum(1 for s in win if s == "tonic_immobility")
        return ti / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pag_drive", 0.0),
            "freeze": self.state.get("vlpag_immobility_analgesia", 0.0),
            "escape": self.state.get("dlpag_escape_command", 0.0),
            "state": self.state.get("defensive_state", "quiet"),
        }
