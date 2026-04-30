"""
BasalForebrainGABA — Basal Forebrain GABAergic Wake-Promoting / Gamma Generator

NEURAL SUBSTRATE
================
The basal forebrain (BF) is a heterogeneous collection of cell groups
in the medial-ventral telencephalon including the medial septum (MS),
diagonal band of Broca (DBB), substantia innominata, magnocellular
preoptic, and nucleus basalis of Meynert. While the cholinergic Ch1-Ch4
populations of BF have been the historical focus (and Ch4 is covered
in NucleusBasalisAcetylcholine), more recent work has highlighted the
critical role of BF GABAergic neurons — particularly parvalbumin-
positive (PV+) and somatostatin-positive (SOM+) populations — in
controlling cortical activation, sleep-wake state, and arousal.

The Yang/Brown/McCarley taxonomy (2017) organizes BF cell types into
glutamatergic, cholinergic, GABAergic-PV+, and GABAergic-SOM+
populations with distinct projections and behavioral correlates. The
hierarchy of wake-promotion is glutamatergic → cholinergic → PV+ → cortex,
with all wake-promoters inhibited by sleep-promoting SOM+ neurons.
This sleep-promoting SOM+ population was identified by Xu et al.
(2015, Nat Neurosci) and provides a BF-internal sleep mechanism distinct
from VLPO/POA.

BF PV+ GABAergic neurons project to cortex and especially to cortical
PV+ interneurons. Optogenetic activation of BF-PV+ neurons preferentially
increases cortical gamma-band oscillations (~40 Hz) (Kim et al. 2015,
PNAS), the EEG signature of attentive wakefulness. BF-PV+ neurons fire
maximally during wake and REM and are silent during NREM, fitting the
gamma-state pattern. Hypercarbia and auditory stimuli arouse animals
from sleep by activating BF-PV+ neurons (Anaclet et al. 2020, eLife).

In Nova's substrate this provides the cortically-projecting GABAergic
wake/REM gamma driver — separate from cholinergic NBM. Pairs with TRN
to gate cortical gamma-state and supplements the wake-promotion of
orexin/histamine systems.

KEY FINDINGS
============
1. BF parvalbumin GABAergic neurons regulate cortical gamma-band
   oscillations — optogenetic stimulation preferentially increases
   ~40 Hz cortical gamma — [Kim Sirota Hangya 2015, PNAS 112:3535,
    "Cortically projecting basal forebrain parvalbumin neurons
    regulate cortical gamma band oscillations"]
2. BF circuit for sleep-wake control — distinct cell types differentially
   regulate sleep and wake; SOM+ promotes sleep, PV+ wake — [Xu et al.
    2015, Nat Neurosci 18:1641-1647, "Basal forebrain circuit for
    sleep-wake control" PMC5776144]
3. BF wake-promoting neurons hierarchically organized: glutamatergic
   → cholinergic → PV+ — all inhibited by SOM+ — [reviewed Yang Brown
    McCarley 2017, Curr Top Behav Neurosci PMC5525536]
4. BF PV+ neurons mediate arousals from sleep induced by hypercarbia
   or auditory stimuli — [Anaclet et al. 2020, eLife/Nat Comm
    PMC7757019]
5. BF cholinergic neurons promote wakefulness by actions on neighboring
   non-cholinergic neurons — opto-dialysis evidence for intra-BF
   wake circuit — [Zant et al. 2016, J Neurosci 36:2057-2067]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.rem_pattern_active
- OrexinWakePromoter.orexin_drive
- HistamineArousalBooster.histamine_drive
- NucleusBasalisAcetylcholine.cortical_ach_release
- ThalamicReticularNucleus.attention_gating_strength
- CarotidBodyChemosensor.hypercapnia_response

OUTPUTS (to brain_runner enrichment)
=====================================
- bf_pv_drive (0.0-1.0): PV+ wake-promoting output
- bf_som_drive (0.0-1.0): SOM+ sleep-promoting output
- cortical_gamma_drive (0.0-1.0): predicted cortical gamma power
- arousal_recruitment (0.0-1.0): BF→cortex wake support
- sleep_promoting_active (bool): SOM+ in dominant state
- bf_state (str): "wake_gamma" | "rem_gamma" | "nrem_quiet" | "transition"

brain_runner enrichment:
    bf = all_results.get("BasalForebrainGABA", {})
    if bf:
        enrichments["brain_bf_pv"] = bf.get("bf_pv_drive", 0.4)
        enrichments["brain_bf_som"] = bf.get("bf_som_drive", 0.2)
        enrichments["brain_cortical_gamma"] = bf.get("cortical_gamma_drive", 0.3)
        enrichments["brain_bf_state"] = bf.get("bf_state", "wake_gamma")
"""

from brain.base_mechanism import BrainMechanism


