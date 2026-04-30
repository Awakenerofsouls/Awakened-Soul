"""
DorsalRapheSerotonin — Dorsal Raphe Nucleus 5-HT Mood-Wake-Patience System

NEURAL SUBSTRATE
================
The dorsal raphe nucleus (DRN) of the midbrain houses the largest single
collection of serotonergic neurons in the mammalian brain (~165,000 in
humans). DRN 5-HT neurons project diffusely to forebrain targets including
prefrontal cortex, amygdala, hippocampus, basal ganglia, and lateral
parabrachial nucleus, providing a tonic neuromodulatory influence on mood,
arousal, and time-to-reward decisions.

DRN 5-HT firing is heterogeneous but dominated by two patterns:
(1) classical broad-spike "clock-like" tonic discharge at 1–2 Hz,
state-modulated — high during waking, lower during NREM, lowest during REM;
(2) phasic responses to salient sensory stimuli, rhythmic motor outputs,
and waiting periods preceding reward delivery.

Multiple distinct subpopulations are now recognized:
 • Anxiolytic 5-HT subpopulation — projects to BLA and ventral hippocampus;
   chemogenetic activation reduces anxiety-related behavior, increases sleep
   secondarily through anxiolysis.
 • CO₂-arousal 5-HT subpopulation — projects to external lateral parabrachial
   nucleus (PBel); mediates arousal from sleep when blood CO₂ rises.
 • Reward-waiting subpopulation — sustains firing during delay periods;
   its activity correlates with the willingness to wait for delayed rewards.
 • Mood / valence-encoding subpopulation — feeds vmPFC and amygdala; chronic
   dysregulation is implicated in depression.

DRN 5-HT receives convergent excitatory drive from orexin (LHA), histamine
(TMN), and locus coeruleus norepinephrine — coupling 5-HT firing to broader
arousal state. It also receives inhibitory GABAergic input from VLPO during
sleep onset (the flip-flop mechanism).

KEY FINDINGS
============
1. DRN 5-HT neurons fire 1–2 Hz tonic clock-like during waking, decrease in
   NREM, near-silent in REM — state-modulated arousal coupling —
   [Mlinar Patti Bonsi 2016, Front Cell Neurosci 10:195,
    doi:10.3389/fncel.2016.00195]
2. Selective chemogenetic activation of DRN 5-HT neurons facilitates sleep
   through anxiolysis (BLA/vHPC projection) — [Cui et al. 2020, PMC7315407]
3. DRN 5-HT projection to external lateral parabrachial nucleus (PBel)
   mediates CO₂-induced arousal from sleep — [Smith et al. 2018, PMC5824737]
4. Sustained DRN 5-HT firing during reward delay periods underlies waiting
   for delayed rewards (patience) — [Miyazaki Miyazaki Doya 2018, PMC6623450]
5. DRN 5-HT neurons receive convergent excitatory drive from orexin,
   histamine, and noradrenaline — multi-arousal-system integration —
   [Brown et al. 2002, PubMed 12388591, J Neurochem]

INPUTS (from prior_results)
============================
- OrexinWakePromoter.orexin_drive
- HistamineArousalBooster.histamine_drive
- ArousalRegulator.tonic_level
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.vlpo_drive
- ValenceTagger.valence_polarity
- ValenceTagger.threat_signal
- VitalCoreRegulator.survival_threat_level
- AppetiteNPYBalancer.hunger_motivation (CO2 / metabolic proxy via para tone)

OUTPUTS (to brain_runner enrichment)
=====================================
- serotonin_drive (0.0-1.0): integrated 5-HT tonic firing proxy
- anxiolytic_subdrive (0.0-1.0): BLA/vHPC anxiolytic projection
- co2_arousal_drive (0.0-1.0): PBel projection magnitude
- waiting_capacity (0.0-1.0): sustained firing for delay tolerance
- mood_valence_encoding (signed -1..+1): mood baseline contribution
- depressive_drift (bool): chronic 5-HT depression pattern
- depressive_drift_ticks (int)

brain_runner enrichment block:
    drs = all_results.get("DorsalRapheSerotonin", {})
    if drs:
        enrichments["brain_serotonin_drive"] = drs.get("serotonin_drive", 0.5)
        enrichments["brain_anxiolytic_drive"] = drs.get("anxiolytic_subdrive", 0.5)
        enrichments["brain_co2_arousal"] = drs.get("co2_arousal_drive", 0.0)
        enrichments["brain_waiting_capacity"] = drs.get("waiting_capacity", 0.5)
        enrichments["brain_mood_valence"] = drs.get("mood_valence_encoding", 0.0)
        enrichments["brain_depressive_drift"] = drs.get("depressive_drift", False)
"""

