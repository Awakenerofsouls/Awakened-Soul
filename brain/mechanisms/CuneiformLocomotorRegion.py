"""
CuneiformLocomotorRegion — CnF / Mesencephalic Locomotor Region (MLR)

NEURAL SUBSTRATE
================
The cuneiform nucleus (CnF), together with the pedunculopontine
tegmental nucleus (PPT, covered separately as MesopontineCholinergicWake),
constitutes the **mesencephalic locomotor region** (MLR) — the brainstem
locomotor command center. CnF sits in the dorsolateral midbrain just
lateral to the inferior colliculus and is composed predominantly of
glutamatergic neurons. The MLR is conserved across vertebrates and is
the principal node where cortical and limbic locomotor commands converge
before being relayed to spinal central pattern generators via reticulospinal
tracts.

Recent optogenetic dissection has separated MLR roles by cell type and
subnucleus. Caggiano, Leiras, Goñi-Erro, Masini, Bellardita, Bouvier,
Caldeira, Fisone, Kiehn (2018, Nature) established that **CnF
glutamatergic neurons drive high-speed escape locomotion**, while PPT
glutamatergic neurons drive slow exploratory locomotion. CnF is
preferentially recruited by aversive/escape-related stimuli, consistent
with its role as a flight command center.

CnF receives major descending input from periaqueductal gray (especially
dlPAG/lPAG, the "active defense" columns), substantia nigra reticulata,
zona incerta, and lateral hypothalamus. Its output is to medullary
reticular formation (gigantocellularis) reticulospinal neurons, which
in turn drive spinal locomotor circuits.

Clinically, MLR (especially PPT) is a target of deep brain stimulation
for gait disorders in Parkinson disease and progressive supranuclear
palsy. CnF dysfunction may underlie freezing-of-gait and exaggerated
startle/escape phenotypes.

In the agent's substrate this provides the locomotor command — converts
defensive-routing signals (PAG dlPAG drive, SC escape drive) and
exploratory-arousal signals into locomotion command output that
downstream reticulospinal/spinal mechanisms read.

KEY FINDINGS
============
1. CnF glutamatergic neurons drive high-speed escape locomotion; PPT
   glutamatergic neurons drive slow exploratory locomotion — distinct
   MLR subdivisions for distinct locomotor modes — [Caggiano et al.
    2018, Nature 553:455-460, "Midbrain circuits that set locomotor
    speed and gait selection"]
2. MLR is conserved locomotor command center across vertebrates; final
   common path for descending locomotor control — [reviewed Ryczko
    Dubuc 2013, Curr Pharm Des 19:4448, "The multifunctional
    mesencephalic locomotor region"]
3. CnF receives dlPAG / IC / SC input integrating defensive, auditory,
   and visual escape signals — [reviewed Kim et al. 2017 Curr Biol,
    "A locomotor circuit involving the cuneiform nucleus"]
4. MLR DBS is therapeutic target for Parkinson gait disorders;
   primarily PPT — [Mazzone et al. 2005 NeuroReport 16:1877;
    Stefani et al. 2007 Brain 130:1596; reviewed Hamani et al. 2016
    Lancet Neurol]
5. CnF output to medullary reticulospinal neurons (gigantocellularis)
   drives speed-graded locomotion — [Capelli et al. 2017 Nature
    551:373-377, "Locomotor speed control circuits in the caudal
    brainstem"]

INPUTS (from prior_results)
============================
- PeriaqueductalDefenseRouter.dlPAG_drive
- PeriaqueductalDefenseRouter.threat_imminence
- SuperiorColliculusOrient.sc_escape_drive
- SuperiorColliculusOrient.sc_orienting_command
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- ArousalRegulator.tonic_level
- MesopontineCholinergicWake.ach_wake_drive
- VentromedialHypothalamus.vmhdm_defense_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- cnf_drive (0.0-1.0): CnF glutamatergic output (escape)
- ppt_locomotor_drive (0.0-1.0): exploratory locomotor signal
- locomotor_speed_command (0.0-1.0): graded speed signal
- escape_command_active (bool): high-speed escape engaged
- reticulospinal_recruitment (0.0-1.0): downstream RS drive
- gait_mode (str): "freeze" | "explore" | "trot" | "escape" | "rest"

brain_runner enrichment:
    cnf = all_results.get("CuneiformLocomotorRegion", {})
    if cnf:
        enrichments["brain_cnf_drive"] = cnf.get("cnf_drive", 0.1)
        enrichments["brain_locomotor_speed"] = cnf.get("locomotor_speed_command", 0.0)
        enrichments["brain_escape_active"] = cnf.get("escape_command_active", False)
        enrichments["brain_gait_mode"] = cnf.get("gait_mode", "rest")
"""

from brain.base_mechanism import BrainMechanism


