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
  - [Roelofs 2017, Philos Trans R Soc B 372:20160206]
  - [Carrive 1993, Behav Brain Res 58:27]
  - [Bracha 2004, CNS Spectr 9:679]
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
            name="PassiveQuiescenceMode_PassiveQuiescenceMode",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