from brain.base_mechanism import BrainMechanism


class DorsalRapheSerotonin(BrainMechanism):
    """
    DRN 5-HT system — heterogeneous subpopulation tracker.

    Computes integrated 5-HT tonic drive from multi-arousal-system convergence
    (Brown 2002), splits output into anxiolytic, CO2-arousal, waiting-capacity,
    and mood-encoding subdrives matching the genetically distinct DRN
    populations identified by Cui 2020, Smith 2018, and Miyazaki 2018.
    """

    BASELINE_TONIC = 0.50
    WAKE_MULTIPLIER = 1.0
    NREM_MULTIPLIER = 0.40
    REM_MULTIPLIER = 0.05
    SLEEP_TRANSITION_MULTIPLIER = 0.65

    OREXIN_GAIN = 0.20
    HISTAMINE_GAIN = 0.15
    NA_GAIN = 0.15
    VLPO_INHIBITION = 0.30

    DEPRESSIVE_DRIFT_THRESHOLD_TICKS = 80
    DEPRESSIVE_LOW_DRIVE_THRESHOLD = 0.30

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="DorsalRapheSerotonin",
            human_analog="Dorsal raphe nucleus serotonergic mood-wake system",
            layer="foundational",
        )
        self.state.setdefault("serotonin_drive", self.BASELINE_TONIC)
        self.state.setdefault("anxiolytic_subdrive", 0.5)
        self.state.setdefault("co2_arousal_drive", 0.0)
        self.state.setdefault("waiting_capacity", 0.5)
        self.state.setdefault("mood_valence_encoding", 0.0)
        self.state.setdefault("depressive_drift", False)
        self.state.setdefault("depressive_drift_ticks", 0)
        self.state.setdefault("low_drive_streak", 0)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _state_multiplier(self, sleep_state: str) -> float:
        """State-modulated firing per Mlinar 2016."""
        if sleep_state == "WAKE":
            return self.WAKE_MULTIPLIER
        if sleep_state == "SLEEP":
            return self.NREM_MULTIPLIER
        if sleep_state == "TRANSITION":
            return self.SLEEP_TRANSITION_MULTIPLIER
        return self.WAKE_MULTIPLIER

    def _convergent_arousal_drive(self, orexin: float, histamine: float, tonic_na: float) -> float:
        """Brown 2002 — orexin + histamine + NA convergent excitation of DRN."""
        excitation = (
            orexin * self.OREXIN_GAIN
            + histamine * self.HISTAMINE_GAIN
            + max(0.0, tonic_na - 0.5) * self.NA_GAIN
        )
        return excitation

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _classify_depressive(self, low_streak: int) -> bool:
        return low_streak > self.DEPRESSIVE_DRIFT_THRESHOLD_TICKS

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        hab = prior.get("HistamineArousalBooster", {})
        histamine = float(hab.get("histamine_drive", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic_na = float(arousal.get("tonic_level", 0.55))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        vlpo_drive = float(swff.get("vlpo_drive", 0.2))

        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))
        threat_signal = bool(valence.get("threat_signal", False))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        hunger_motivation = float(appetite.get("hunger_motivation", 0.5))

        # --- State multiplier (Mlinar 2016: clock-like state-modulated firing) ---
        state_mult = self._state_multiplier(sleep_state)

        # --- Convergent arousal-system excitation (Brown 2002) ---
        excitation = self._convergent_arousal_drive(orexin, histamine, tonic_na)

        # --- VLPO inhibitory input ---
        inhibition = vlpo_drive * self.VLPO_INHIBITION

        # --- Compute net tonic 5-HT drive ---
        target = self.BASELINE_TONIC * state_mult + excitation - inhibition
        target = max(0.05, min(0.98, target))

        prev = float(self.state.get("serotonin_drive", self.BASELINE_TONIC))
        new_drive = self._smooth(prev, target)

        # --- Anxiolytic subpopulation (Cui 2020 — BLA/vHPC projection) ---
        # Activates more strongly when threat is present and 5-HT drive is high
        # (the anxiolytic role is to reduce the impact of threat-coded valence)
        anxiolytic_target = new_drive * 0.7
        if threat_signal:
            anxiolytic_target += 0.15
        if valence_polarity < 0.4:
            anxiolytic_target += 0.10
        anxiolytic_target = max(0.05, min(0.95, anxiolytic_target))
        prev_anxio = float(self.state.get("anxiolytic_subdrive", 0.5))
        new_anxio = self._smooth(prev_anxio, anxiolytic_target)

        # --- CO2-arousal subpopulation (Smith 2018 — PBel projection) ---
        # Activates with rising metabolic demand / hypoxia proxy
        # We use survival_threat + hunger_motivation as a metabolic-distress proxy
        co2_proxy = max(0.0, (survival_threat * 0.5) + (hunger_motivation - 0.5) * 0.3)
        co2_target = co2_proxy
        if sleep_state in ("SLEEP", "TRANSITION") and co2_proxy > 0.3:
            # CO2 arousal effect strongest from sleep
            co2_target = min(1.0, co2_target * 1.5)
        prev_co2 = float(self.state.get("co2_arousal_drive", 0.0))
        new_co2 = self._smooth(prev_co2, co2_target)

        # --- Waiting capacity (Miyazaki 2018 — sustained firing during delays) ---
        # Driven by tonic 5-HT drive, attenuated by anxiety and high arousal
        waiting_target = new_drive * 0.8
        if threat_signal:
            waiting_target -= 0.20
        if tonic_na > 0.75:
            waiting_target -= 0.15
        waiting_target = max(0.0, min(1.0, waiting_target))
        prev_wait = float(self.state.get("waiting_capacity", 0.5))
        new_wait = self._smooth(prev_wait, waiting_target)

        # --- Mood-valence encoding (signed) ---
        # vmPFC/amygdala feed: + 5-HT correlates with positive baseline mood;
        # chronic depression of 5-HT correlates with depressed valence
        mood_target = (new_drive - 0.5) * 1.6  # range roughly -0.8..+0.8
        prev_mood = float(self.state.get("mood_valence_encoding", 0.0))
        new_mood = self._smooth(prev_mood, mood_target)

        # --- Depressive drift detection ---
        prev_streak = int(self.state.get("low_drive_streak", 0))
        if new_drive < self.DEPRESSIVE_LOW_DRIVE_THRESHOLD:
            low_streak = prev_streak + 1
        else:
            low_streak = max(0, prev_streak - 1)
        depressive_drift = self._classify_depressive(low_streak)

        # --- Track recent drive (for chronicity windows) ---
        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_drive, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        prev_drift_ticks = int(self.state.get("depressive_drift_ticks", 0))
        drift_ticks = prev_drift_ticks + 1 if depressive_drift else 0

        # --- Persist ---
        self.state["serotonin_drive"] = round(new_drive, 4)
        self.state["anxiolytic_subdrive"] = round(new_anxio, 4)
        self.state["co2_arousal_drive"] = round(new_co2, 4)
        self.state["waiting_capacity"] = round(new_wait, 4)
        self.state["mood_valence_encoding"] = round(new_mood, 4)
        self.state["depressive_drift"] = depressive_drift
        self.state["depressive_drift_ticks"] = drift_ticks
        self.state["low_drive_streak"] = low_streak
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "serotonin_drive": round(new_drive, 4),
            "anxiolytic_subdrive": round(new_anxio, 4),
            "co2_arousal_drive": round(new_co2, 4),
            "waiting_capacity": round(new_wait, 4),
            "mood_valence_encoding": round(new_mood, 4),
            "depressive_drift": depressive_drift,
            "depressive_drift_ticks": drift_ticks,
        }