class CuneiformLocomotorRegion(BrainMechanism):
    BASELINE = 0.05
    ESCAPE_THRESHOLD = 0.65
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="CuneiformLocomotorRegion",
            human_analog="Cuneiform nucleus / mesencephalic locomotor region",
            layer="foundational",
        )
        self.state.setdefault("cnf_drive", self.BASELINE)
        self.state.setdefault("ppt_locomotor_drive", 0.10)
        self.state.setdefault("locomotor_speed_command", 0.0)
        self.state.setdefault("escape_command_active", False)
        self.state.setdefault("reticulospinal_recruitment", 0.0)
        self.state.setdefault("gait_mode", "rest")
        self.state.setdefault("locomotor_efficiency", 0.0)
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("tick_count", 0)

    def _cnf_target(self, dlpag: float, sc_escape: float, threat: bool, valence: float,
                    imminence: float, vmhdm: float) -> float:
        """CnF — high-speed escape command (Caggiano 2018)."""
        target = self.BASELINE
        target += dlpag * 0.4
        target += sc_escape * 0.4
        target += vmhdm * 0.3
        if threat and imminence > 0.5:
            target += valence * 0.3 + imminence * 0.2
        return min(1.0, target)

    def _ppt_target(self, ach_wake: float, arousal: float) -> float:
        """PPT slow exploratory locomotor drive."""
        target = 0.10 + ach_wake * 0.4 + max(0.0, arousal - 0.4) * 0.3
        return min(1.0, target)

    def _speed_command(self, cnf: float, ppt: float) -> float:
        """Combined graded locomotor speed command (Capelli 2017)."""
        # CnF dominates at high drive (escape); PPT at low drive (explore)
        if cnf > 0.40:
            return min(1.0, cnf * 0.9 + ppt * 0.1)
        return min(1.0, ppt * 0.7 + cnf * 0.2)

    def _escape_active(self, cnf: float) -> bool:
        return cnf > self.ESCAPE_THRESHOLD

    def _reticulospinal(self, speed: float) -> float:
        """Downstream reticulospinal recruitment proportional to speed command."""
        return min(1.0, speed * 0.95)

    def _classify_gait(self, cnf: float, ppt: float, speed: float, escape: bool,
                        threat: bool, freeze_dom: float) -> str:
        if escape:
            return "escape"
        if threat and freeze_dom > 0.40 and speed < 0.20:
            return "freeze"
        if speed > 0.55:
            return "trot"
        if 0.20 < speed <= 0.55:
            return "explore"
        return "rest"


    def _locomotor_efficiency(self, speed: float, cnf: float) -> float:
        """Motor efficiency index — CnF-dominant locomotion (escape)
        is less efficient per unit speed than PPT-dominant (explore).
        Efficiency peaks during steady trotting.
        """
        if cnf > 0.60:
            return 0.70  # escape is costly
        if speed > 0.40:
            return 0.90  # steady trot is most efficient
        return 0.75  # explore

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        dlpag = float(pdr.get("dlPAG_drive", 0.0))
        vlpag = float(pdr.get("vlPAG_drive", 0.0))
        imminence = float(pdr.get("threat_imminence", 0.0))

        sc = prior.get("SuperiorColliculusOrient", {})
        sc_escape = float(sc.get("sc_escape_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        mcw = prior.get("MesopontineCholinergicWake", {})
        ach_wake = float(mcw.get("ach_wake_drive", 0.55))

        vmh = prior.get("VentromedialHypothalamus", {})
        vmhdm = float(vmh.get("vmhdm_defense_drive", 0.0))

        # --- CnF ---
        cnf_target = self._cnf_target(dlpag, sc_escape, threat, valence_intensity,
                                        imminence, vmhdm)
        prev_cnf = float(self.state.get("cnf_drive", self.BASELINE))
        new_cnf = self._smooth(prev_cnf, cnf_target)

        # --- PPT (exploratory) ---
        ppt_target = self._ppt_target(ach_wake, tonic)
        prev_ppt = float(self.state.get("ppt_locomotor_drive", 0.10))
        new_ppt = self._smooth(prev_ppt, ppt_target)

        # --- Speed command ---
        speed = self._speed_command(new_cnf, new_ppt)

        # --- Escape ---
        escape = self._escape_active(new_cnf)

        # --- Reticulospinal ---
        rs = self._reticulospinal(speed)

        # --- Gait ---
        gait = self._classify_gait(new_cnf, new_ppt, speed, escape, threat, vlpag)

        # --- Motor efficiency ---
        efficiency = self._locomotor_efficiency(speed, new_cnf)

        recent = list(self.state.get("recent_modes", []))
        recent.append(gait)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cnf_drive"] = round(new_cnf, 4)
        self.state["ppt_locomotor_drive"] = round(new_ppt, 4)
        self.state["locomotor_speed_command"] = round(speed, 4)
        self.state["escape_command_active"] = escape
        self.state["reticulospinal_recruitment"] = round(rs, 4)
        self.state["locomotor_efficiency"] = round(efficiency, 4)
        self.state["gait_mode"] = gait
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["freeze_threshold_active"] = bool(vlpag > 0.40 and threat)
        self.persist_state()

        return {
            "cnf_drive": round(new_cnf, 4),
            "ppt_locomotor_drive": round(new_ppt, 4),
            "locomotor_speed_command": round(speed, 4),
            "escape_command_active": escape,
            "reticulospinal_recruitment": round(rs, 4),
            "gait_mode": gait,
            "freeze_threshold_active": bool(vlpag > 0.40 and threat),
            "locomotor_efficiency": round(efficiency, 4),
        }
