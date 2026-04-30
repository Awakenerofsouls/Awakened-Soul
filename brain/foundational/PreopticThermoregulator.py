"""
PreopticThermoregulator — POA/MnPO Thermoregulation, Sleep, Fever Hub

NEURAL SUBSTRATE
================
The preoptic area (POA) of the anterior hypothalamus, especially the
median preoptic nucleus (MnPO) and ventrolateral preoptic area (VLPO),
is the master thermoregulatory and sleep-promoting hub of the mammalian
brain. The MnPO contains genetically distinct populations of warm-sensitive
neurons expressing PACAP, BDNF, QRFP, and the prostaglandin EP3 receptor
(EP3R), with co-expressed receptors for temperature, leptin, estrogen,
and PGE2. These warm-sensitive neurons are the principal cellular substrate
for body temperature regulation and the febrile response.

MnPO warm-sensitive neurons fire when core body temperature rises and
project to medullary raphe sympathetic premotor neurons (raphe pallidus,
RPa) and to the dorsomedial hypothalamus (DMH). When ambient or core
temperature rises, MnPO firing increases, inhibiting RPa/DMH, suppressing
sympathetic BAT thermogenesis, and promoting heat loss via cutaneous
vasodilation. When temperature falls, MnPO firing falls, releasing RPa
and DMH from inhibition and engaging cold-defense (BAT thermogenesis,
shivering, cutaneous vasoconstriction).

PGE2-mediated fever signaling acts on EP3R-expressing MnPO neurons:
PGE2 binding inhibits these neurons, releasing thermogenesis and producing
the febrile temperature rise. Recent work (Nature 2025) identified preoptic
EP3R neurons as a "two-way switch" between fever and torpor.

The POA is also a sleep-promoting hub. VLPO galanin/GABA neurons promote
NREM sleep by inhibiting wake-promoting nuclei (TMN, LC, raphe, orexin),
and a subset of warm-sensitive MnPO neurons (nitrergic/glutamatergic)
promote both sleep and hypothermia, demonstrating partial overlap of
sleep and thermoregulation circuits in the preoptic area.

In Nova's substrate this provides the unified preoptic thermoregulator
and sleep-promoter — sets thermoregulatory tone, supports VLPO sleep
push, and routes fever signal via EP3R when PGE2 is present.

KEY FINDINGS
============
1. MnPO contains warm-responsive neurons expressing peptides (PACAP,
   BDNF, QRFP) and receptors (temperature, leptin, estrogen, PGE2)
   that regulate body temperature — [Tan Knight 2018, Cell 174:1080,
    "Warm-Sensitive Neurons that Control Body Temperature";
    reviewed PMC9154766]
2. PGE2 binding to EP3 receptors on MnPO neurons inhibits these neurons,
   releasing thermogenesis and producing fever — [Nakamura et al. 2002,
    Eur J Neurosci 15:1849, "Different Populations of Prostaglandin EP3
    Receptor-Expressing Preoptic Neurons" PMC2857774]
3. Preoptic EP3R neurons constitute a two-way switch for fever and
   torpor — bidirectional thermoregulatory state control — [Nature 2025
    doi:10.1038/s41586-025-09056-1, "Preoptic EP3R neurons constitute
    a two-way switch for fever and torpor"]
4. Median preoptic area neurons are required for cooling- and febrile-
   activations of BAT thermogenesis — both cold-defense and fever go
   through MnPO → RPa — [Nakamura et al. 2020, Sci Rep 10:17655,
    PubMed 33093475]
5. POA contains overlapping circuits for sleep and thermoregulation —
   warm-tagged MnPO neurons reactivated promote sleep with hypothermia —
   [Harding et al. 2018; reviewed Frontiers Neurosci 2021
    doi:10.3389/fnins.2021.664781, PMC8280336]

INPUTS (from prior_results)
============================
- ThermoregulationCore.thermal_drive
- ThermoregulationCore.core_temp_proxy
- StressActivationAxis.cortisol_level
- AreaPostremaToxinGuard.aversive_interoceptive_signal (proxy for inflammation/PGE2)
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.sleep_pressure
- ArousalRegulator.tonic_level
- HistamineArousalBooster.histamine_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- mnpo_warm_sensitive_drive (0.0-1.0): warm-responsive firing
- vlpo_sleep_drive (0.0-1.0): VLPO sleep-promoting GABA output
- ep3r_inhibition (0.0-1.0): PGE2-mediated suppression of MnPO
- thermoregulatory_tone (signed -1..+1): + = heat-loss/sleep, - = cold-defense
- fever_signal_active (bool)
- bat_thermogenesis_brake (0.0-1.0): MnPO → RPa inhibition strength
- preoptic_state (str): "warm_sensing" | "cold_defense" | "fever" | "sleep_promoting"

brain_runner enrichment:
    poa = all_results.get("PreopticThermoregulator", {})
    if poa:
        enrichments["brain_mnpo_warm"] = poa.get("mnpo_warm_sensitive_drive", 0.5)
        enrichments["brain_vlpo_sleep"] = poa.get("vlpo_sleep_drive", 0.0)
        enrichments["brain_thermo_tone"] = poa.get("thermoregulatory_tone", 0.0)
        enrichments["brain_preoptic_state"] = poa.get("preoptic_state", "warm_sensing")
"""

