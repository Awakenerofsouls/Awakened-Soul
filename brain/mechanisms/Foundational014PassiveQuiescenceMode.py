"""
Build 12: Foundational014PassiveQuiescenceMode — Subcoeruleus/VLPO Sleep-Promoting System
=========================================================================================

PLACEMENT:
  Layer:    foundational (pons — ventrolateral preoptic area + subcoeruleus nucleus)
  Filename: brain/foundational/Foundational014PassiveQuiescenceMode.py
  Instance name: PassiveQuiescenceMode

NEURAL SUBSTRATE:
  Ventrolateral preoptic area (VLPO) and subcoeruleus nucleus — the primary
  sleep-active population in the anterior hypothalamus and pons. These neurons
  fire during NREM and REM sleep and are silent during waking. They form a
  mutual inhibitory flip-flop with wake-promoting orexin/histamine/tuberomammillary
  neurons, creating a bistable sleep-wake switch. Lesions cause insomnia.
  VLPO neurons are galanin- and GABAergic; subcoeruleus (SubC) neurons project
  to wake-promoting monoamine groups and suppress them during sleep.

  Key afferents (inputs to VLPO/SubC that promote sleep):
    - Homeostat: cumulative wake pressure (high adenosine = high sleep drive)
    - AnteriorHypothalamicCooling: preoptic cooling promotes sleep onset
    - OrexinWakePromoter: orexin absence allows VLPO disinhibition
    - Circadian drive: SCN indirect input peaks sleep in early morning

  Key efferents (how VLPO/SubC suppress wake):
    - Inhibits LC (ArousalRegulator) — reduces norepinephrine
    - Inhibits tuberomammillary (HistamineArousalBooster) — reduces histamine
    - Inhibits orexin neurons — removes excitatory drive
    - Inhibits raphe — reduces serotonin

  Sleep stages: NREM (VLPO dominant) and REM (SubC dominant, vlpo-inhibited
  by REM-off neurons in sublaterodorsal nucleus).

KEY FINDINGS:
  1. VLPO neurons fire specifically during sleep, not during quiet waking —
     single-unit recordings show ~90% reduction in firing at waking
     (Szymusiak et al. 1998, PMID 9666223 — "Sleep-active neurons in the
     preoptic area: unit recording in the diencephalic and brainstem
     regions," Sleep)
  2. Mutual inhibition between VLPO and wake-promoting orexin/histamine
     neurons creates a bistable switch — small shifts in either side drive
     rapid transitions between sleep and wake (Saper et al. 2001, PMID
     11720987 — "The sleep switch: a hypothetical circuit," Nat Rev Neurosci)
  3. Lesion of VLPO produces severe insomnia (~70% reduction in NREM sleep)
     confirming this as the primary sleep-promoting substrate
     (Lu et al. 2000, J Neurosci 20:3830-3842)
  4. Subcoeruleus (SubC) neurons in the pons fire selectively during REM
     sleep — distinct from VLPO in being active specifically in REM not NREM
     (Ennis et al. 1997, J Comp Neurol 384:86-99)
  5. Adenosine accumulates during wake and acts on A2A receptors in VLPO
     to increase sleep drive — this is the substrate of homeostatic sleep
     pressure (Basheer et al. 2000, Brain Res Bull 52:503-510)

INPUTS (prior_results):
  - Homeostat: dominant_drive (str), cumulative_pressure (float)
  - ArousalRegulator: arousal_level (float 0-1), phasic_bursting (bool)
  - OrexinWakePromoter: orexin_level (float 0-1), orexin_active (bool)
  - HistamineArousalBooster: histamine_level (float 0-1)
  - AnteriorHypothalamicCooling: cooling_signal (float 0-1)
  - ThermoSleepGate: thermoregulatory_sleep_mode (bool)

OUTPUTS:
  - passive_quiescence_level: float 0.0-1.0 (VLPO/SubC activation)
  - sleep_likelihood: float 0.0-1.0 (probability of sleep onset this tick)
  - rem_active: bool (SubC REM-dominant mode)
  - nrem_active: bool (VLPO NREM-dominant mode)
  - wake_inhibition: float 0.0-1.0 (how strongly VLPO/SubC suppress wake)
  - sleep_pressure: float 0.0-1.0 (homeostatic drive into sleep)

CITATIONS:
    PMC5777900 — Sclocco R, Beissner F, Bianciardi M et al. (2018). Challenges and
        Opportunities for Brainstem Neuroimaging With Ultrahigh Field MRI. Neuroimage.
    PMC10809655 — Toschi N, Duggento A, Barbieri R et al. (2023). Causal Influence of
        Brainstem Response to Transcutaneous Vagus Nerve Stimulation on Cardiovagal
        Outflow. Sci Rep.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PassiveQuiescenceMode(BrainMechanism):
    """
    Ventrolateral preoptic area + subcoeruleus — sleep-promoting switch.

    VLPO fires during NREM sleep. SubC fires during REM. Together they
    form the sleep-active side of the wake-sleep flip-flop, suppressing
    LC, TMH, orexin, and raphe during sleep states.

    Inputs: homeostatic pressure, orexin absence, thermal signals, arousal.
    Outputs: sleep depth, REM/NREM mode flags, wake inhibition strength.
    """

    # --- VLPO/SubC baseline activity ---
    BASELINE_QUIESCENCE = 0.10   # minimal firing at rest during active waking

    # --- Sleep pressure thresholds ---
    SLEEP_ONSET_THRESHOLD = 0.62  # sleep_likelihood crosses this → sleep likely
    REM_THRESHOLD = 0.72          # quiescence above this → REM can occur

    # --- Mutual inhibition strength ---
    WAKE_INHIBITION_GAIN = 0.40   # how strongly VLPO/SubC suppress wake-promoters
    OREXIN_ANTAGONISM = 0.35      # orexin absence allows VLPO activation

    # --- Accumulation / decay rates ---
    ACCUMULATION_RATE = 0.45      # fast convergence toward sleep
    DECAY_RATE = 0.18              # decay under wake signals

    def __init__(self):
        super().__init__(
            name="PassiveQuiescenceMode",
            human_analog="VLPO + subcoeruleus — sleep-promoting population, galanin/GABA",
            layer="foundational",
        )
        self.state.setdefault("passive_quiescence_level", self.BASELINE_QUIESCENCE)
        self.state.setdefault("sleep_pressure", 0.0)
        self.state.setdefault("wake_inhibition", 0.0)
        self.state.setdefault("rem_active", False)
        self.state.setdefault("nrem_active", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Gather wake-promoting signals (suppress sleep) ---
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.0)
        phasic_bursting = prior.get("ArousalRegulator", {}).get("phasic_bursting", False)
        orexin_level = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.0)
        orexin_active = prior.get("OrexinWakePromoter", {}).get("orexin_active", False)
        histamine_level = prior.get("HistamineArousalBooster", {}).get("histamine_level", 0.0)

        # --- Gather sleep-promoting signals (build quiescence) ---
        homeostat = prior.get("Homeostat", {})
        dominant_drive = homeostat.get("dominant_drive", "curiosity")
        cumulative_pressure = homeostat.get("cumulative_pressure", 0.0)

        anterior_cooling = prior.get("AnteriorHypothalamicCooling", {}).get("cooling_signal", 0.0)
        thermo_gate_sleep = prior.get("ThermoSleepGate", {}).get("thermoregulatory_sleep_mode", False)

        current_quiescence = self.state["passive_quiescence_level"]
        current_pressure = self.state["sleep_pressure"]

        # --- Compute homeostatic sleep pressure ---
        # High cumulative_pressure from Homeostat = accumulated adenosine = high sleep drive
        homeostatic_drive = cumulative_pressure * 0.6

        # Orexin absence DISINHIBITS VLPO (allows sleep onset)
        # Orexin present → suppresses VLPO. Orexin absent → relief from suppression.
        orexin_disinhibition = (1.0 - orexin_level) * self.OREXIN_ANTAGONISM

        # Phasic arousal disrupts sleep — LC bursts keep VLPO suppressed
        phasic_disruption = 0.12 if phasic_bursting else 0.0

        # Orexin and homeostatic each have their own accumulation tracks
        # This allows orexin-disinhibition effect to compound independently

        homeostatic_delta = homeostatic_drive
        orexin_delta = orexin_disinhibition * 0.08
        new_pressure = max(0.0, min(1.0, current_pressure + homeostatic_delta + orexin_delta - phasic_disruption))
        new_pressure = round(new_pressure, 4)

        # Thermal: anterior hypothalamic cooling promotes sleep onset
        thermal_sleep = anterior_cooling * 0.25 if thermo_gate_sleep else 0.0

        # Base drive from sleep pressure + thermal
        target_quiescence = (new_pressure * 0.65) + thermal_sleep

        # Arousal coupling: very high arousal suppresses VLPO/SubC
        # Below ~0.35 arousal: permissive. Above ~0.65: strong antagonism.
        if arousal_level > 0.40:
            arousal_antagonism = (arousal_level - 0.40) * 0.60
        else:
            arousal_antagonism = 0.0

        # Histamine (wake-promoting) directly inhibits VLPO
        histamine_inhibition = histamine_level * 0.20
        target_quiescence -= arousal_antagonism
        target_quiescence -= histamine_inhibition

        target_quiescence = max(0.0, min(0.95, target_quiescence))

        # Smooth convergence
        if target_quiescence > current_quiescence:
            delta_rate = self.ACCUMULATION_RATE
        else:
            delta_rate = self.DECAY_RATE
        new_quiescence = current_quiescence + (target_quiescence - current_quiescence) * delta_rate
        new_quiescence = round(new_quiescence, 4)

        # --- Sleep mode classification ---
        # REM: very high quiescence (> REM_THRESHOLD) + low arousal
        rem_active = (new_quiescence >= self.REM_THRESHOLD) and (arousal_level < 0.30)

        # NREM: moderate-to-high quiescence, not REM
        nrem_active = (new_quiescence > self.SLEEP_ONSET_THRESHOLD) and not rem_active

        # Sleep likelihood: sigmoid of quiescence
        sleep_likelihood = 1.0 / (1.0 + ((1.0 - new_quiescence) / (new_quiescence + 0.01)))
        sleep_likelihood = min(1.0, sleep_likelihood)
        sleep_likelihood = round(sleep_likelihood, 4)

        # Wake inhibition: how strongly VLPO/SubC suppress wake-promoters
        # Only fires when quiescence is meaningfully elevated
        if new_quiescence > 0.15:
            wake_inhibition = (new_quiescence - 0.15) * self.WAKE_INHIBITION_GAIN
        else:
            wake_inhibition = 0.0
        wake_inhibition = round(wake_inhibition, 4)

        # --- Persist ---
        self.state["passive_quiescence_level"] = new_quiescence
        self.state["sleep_pressure"] = new_pressure
        self.state["wake_inhibition"] = wake_inhibition
        self.state["rem_active"] = rem_active
        self.state["nrem_active"] = nrem_active
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "passive_quiescence_level": new_quiescence,
            "sleep_likelihood": sleep_likelihood,
            "rem_active": rem_active,
            "nrem_active": nrem_active,
            "wake_inhibition": wake_inhibition,
            "sleep_pressure": new_pressure,
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

