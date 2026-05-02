"""
Subcortical020ThalamicCentromedianIntralaminar.py — Wire 20: CMIntralaminarArousal

Centromedian (CM) and parafascicular (Pf) intralaminar nuclei —
intralaminar thalamic arousal and pain relay.

Neural analog: CM and Pf constitute the intralaminar nuclear complex of the
thalamus. Together with the centre median (CM), they form the main arousal-
generating matrix thalamic system. They receive input from the brainstem
reticular formation (ascending reticular activating system), the spinal cord
(pain), and the basal ganglia, and project broadly to striatum and cortex.

ANATOMY (Jones 2007):
  - CM/Pf: midline-adjacent intralaminar nuclei (not in main sensory pathways)
  - Inputs: brainstem reticular activating system, spinothalamic pain fibers,
    cerebellar nuclei (indirect), basal ganglia (indirect)
  - Outputs: widespread to striatum (motor), prefrontal cortex (arousal),
    posterior parietal, anterior cingulate
  - Burst and tonic modes: CM neurons fire in low-threshold burst mode
    during non-REM sleep and in tonic mode during waking

HALASSA 2021 — AROUSAL AND MATRIX THALAMUS:
  The "matrix" system (intralaminar nuclei + medial thalamus) provides
  broad, low-specificity background excitation to cortex. This is distinct
  from "core" relay nuclei which send specific sensory signals. Matrix cells
  have wide axonal arbors → widespread cortical depolarization.
  This creates a "blanket of arousal" (Halassa's phrase) over which
  specific signals from first-order relays (like MGN → V1) ride.

PAIN RELAY:
  CM receives spinothalamic input for pain. Pf also relays pain and visceral
  input. CM-Pf stimulation can drive anterior cingulate cortex (ACC),
  the cortical seat of pain affect/unpleasantness.

AUTONOMIC INTEGRATION:
  CM/Pf project to insular cortex and hypothalamus — autonomic state
  monitoring. They carry interoceptive signals (body state) alongside
  arousal signals.

KEY FUNCTIONS:
  1. arousal_modulation: ascending arousal signal from brainstem reticular
     formation, gated by current vigilance state
  2. arousal_weight: how strongly CM is amplifying cortex-wide excitation
  3. autonomic_state_signal: interoceptive/body state info from CM/Pf

REFS:
- Halassa 2021 Nat Rev Neurosci 22:515-530 — matrix vs core thalamus, arousal
- Jones 2007 Thalamus Vol I (2nd ed.) — intralaminar anatomy
- McCormick & Bal 1994 Prog Brain Res — thalamic arousal mechanisms
- Van der Werf et al. 2002 Brain Research Reviews — intralaminar functions
- Sherman & Guillery 2013 — thalamocortical function text

CITATIONS:
    PMC3569130 — Schiff ND, Shah SA, Hudson AE et al. (2013). Gating of Attentional
        Effort Through the Central Thalamus. Front Syst Neurosci.
    PMC10366221 — Kumar VJ, Scheffler K, Grodd W (2023). The Structural Connectivity
        Mapping of the Intralaminar Thalamic Nuclei. Hum Brain Mapp.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicCentromedianIntralaminar(BrainMechanism):
    """
    CM/Pf intralaminar nucleus — arousal, pain, and autonomic relay.

    Receives brainstem arousal signals (ARAS), spinothalamic pain input,
    and basal ganglia modulatory signals. Generates a broad arousal
    modulation signal for cortex plus an autonomic state indicator.

    Distinct from specific sensory relays (MGN, VPL) — CM/Pf provide the
    non-specific "arousal blanket" over cortex.
    """

    ARousal_BASELINE = 0.30       # Intrinsic CM firing in relaxed wakefulness
    BURST_GAIN = 1.20             # Gain during burst (arousal onset)
    PAIN_INFLATION = 0.40         # Pain amplifies arousal weight
    AUTONOMIC_INTEGRATION_GAIN = 0.35
    DECAY_RATE = 0.06             # Natural decay per tick

    def __init__(self):
        super().__init__(
            name="ThalamicCentromedianIntralaminar",
            human_analog="Centromedian/Parafascicular intralaminar nuclei — arousal matrix",
            layer="subcortical",
        )
        self.state.setdefault("arousal_modulation", 0.0)
        self.state.setdefault("arousal_weight", 0.0)
        self.state.setdefault("autonomic_state_signal", 0.0)
        self.state.setdefault("last_pain_input", 0.0)
        self.state.setdefault("brainstem_arousal_input", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Brainstem ascending reticular activating system (ARAS)
        arasal_signal = prior.get("BrainstemAscendingArousal", {})
        arasal_level = arasal_signal.get("arousal_signal_strength", 0.0)

        # Source 2: Spinothalamic pain input (via spinal cord relay)
        pain_signal = prior.get("SpinalCordPainRelay", {})
        pain_level = pain_signal.get("pain_signal_strength", 0.0)

        # Source 3: Basal ganglia modulation (indirect pathway)
        indirect_pathway = prior.get("IndirectPathwaySuppressor", {})
        bg_modulation = indirect_pathway.get("suppression_strength", 0.0)

        # Source 4: Interoceptive/autonomic state (from insular thalamic relay)
        autonomic_input = prior.get("InteroceptiveThalamicRelay", {})
        interoceptive_signal = autonomic_input.get("interoceptive_strength", 0.0)

        # Arousal modulation: combines ARAS + pain amplification + BG modulation
        base_arousal = self.ARousal_BASELINE + arasal_level * 0.50

        # Pain inflates arousal (acute pain → high arousal/fight-flight mode)
        pain_boost = pain_level * self.PAIN_INFLATION * 0.5

        # Basal ganglia modulates arousal (high indirect = suppressed arousal)
        bg_mod_effect = (0.5 - bg_modulation) * 0.25

        raw_arousal = base_arousal + pain_boost + bg_mod_effect
        arousal_modulation = max(0.0, min(1.0, raw_arousal))

        # Arousal weight: intensity of CM broadcast to cortex
        # High arousal_weight = strong matrix excitation over cortex
        arousal_weight = max(0.0, min(1.0, arousal_modulation * self.BURST_GAIN))

        # Autonomic state signal: combines interoceptive + pain
        autonomic_state = (
            interoceptive_signal * 0.60
            + pain_level * 0.40
        )
        autonomic_state_signal = max(0.0, min(1.0, autonomic_state))

        # Decay arousal if no input
        if arasal_level < 0.05 and pain_level < 0.05:
            arousal_modulation = max(
                self.ARousal_BASELINE,
                arousal_modulation - self.DECAY_RATE
            )
            arousal_weight = max(0.0, arousal_weight - self.DECAY_RATE)

        self.state["arousal_modulation"] = round(arousal_modulation, 4)
        self.state["arousal_weight"] = round(arousal_weight, 4)
        self.state["autonomic_state_signal"] = round(autonomic_state_signal, 4)
        self.state["last_pain_input"] = round(pain_level, 4)
        self.state["brainstem_arousal_input"] = round(arasal_level, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "arousal_modulation": round(arousal_modulation, 4),
            "arousal_weight": round(arousal_weight, 4),
            "autonomic_state_signal": round(autonomic_state_signal, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