from brain.base_mechanism import BrainMechanism


class PreopticThermoregulator(BrainMechanism):
    BASELINE_MNPO = 0.50
    BASELINE_VLPO = 0.20
    PGE2_THRESHOLD = 0.50
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="PreopticThermoregulator",
            human_analog="Preoptic area thermoregulator (MnPO + VLPO)",
            layer="foundational",
        )
        self.state.setdefault("mnpo_warm_sensitive_drive", self.BASELINE_MNPO)
        self.state.setdefault("vlpo_sleep_drive", self.BASELINE_VLPO)
        self.state.setdefault("ep3r_inhibition", 0.0)
        self.state.setdefault("thermoregulatory_tone", 0.0)
        self.state.setdefault("fever_signal_active", False)
        self.state.setdefault("bat_thermogenesis_brake", 0.5)
        self.state.setdefault("preoptic_state", "warm_sensing")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _mnpo_warm_target(self, thermal_drive: float, core_temp: float, ep3r_inh: float) -> float:
        """MnPO warm-sensitive neurons — fire when temp rises.
        Inhibited by PGE2 (EP3R) → fever release.
        """
        # thermal_drive > 0 = too warm; raises MnPO firing
        target = self.BASELINE_MNPO + thermal_drive * 0.3
        target += (core_temp - 0.5) * 0.4
        # PGE2 / EP3R inhibition reduces MnPO firing
        target -= ep3r_inh * 0.6
        return max(0.05, min(1.0, target))

    def _vlpo_sleep_target(self, sleep_pressure: float, sleep_state: str,
                           histamine: float, mnpo_warm: float) -> float:
        """VLPO sleep-promoting GABAergic neurons — engaged by sleep pressure
        and reduced by wake-promoting histamine (mutual inhibition).
        Warm-sensitive MnPO subset also promotes sleep (Harding 2018 overlap).
        """
        target = self.BASELINE_VLPO
        if sleep_state == "SLEEP":
            target = 0.70
        elif sleep_state == "TRANSITION":
            target = 0.45
        target += sleep_pressure * 0.3
        target -= max(0.0, histamine - 0.5) * 0.4  # histamine suppresses VLPO
        target += max(0.0, mnpo_warm - 0.65) * 0.2  # warm overlap with sleep
        return max(0.0, min(1.0, target))

    def _ep3r_inhibition_target(self, aversive_signal: float, cortisol: float) -> float:
        """PGE2-driven EP3R inhibition of MnPO. Aversive interoceptive signal
        is proxy for systemic inflammation / IL-1 → PGE2.
        """
        if aversive_signal < 0.30:
            return 0.0
        target = (aversive_signal - 0.30) * 1.2
        if cortisol > 0.65:
            target *= 0.7  # cortisol attenuates inflammatory drive
        return min(1.0, target)

    def _thermoregulatory_tone(self, mnpo: float, ep3r: float) -> float:
        """+ tone = heat-loss / sleep promotion; - tone = cold-defense."""
        # Warm-sensing MnPO fires → cooling tone
        return max(-1.0, min(1.0, (mnpo - 0.5) * 1.5 - ep3r * 0.5))

    def _bat_brake(self, mnpo: float) -> float:
        """MnPO → RPa BAT thermogenesis inhibition strength."""
        return max(0.0, min(1.0, mnpo))

    def _classify_state(self, mnpo: float, vlpo: float, ep3r: float, fever: bool) -> str:
        if fever:
            return "fever"
        if vlpo > 0.55:
            return "sleep_promoting"
        if mnpo < 0.30:
            return "cold_defense"
        return "warm_sensing"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        thermo = prior.get("ThermoregulationCore", {})
        thermal_drive = float(thermo.get("thermal_drive", 0.0))
        core_temp = float(thermo.get("core_temp_proxy", 0.5))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        ap = prior.get("AreaPostremaToxinGuard", {})
        aversive = float(ap.get("aversive_interoceptive_signal", 0.0))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        sleep_pressure = float(swff.get("sleep_pressure", 0.0))

        hist_data = prior.get("HistamineArousalBooster", {})
        histamine = float(hist_data.get("histamine_drive", 0.5))

        # --- EP3R inhibition (PGE2 proxy) ---
        ep3r_target = self._ep3r_inhibition_target(aversive, cortisol)
        prev_ep3r = float(self.state.get("ep3r_inhibition", 0.0))
        new_ep3r = self._smooth(prev_ep3r, ep3r_target)

        # --- MnPO warm-sensitive ---
        mnpo_target = self._mnpo_warm_target(thermal_drive, core_temp, new_ep3r)
        prev_mnpo = float(self.state.get("mnpo_warm_sensitive_drive", self.BASELINE_MNPO))
        new_mnpo = self._smooth(prev_mnpo, mnpo_target)

        # --- VLPO sleep ---
        vlpo_target = self._vlpo_sleep_target(sleep_pressure, sleep_state, histamine, new_mnpo)
        prev_vlpo = float(self.state.get("vlpo_sleep_drive", self.BASELINE_VLPO))
        new_vlpo = self._smooth(prev_vlpo, vlpo_target)

        # --- Thermoregulatory tone ---
        tone = self._thermoregulatory_tone(new_mnpo, new_ep3r)

        # --- BAT brake ---
        bat_brake = self._bat_brake(new_mnpo)

        # --- Fever ---
        fever = new_ep3r > self.PGE2_THRESHOLD

        # --- State ---
        state = self._classify_state(new_mnpo, new_vlpo, new_ep3r, fever)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mnpo_warm_sensitive_drive"] = round(new_mnpo, 4)
        self.state["vlpo_sleep_drive"] = round(new_vlpo, 4)
        self.state["ep3r_inhibition"] = round(new_ep3r, 4)
        self.state["thermoregulatory_tone"] = round(tone, 4)
        self.state["fever_signal_active"] = fever
        self.state["bat_thermogenesis_brake"] = round(bat_brake, 4)
        self.state["preoptic_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mnpo_warm_sensitive_drive": round(new_mnpo, 4),
            "vlpo_sleep_drive": round(new_vlpo, 4),
            "ep3r_inhibition": round(new_ep3r, 4),
            "thermoregulatory_tone": round(tone, 4),
            "fever_signal_active": fever,
            "bat_thermogenesis_brake": round(bat_brake, 4),
            "preoptic_state": state,
        }
