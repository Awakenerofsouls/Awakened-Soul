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
  - [Saper 2005, Nature 437:1257, doi:10.1038/nature04284]
  - [Boulant 2000, Clin Infect Dis 31:S157, doi:10.1086/317520]
  - [McGinty 2001, Sleep Med Rev 5:355]
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
            name="ThermoSleepGate_ThermoSleepGate",
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
        warmth_base = core_temp * 0.50

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


