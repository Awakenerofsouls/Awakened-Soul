"""
MedullaryRaphePallidus — rRPa Sympathetic Premotor / BAT Thermogenesis Driver

NEURAL SUBSTRATE
================
The medullary raphe pallidus (RPa), particularly its rostral subdivision
(rRPa), is the principal sympathetic premotor structure of the medulla
for thermoregulatory and metabolic outflow. It sits in the midline of
the rostral medulla and contains both serotonergic (5-HT) neurons and
non-serotonergic VGLUT3+ glutamatergic neurons that project directly
to spinal sympathetic preganglionic neurons in the intermediolateral
column (IML).

The rRPa is the final medullary station for descending control of brown
adipose tissue (BAT) thermogenesis and cutaneous vasoconstriction. Cold
exposure or central PGE2 (fever) administration activates rRPa neurons,
and their stimulation drives sympathetic outflow that produces BAT
non-shivering thermogenesis, shivering, and cutaneous vasoconstriction
to conserve and produce heat. Suppression of rRPa abolishes sympathetic
BAT thermogenesis and cold-defense (Morrison and colleagues).

The rRPa receives major descending excitatory drive from the dorsomedial
hypothalamus (DMH) for psychogenic-stress thermogenesis, from the median
preoptic area (MnPO) inhibitory pathway for warm-defense braking, and
from orexin/perifornical hypothalamic neurons that augment BAT
thermogenesis (Tupone et al. 2011).

VGLUT3+ neurons in rRPa are the principal cold-/PGE2-responsive
glutamatergic premotor neurons; they distinct from serotonergic raphe
neurons that contribute distinct functions. The raphe magnus (NRM)
already covered separately handles descending pain modulation; rRPa
specializes in autonomic/thermal premotor function.

In Nova's substrate this provides the descending sympathetic premotor
channel for thermogenesis and cardiovascular cold-defense — engaged
by DMH stress drive, MnPO release (cold/fever), and orexin.

KEY FINDINGS
============
1. rRPa contains sympathetic premotor neurons mediating fever and other
   thermoregulatory functions — VGLUT3+ raphe neurons activated by cold
   exposure and central PGE2; suppression abolishes sympathetic BAT
   thermogenesis — [Nakamura et al. 2004, J Neurosci 24:5370-5380,
    "Identification of Sympathetic Premotor Neurons in Medullary Raphe
    Regions Mediating Fever and Other Thermoregulatory Functions"
    PMC6729310]
2. rRPa neurons with slowly conducting spinal axons are putative
   sympathetic premotor neurons for BAT — directly activated by skin
   cooling — [Morrison 2007, FASEB J 21:A472, "Skin cooling-evoked
   responses of rostral raphe pallidus neurons with slowly conducting
   spinal axons"]
3. Orexinergic projection from perifornical hypothalamus to RPa
   increases rat BAT thermogenesis — orexin drives thermogenic state —
   [Tupone Madden Cano Morrison 2011, J Neurosci 31:15944-15955,
    PMC3607627]
4. Central efferent pathways for cold-defensive and febrile shivering
   converge on RPa → spinal somatic + sympathetic outflow — [Nakamura
    Morrison 2011, J Physiol 589:3641-3658, PMC3167123]
5. Reviewed in central control of BAT thermogenesis — DMH and rRPa are
   the two principal premotor populations for cold defense — [reviewed
    Frontiers Endocrinol 2012 doi:10.3389/fendo.2012.00005, "Central
    Control of Brown Adipose Tissue Thermogenesis" PMC3292175]

INPUTS (from prior_results)
============================
- ThermoregulationCore.thermal_drive
- ThermoregulationCore.core_temp_proxy
- DorsomedialHypothalamus.bat_thermogenesis_drive
- DorsomedialHypothalamus.dmh_drive
- PreopticThermoregulator.bat_thermogenesis_brake
- PreopticThermoregulator.fever_signal_active
- OrexinWakePromoter.orexin_drive
- StressActivationAxis.stress_active

OUTPUTS (to brain_runner enrichment)
=====================================
- rpa_sympathetic_drive (0.0-1.0): rRPa premotor sympathetic output
- bat_thermogenesis_command (0.0-1.0): final BAT thermogenic drive
- cutaneous_vasoconstriction (0.0-1.0): skin vasoconstriction signal
- shivering_drive (0.0-1.0): somatic shivering recruitment
- fever_thermogenic_active (bool): febrile sympathetic engagement
- cold_defense_active (bool)
- rpa_state (str): "quiet" | "cold_defense" | "fever" | "stress_thermogenic"

brain_runner enrichment:
    rpa = all_results.get("MedullaryRaphePallidus", {})
    if rpa:
        enrichments["brain_rpa_sympathetic"] = rpa.get("rpa_sympathetic_drive", 0.2)
        enrichments["brain_bat_command"] = rpa.get("bat_thermogenesis_command", 0.0)
        enrichments["brain_shivering"] = rpa.get("shivering_drive", 0.0)
        enrichments["brain_rpa_state"] = rpa.get("rpa_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedullaryRaphePallidus(BrainMechanism):
    BASELINE_DRIVE = 0.20
    SHIVER_THRESHOLD = 0.55
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="MedullaryRaphePallidus",
            human_analog="Rostral raphe pallidus sympathetic premotor / BAT driver",
            layer="foundational",
        )
        self.state.setdefault("rpa_sympathetic_drive", self.BASELINE_DRIVE)
        self.state.setdefault("bat_thermogenesis_command", 0.0)
        self.state.setdefault("cutaneous_vasoconstriction", 0.0)
        self.state.setdefault("shivering_drive", 0.0)
        self.state.setdefault("fever_thermogenic_active", False)
        self.state.setdefault("cold_defense_active", False)
        self.state.setdefault("rpa_state", "quiet")
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _rpa_drive_target(self, dmh_drive: float, dmh_bat: float, mnpo_brake: float,
                          fever: bool, orexin: float, thermal_drive: float) -> float:
        """rRPa drive — DMH descends, MnPO inhibits, orexin augments
        (Tupone 2011), fever bypasses MnPO brake.
        """
        target = self.BASELINE_DRIVE
        target += dmh_drive * 0.4 + dmh_bat * 0.3
        # MnPO brake (warm defense)
        target -= mnpo_brake * 0.5
        if fever:
            # Fever overrides MnPO brake (PGE2 → MnPO inhibition releases RPa)
            target += 0.30
        # Cold drive — directly engages RPa
        if thermal_drive < -0.2:
            target += abs(thermal_drive) * 0.5
        # Orexin augmentation
        target += max(0.0, orexin - 0.4) * 0.2
        return max(0.0, min(1.0, target))

    def _bat_command(self, rpa: float, fever: bool, cold: bool) -> float:
        """Final BAT thermogenic command."""
        target = rpa * 0.85
        if fever:
            target = min(1.0, target + 0.15)
        if cold:
            target = min(1.0, target + 0.10)
        return max(0.0, min(1.0, target))

    def _vasoconstriction(self, rpa: float, thermal_drive: float) -> float:
        """Cutaneous vasoconstriction — engaged by RPa drive especially in cold."""
        target = rpa * 0.6
        if thermal_drive < -0.2:
            target += abs(thermal_drive) * 0.4
        return min(1.0, target)

    def _shivering_drive(self, rpa: float, thermal_drive: float) -> float:
        """Shivering — somatic motor output via raphe → spinal motor;
        engaged at high RPa drive with cold.
        """
        if thermal_drive >= 0.0:
            return 0.0
        if rpa < 0.35:
            return 0.0
        return min(1.0, (rpa - 0.35) * 1.3 + abs(thermal_drive) * 0.3)

    def _classify_state(self, rpa: float, fever: bool, cold: bool, dmh_stress: float) -> str:
        if fever:
            return "fever"
        if cold:
            return "cold_defense"
        if dmh_stress > 0.55 and rpa > 0.40:
            return "stress_thermogenic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        thermo = prior.get("ThermoregulationCore", {})
        thermal_drive = float(thermo.get("thermal_drive", 0.0))
        core_temp = float(thermo.get("core_temp_proxy", 0.5))

        dmh_data = prior.get("DorsomedialHypothalamus", {})
        dmh_drive = float(dmh_data.get("dmh_drive", 0.20))
        dmh_bat = float(dmh_data.get("bat_thermogenesis_drive", 0.0))

        poa = prior.get("PreopticThermoregulator", {})
        mnpo_brake = float(poa.get("bat_thermogenesis_brake", 0.5))
        fever = bool(poa.get("fever_signal_active", False))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        cold = thermal_drive < -0.2

        # --- rRPa drive ---
        rpa_target = self._rpa_drive_target(dmh_drive, dmh_bat, mnpo_brake,
                                             fever, orexin, thermal_drive)
        prev_rpa = float(self.state.get("rpa_sympathetic_drive", self.BASELINE_DRIVE))
        new_rpa = self._smooth(prev_rpa, rpa_target)

        # --- BAT command ---
        bat = self._bat_command(new_rpa, fever, cold)
        prev_bat = float(self.state.get("bat_thermogenesis_command", 0.0))
        new_bat = self._smooth(prev_bat, bat)

        # --- Cutaneous vasoconstriction ---
        vasocon = self._vasoconstriction(new_rpa, thermal_drive)

        # --- Shivering drive ---
        shiver = self._shivering_drive(new_rpa, thermal_drive)

        # --- Flags ---
        fever_active = fever and new_rpa > 0.35
        cold_active = cold and new_rpa > 0.35

        # --- State ---
        state = self._classify_state(new_rpa, fever_active, cold_active, dmh_drive)

        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_rpa, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["rpa_sympathetic_drive"] = round(new_rpa, 4)
        self.state["bat_thermogenesis_command"] = round(new_bat, 4)
        self.state["cutaneous_vasoconstriction"] = round(vasocon, 4)
        self.state["shivering_drive"] = round(shiver, 4)
        self.state["fever_thermogenic_active"] = fever_active
        self.state["cold_defense_active"] = cold_active
        self.state["rpa_state"] = state
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "rpa_sympathetic_drive": round(new_rpa, 4),
            "bat_thermogenesis_command": round(new_bat, 4),
            "cutaneous_vasoconstriction": round(vasocon, 4),
            "shivering_drive": round(shiver, 4),
            "fever_thermogenic_active": fever_active,
            "cold_defense_active": cold_active,
            "rpa_state": state,
        }
