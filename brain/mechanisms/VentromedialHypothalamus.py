"""
VentromedialHypothalamus — VMH / Defense + Aggression + Satiety + Glucose

NEURAL SUBSTRATE
================
The ventromedial hypothalamus (VMH) is a compact ventral hypothalamic
nucleus, ventral to DMH. Three functionally + molecularly distinct
subpopulations:

- **VMHdm (dorsomedial subdivision)** — Steroidogenic factor 1 (SF1)
  positive. Defense + predator avoidance. Drives PAG defense responses.
- **VMHvl (ventrolateral subdivision)** — estrogen receptor α + progesterone
  receptor positive. Female sexual receptivity + male-male aggression.
- **VMHc (central VMH)** — feeding satiety + glucose-sensing. VMH glucose-
  sensing neurons regulate counter-regulatory response to hypoglycemia.

Inputs: MeA, BLA, ARC, MPOA, BNST.
Outputs: PAG (defense), AHN (defense + aggression), ARC (feeding gate),
VTA (motivation), brainstem premotor.

Classic experimental finding: VMH lesions produce hyperphagia + obesity
(the "VMH satiety syndrome"). Modern dissection shows this is the VMHc
satiety subset.

KEY FINDINGS
============
1. VMHdm SF1+ neurons drive defensive freezing/escape via PAG —
   optogenetic activation produces freezing — [Wang 2015, Cell 162:363,
   doi:10.1016/j.cell.2015.06.034]
2. VMHvl estrogen-receptor+ neurons control female sexual receptivity +
   male aggression intensity — [Lee 2014, Nature 509:627, PMC4119886]
3. VMH glucose-sensing neurons regulate counter-regulatory response to
   hypoglycemia — [Borg 1997, Diabetes 46:1521, PMID 9287054]
4. VMH lesions produce hyperphagia + obesity (VMH satiety syndrome) —
   foundational finding — [Hetherington 1942, Anat Rec 78:149]
5. VMHvl PR+ subset specifically codes male-male aggression intensity —
   [Yang 2017, Cell 171:1176, doi:10.1016/j.cell.2017.10.046]

INPUTS
======
- BasolateralAmygdala.bla_drive
- MedialAmygdala.mea_drive
- ArcuatePOMCSatiety.satiety_signal
- GlucoseProxy.glucose_level (default 0.5 = euglycemia)
- EstrogenProxy.estrogen_level (default 0.5)
- CentralNucleusFearRouter.threat_signal (or .cea_drive)

OUTPUTS
=======
- vmhdm_defense_drive (0-1)
- vmhvl_social_drive (0-1)
- vmhc_satiety_signal (0-1)
- pag_defense_command (0-1)
- ahn_defense_command (0-1)
- glucose_counterregulation (0-1)
- vmh_state (str): "defense" | "social_aggression" | "satiety_active" |
  "hypoglycemic_defense" | "quiet"

brain_runner enrichment:
    vmh = all_results.get("VentromedialHypothalamus", {})
    if vmh:
        enrichments["brain_vmhdm_defense"] = vmh.get("vmhdm_defense_drive", 0.0)
        enrichments["brain_vmhvl_social"] = vmh.get("vmhvl_social_drive", 0.0)
        enrichments["brain_vmhc_satiety"] = vmh.get("vmhc_satiety_signal", 0.0)
        enrichments["brain_pag_defense"] = vmh.get("pag_defense_command", 0.0)
        enrichments["brain_glucose_counterreg"] = vmh.get("glucose_counterregulation", 0.0)
        enrichments["brain_vmh_state"] = vmh.get("vmh_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class VentromedialHypothalamus(BrainMechanism):
    """VMH — three-subnucleus defense/social/satiety hub."""

    SMOOTH = 0.20
    DEFENSE_THRESHOLD = 0.40
    SOCIAL_THRESHOLD = 0.35
    HYPOGLYCEMIA_THRESHOLD = 0.30  # glucose level below this triggers counter-reg

    def __init__(self):
        super().__init__(
            name="VentromedialHypothalamus",
            human_analog="Ventromedial hypothalamus (defense + social + satiety)",
            layer="foundational",
        )
        self.state.setdefault("vmhdm_defense_drive", 0.0)
        self.state.setdefault("vmhvl_social_drive", 0.0)
        self.state.setdefault("vmhc_satiety_signal", 0.0)
        self.state.setdefault("pag_defense_command", 0.0)
        self.state.setdefault("ahn_defense_command", 0.0)
        self.state.setdefault("glucose_counterregulation", 0.0)
        self.state.setdefault("vmh_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # VMHdm — SF1+ defense (Wang 2015)
    # ------------------------------------------------------------------
    def _vmhdm_defense(self, threat: float, mea: float, bla: float) -> float:
        """VMHdm SF1+ neurons fire on predator/threat detection."""
        return min(1.0, threat * 0.50 + mea * 0.30 + bla * 0.20)

    # ------------------------------------------------------------------
    # VMHvl — ER+ social/aggression (Lee 2014, Yang 2017)
    # ------------------------------------------------------------------
    def _vmhvl_social(self, mea: float, estrogen: float, threat: float) -> float:
        """VMHvl ER+ neurons drive social behaviors (sex + aggression)."""
        # Social context detection: MeA + estrogen modulation
        # Suppressed by overt threat (defense priority)
        target = mea * 0.50 + estrogen * 0.40
        target -= threat * 0.30
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # VMHc — satiety (Hetherington 1942, glucose-sensing Borg 1997)
    # ------------------------------------------------------------------
    def _vmhc_satiety(self, satiety: float, glucose: float) -> float:
        """VMHc satiety firing — driven by ARC POMC satiety signal +
        euglycemia (high glucose suppresses hunger via VMH satiety cells).
        """
        return min(1.0, satiety * 0.55 + max(0.0, glucose - 0.40) * 0.40)

    # ------------------------------------------------------------------
    # PAG defense command (Wang 2015)
    # ------------------------------------------------------------------
    def _pag_defense(self, vmhdm: float) -> float:
        """VMHdm → PAG defense command (freezing/escape)."""
        if vmhdm < 0.30:
            return 0.0
        return min(1.0, (vmhdm - 0.30) * 1.6)

    # ------------------------------------------------------------------
    # AHN defense command
    # ------------------------------------------------------------------
    def _ahn_defense(self, vmhdm: float, vmhvl: float, threat: float) -> float:
        """Anterior hypothalamic nucleus defense — both VMHdm + VMHvl
        contribute (overlapping defense + aggression)."""
        return min(1.0, vmhdm * 0.45 + vmhvl * 0.30 + threat * 0.20)

    # ------------------------------------------------------------------
    # Glucose counter-regulation (Borg 1997)
    # ------------------------------------------------------------------
    def _glucose_counterreg(self, glucose: float) -> float:
        """Hypoglycemia triggers counter-regulatory response via VMH
        glucose-sensing neurons.
        """
        if glucose >= self.HYPOGLYCEMIA_THRESHOLD:
            return 0.0
        # Linear ramp as glucose drops below threshold
        return min(1.0, (self.HYPOGLYCEMIA_THRESHOLD - glucose) * 3.0)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, vmhdm: float, vmhvl: float, vmhc: float,
                          glucose_counter: float) -> str:
        """Classify VMH operating mode.

        Priority: defense > hypoglycemic_defense > social > satiety > quiet
        """
        if vmhdm > self.DEFENSE_THRESHOLD:
            return "defense"
        if glucose_counter > 0.30:
            return "hypoglycemic_defense"
        if vmhvl > self.SOCIAL_THRESHOLD:
            return "social_aggression"
        if vmhc > 0.30:
            return "satiety_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _subnucleus_arbitration(self, vmhdm: float, vmhvl: float,
                                  vmhc: float, glucose_counter: float) -> str:
        """Three-subnucleus arbitration (Wang 2015 / Lee 2014 / Hetherington 1942).

        Defense > glucose-counter > social > satiety priority.
        Returns dominant subnucleus name.
        """
        if vmhdm > self.DEFENSE_THRESHOLD:
            return "vmhdm"
        if glucose_counter > 0.30:
            return "vmhc_glucose"
        if vmhvl > self.SOCIAL_THRESHOLD:
            return "vmhvl"
        if vmhc > 0.30:
            return "vmhc_satiety"
        return "none"

    def _bla_threat_to_vmhdm_gain(self, bla: float, threat: float) -> float:
        """BLA→VMHdm threat-amplification gain — predator-detection
        circuits in BLA increase VMHdm SF1+ excitability.
        """
        if (bla + threat) < 0.20:
            return 0.0
        return min(1.0, bla * 0.5 + threat * 0.5)

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "vmhdm": self.state.get("vmhdm_defense_drive", 0.0),
            "vmhvl": self.state.get("vmhvl_social_drive", 0.0),
            "vmhc": self.state.get("vmhc_satiety_signal", 0.0),
            "pag_def": self.state.get("pag_defense_command", 0.0),
            "glucose_counter": self.state.get("glucose_counterregulation", 0.0),
            "state": self.state.get("vmh_state", "quiet"),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        mea_data = prior.get("MedialAmygdala", {})
        mea = float(mea_data.get("mea_drive", 0.0))

        cea_data = prior.get("CentralNucleusFearRouter", {})
        threat = float(cea_data.get("threat_signal",
                            cea_data.get("cea_drive", 0.0)))

        arc = prior.get("ArcuatePOMCSatiety", {})
        satiety = float(arc.get("satiety_signal", 0.0))

        glucose_data = prior.get("GlucoseProxy", {})
        glucose = float(glucose_data.get("glucose_level", 0.5))

        estrogen_data = prior.get("EstrogenProxy", {})
        estrogen = float(estrogen_data.get("estrogen_level", 0.5))

        # --- Three subnuclei ---
        vmhdm_target = self._vmhdm_defense(threat, mea, bla)
        prev_vmhdm = float(self.state.get("vmhdm_defense_drive", 0.0))
        new_vmhdm = self._smooth(prev_vmhdm, vmhdm_target)

        vmhvl_target = self._vmhvl_social(mea, estrogen, threat)
        prev_vmhvl = float(self.state.get("vmhvl_social_drive", 0.0))
        new_vmhvl = self._smooth(prev_vmhvl, vmhvl_target)

        vmhc_target = self._vmhc_satiety(satiety, glucose)
        prev_vmhc = float(self.state.get("vmhc_satiety_signal", 0.0))
        new_vmhc = self._smooth(prev_vmhc, vmhc_target)

        # --- Outputs ---
        pag_def = self._pag_defense(new_vmhdm)
        ahn_def = self._ahn_defense(new_vmhdm, new_vmhvl, threat)
        glucose_counter = self._glucose_counterreg(glucose)

        state = self._classify_state(new_vmhdm, new_vmhvl, new_vmhc,
                                      glucose_counter)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vmhdm_defense_drive"] = round(new_vmhdm, 4)
        self.state["vmhvl_social_drive"] = round(new_vmhvl, 4)
        self.state["vmhc_satiety_signal"] = round(new_vmhc, 4)
        self.state["pag_defense_command"] = round(pag_def, 4)
        self.state["ahn_defense_command"] = round(ahn_def, 4)
        self.state["glucose_counterregulation"] = round(glucose_counter, 4)
        self.state["vmh_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vmhdm_defense_drive": round(new_vmhdm, 4),
            "vmhvl_social_drive": round(new_vmhvl, 4),
            "vmhc_satiety_signal": round(new_vmhc, 4),
            "pag_defense_command": round(pag_def, 4),
            "ahn_defense_command": round(ahn_def, 4),
            "glucose_counterregulation": round(glucose_counter, 4),
            "vmh_state": state,
        }