class BasalForebrainGABA(BrainMechanism):
    BASELINE_PV = 0.40
    BASELINE_SOM = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="BasalForebrainGABA",
            human_analog="Basal forebrain GABAergic (PV+ wake / SOM+ sleep)",
            layer="foundational",
        )
        self.state.setdefault("bf_pv_drive", self.BASELINE_PV)
        self.state.setdefault("bf_som_drive", self.BASELINE_SOM)
        self.state.setdefault("cortical_gamma_drive", 0.30)
        self.state.setdefault("arousal_recruitment", 0.30)
        self.state.setdefault("sleep_promoting_active", False)
        self.state.setdefault("bf_state", "wake_gamma")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _pv_target(self, sleep_state: str, rem: bool, arousal: float,
                    orexin: float, histamine: float, hypercapnia: float) -> float:
        """BF PV+ wake/REM-promoting drive.
        Active during wake and REM, silent during NREM.
        """
        if sleep_state == "SLEEP" and not rem:
            return 0.05  # NREM — silent
        if rem:
            return min(1.0, 0.65 + arousal * 0.2)
        # Wake
        target = self.BASELINE_PV
        target += max(0.0, arousal - 0.5) * 0.4
        target += orexin * 0.2
        target += max(0.0, histamine - 0.5) * 0.2
        # Hypercapnia / arousal stimuli (Anaclet 2020)
        target += hypercapnia * 0.20
        return min(1.0, target)

    def _som_target(self, sleep_state: str, sleep_pressure: float, arousal: float) -> float:
        """BF SOM+ sleep-promoting drive (Xu 2015).
        Engaged during sleep transitions and high sleep pressure.
        """
        if sleep_state == "SLEEP":
            return 0.65
        if sleep_state == "TRANSITION":
            return 0.45
        # Wake — engaged when arousal low and sleep pressure rising
        if arousal < 0.40:
            return self.BASELINE_SOM + (0.4 - arousal) * 0.5
        return self.BASELINE_SOM

    def _cortical_gamma(self, pv: float, som: float, ach: float, attention: float) -> float:
        """Cortical gamma drive — Kim 2015 BF-PV+ → cortical gamma."""
        target = pv * 0.6 + ach * 0.2 + attention * 0.2 - som * 0.3
        return max(0.0, min(1.0, target))

    def _arousal_recruitment(self, pv: float, gamma: float) -> float:
        """BF → cortex wake support."""
        return min(1.0, pv * 0.7 + gamma * 0.3)

    def _classify_state(self, sleep_state: str, rem: bool, pv: float, som: float) -> str:
        if rem and pv > 0.50:
            return "rem_gamma"
        if sleep_state == "SLEEP" and not rem:
            return "nrem_quiet"
        if sleep_state == "TRANSITION":
            return "transition"
        if pv > som:
            return "wake_gamma"
        return "transition"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        rem = bool(swff.get("rem_pattern_active", False))
        sleep_pressure = float(swff.get("sleep_pressure", 0.0))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        hist_data = prior.get("HistamineArousalBooster", {})
        histamine = float(hist_data.get("histamine_drive", 0.5))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        trn = prior.get("ThalamicReticularNucleus", {})
        attention = float(trn.get("attention_gating_strength", 0.40))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))

        # --- PV+ drive ---
        pv_target = self._pv_target(sleep_state, rem, tonic, orexin, histamine, hypercapnia)
        if phasic:
            pv_target = min(1.0, pv_target + 0.10)
        prev_pv = float(self.state.get("bf_pv_drive", self.BASELINE_PV))
        new_pv = self._smooth(prev_pv, pv_target)

        # --- SOM+ drive ---
        som_target = self._som_target(sleep_state, sleep_pressure, tonic)
        prev_som = float(self.state.get("bf_som_drive", self.BASELINE_SOM))
        new_som = self._smooth(prev_som, som_target)

        # --- Cortical gamma ---
        gamma = self._cortical_gamma(new_pv, new_som, ach, attention)
        prev_gamma = float(self.state.get("cortical_gamma_drive", 0.30))
        new_gamma = self._smooth(prev_gamma, gamma)

        # --- Arousal recruitment ---
        arousal_rec = self._arousal_recruitment(new_pv, new_gamma)

        # --- Sleep-promoting flag ---
        sleep_promoting = new_som > new_pv and new_som > 0.40

        # --- State ---
        state = self._classify_state(sleep_state, rem, new_pv, new_som)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["bf_pv_drive"] = round(new_pv, 4)
        self.state["bf_som_drive"] = round(new_som, 4)
        self.state["cortical_gamma_drive"] = round(new_gamma, 4)
        self.state["arousal_recruitment"] = round(arousal_rec, 4)
        self.state["sleep_promoting_active"] = sleep_promoting
        self.state["bf_state"] = state
        self.state["wake_promotion"] = (state in ("WakeActive", "GammaBurst"))
        self.state["gamma_drive_ema"] = round(new_gamma * 0.2 + float(self.state.get("gamma_drive_ema", new_gamma)) * 0.8, 4)
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "bf_pv_drive": round(new_pv, 4),
            "bf_som_drive": round(new_som, 4),
            "cortical_gamma_drive": round(new_gamma, 4),
            "arousal_recruitment": round(arousal_rec, 4),
            "sleep_promoting_active": sleep_promoting,
            "bf_state": state,
            "wake_promotion": (state in ("WakeActive", "GammaBurst")),
        }
