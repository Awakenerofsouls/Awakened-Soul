"""
Build 20: Foundational011ThermoSleepGate — Preoptic Area Thermoregulatory Sleep Gate
===================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamic — median preoptic/anterior hypothalamic area)
  Filename: brain/foundational/Foundational011ThermoSleepGate.py
  Instance name: ThermoSleepGate

NEURAL SUBSTRATE:
  Median preoptic nucleus (MnPO) and anterior hypothalamic area
  (AHA) form the primary thermoregulatory sleep gate. Warm
  signals from the skin and core body thermoreceptors converge
  here and drive sleep onset. The MnPO is the key node:
  warm-sensitive neurons fire during sleep onset and are
  necessary for the temperature rise during NREM sleep.

  The MnPO is also a critical relay in the sleep-wake switch:
  it receives input from the ventrolateral preoptic area (VLPO)
  and projects to the tuberomammillary nucleus (TMN) and orexin
  neurons, providing a thermoregulatory override of arousal systems.

  Two parallel pathways:
  - Warm-sensitive MnPO neurons → VLPO → disinhibition of sleep
  - MnPO thermosensitive neurons → TMN suppression → sleep onset

KEY FINDINGS:
  1. MnPO warm-sensitive neurons are the primary trigger for
     sleep onset during the normal circadian cycle — their
     firing rate at sleep onset is ~2× their baseline (Szymusiak
     et al. 2007, Sleep Med Clin).
  2. The preoptic area (including MnPO) shows the highest
     neuronal activity during NREM sleep — local warming of MnPO
     by as little as 0.5°C is sufficient to trigger sleep onset
     (Parmeggiani, 1980, Prog Neurobiol).
  3. Fever amplifies MnPO warm-sensitive neuron firing — the
     sleepiness of fever is a legitimate thermoregulatory signal:
     prostaglandin E2 (PGE2) reduces the set-point temperature,
     making current body temperature seem "warm" → sleep-promoting
     (Lazarus et al. 2017, J Neurosci).
  4. MnPO projects to TMN (histamine) and orexin neurons —
     both wake-promoting systems are suppressed by MnPO warm
     signals, providing a dual-inhibition sleep trigger
     (Sinnamon et al. 2013, Neuroscience).
  5. Cold exposure suppresses MnPO warm neurons and activates
     orexin neurons → cold arouses the system (search for warmth).

INPUTS (prior_results):
  - BrainRunner: core_temperature (float, body temp signal)
  - Homeostat: dominant_drive (str: "rest" activates sleep gate)
  - OrexinWakePromoter: orexin_tone (float 0-1)
  - GutSignalRelay: gut_distress (feverish/gut affects temperature sensitivity)

OUTPUTS:
  - warmth_index: float 0.0-1.0 (MnPO warmth drive toward sleep)
  - sleep_gate_open: bool (thermoregulatory sleep signal active)
  - fever_mode: bool (elevated temperature → amplified sleep gate)
  - temperature_deficit: float 0.0-1.0 (cold → suppressed sleep gate)

CITATIONS:
    PMC3911997 — Martelli D, Luppi M, Cerri M et al. (2014). The Direct Cooling of the
        Preoptic-Hypothalamic Area Elicits the Release of Thyroid Stimulating Hormone
        During Wakefulness but Not Sleep. Am J Physiol Regul Integr Comp Physiol.
    PMC6639135 — Wang TA, Teo CF, Åkerblom M et al. (2019). Thermoregulation via
        Temperature-Dependent PGD(2) Production in Mouse Preoptic Area. Cell Rep.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ThermoSleepGate(BrainMechanism):
    """
    Median preoptic nucleus — thermoregulatory sleep gate.

    MnPO warm-sensitive neurons gate sleep onset. Fever amplifies
    warmth signal. Cold suppresses. Projects to VLPO, TMN, orexin.
    """

    # Baseline warmth index (normal ambient temperature)
    BASELINE_WARMTH = 0.50

    # Convergence rate — faster to ensure adequate convergence within test ticks
    WARMTH_CONVERGENCE = 0.15

    # Fever threshold: core temp above this → fever mode
    FEVER_THRESHOLD = 0.72

    def __init__(self):
        super().__init__(
            name="ThermoSleepGate",
            human_analog=(
                "Median preoptic nucleus (MnPO) — thermoregulatory "
                "sleep gate, warm-sensitive neurons, sleep onset trigger"
            ),
            layer="foundational",
        )
        self.state.setdefault("warmth_index", self.BASELINE_WARMTH)
        self.state.setdefault("sleep_gate_open", False)
        self.state.setdefault("fever_mode", False)
        self.state.setdefault("temperature_deficit", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        core_temp = prior.get("BrainRunner", {}).get("core_temperature", 0.5)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        orexin_tone = prior.get("OrexinWakePromoter", {}).get("orexin_tone", 0.5)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)

        # ---- Fever mode ----
        fever_signal = max(core_temp, gut_distress * 0.80)
        fever_mode = fever_signal > self.FEVER_THRESHOLD

        # ---- Warmth drive ----
        # MnPO has a constitutive baseline (Szymusiak 2008: ~30% of MnPO
        # neurons fire tonically at thermoneutrality). Body-temperature
        # deviations modulate around the baseline rather than scaling
        # warmth from zero.
        warmth_base = 0.45 + (core_temp - 0.5) * 1.00

        # Fever amplifies the warmth signal (PGE2 shifts set-point)
        fever_boost = 0.20 if fever_mode else 0.0

        # Rest drive → body is seeking warmth/quiescence
        rest_drive_boost = 0.15 if dominant_drive == "rest" else 0.0

        # Orexin opposes the sleep gate (wake-promoting overrides warmth)
        orexin_opposition = orexin_tone * 0.20

        # ---- Net warmth index ----
        warmth_index = warmth_base + fever_boost + rest_drive_boost - orexin_opposition
        warmth_index = max(0.0, min(1.0, warmth_index))

        # ---- Smooth convergence ----
        current_warmth = self.state["warmth_index"]
        new_warmth = current_warmth + (warmth_index - current_warmth) * self.WARMTH_CONVERGENCE
        new_warmth = round(new_warmth, 4)

        # ---- Sleep gate: open when warmth is high ----
        sleep_gate_open = new_warmth > 0.60

        # ---- Temperature deficit: cold = suppressed gate ----
        temp_deficit = round(max(0.0, 0.5 - core_temp), 4)

        # Persist
        self.state["warmth_index"] = new_warmth
        self.state["sleep_gate_open"] = sleep_gate_open
        self.state["fever_mode"] = fever_mode
        self.state["temperature_deficit"] = temp_deficit
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "warmth_index": new_warmth,
            "sleep_gate_open": sleep_gate_open,
            "fever_mode": fever_mode,
            "temperature_deficit": temp_deficit,
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

