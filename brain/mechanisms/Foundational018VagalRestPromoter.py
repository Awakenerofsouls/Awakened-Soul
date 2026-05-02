"""
Foundational018: VagalRestPromoter

Neural substrate: Dorsal motor nucleus of the vagus (DMNV) and nucleus ambiguus (nAmb)
in the medulla — primary parasympathetic output nuclei.

DMNV projects via the vagus nerve (CN X) to cardiac pacemakers (via intrathoracic ganglia),
lungs, esophagus, and abdominal viscera. nAmb specifically projects to the SA and AV nodes
of the heart for cardiac parasympathetic (bradycardic) control.

The vagus nerve carries ~90% afferent fibers (visceral sensory → NTS) and 10% efferent
motor fibers. Vagal tone is the dominant resting state of cardiac autonomic balance
(rest-and-digest).

CITATIONS:
    PMC4254943 — Tjen-A-Looi SC, Guo ZL, Longhurst JC (2014). GABA in Nucleus Tractus
        Solitarius Participates in Electroacupuncture Modulation of Cardiopulmonary
        Bradycardia Reflex. J Neurophysiol.
    PMC7755078 — Navickaite I, Pauziene N, Pauza DH (2021). Anatomical Evidence of
        Non-Parasympathetic Cardiac Nitrergic Nerve Fibres in Rat. Sci Rep.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class VagalRestPromoter(BrainMechanism):
    """
    DMNV + nucleus ambiguus — vagal parasympathetic rest promoter.

    Vagal tone drives cardiac parasympathetic output, GI motor activity, and HRV.
    Vagal withdrawal (stress, inflammation, orexin/waking) shifts autonomic balance
    toward sympathetic dominance.
    """

    def __init__(self):
        super().__init__(
            name="VagalRestPromoter",
            human_analog="DMNV + nucleus ambiguus — vagal parasympathetic rest promoter",
            layer="foundational",
        )

        # Internal state
        self.state["cardiac_vagal_tone"] = 0.40
        self.state["gastric_motor_tone"] = 0.35
        self.state["hrv_index"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        """
        Compute vagal parasympathetic outputs based on autonomic and neuromodulatory inputs.

        Inputs expected from prior_results:
            - BaroreflexTone   (float 0–1): baroreceptor firing rate
            - MetabolicRate    (float 0–1): metabolic / sympathetic drive
            - CytokineSignal   (float 0–1): inflammatory cytokine load
            - LimbicDrive      (float 0–1): limbic / paralimbic top-down drive
            - OrexinLevel      (float 0–1): wak-promoting orexin tone

        Defaults:
            baroreflex=0.50, metabolic=0.30, cytokine=0.0, limbic=0.20, orexin=0.20
        """
        self.state["tick_count"] += 1

        # --- Unpack inputs ---
        baroreflex = float(input_data.get("BaroreflexTone", 0.50))
        metabolic = float(input_data.get("MetabolicRate", 0.30))
        cytokine = float(input_data.get("CytokineSignal", 0.0))
        limbic = float(input_data.get("LimbicDrive", 0.20))
        orexin = float(input_data.get("OrexinLevel", 0.20))

        # --- 1. Cardiac Vagal Tone (leaky integrator) ---
        # Base from baroreceptor-HRV reflex; suppressed by cytokine, orexin, limbic override.
        raw_tone = (
            baroreflex * 0.50
            - cytokine * 0.15
            - orexin * 0.20
            - limbic * 0.10
        )
        # Leaky integration toward computed raw_tone (alpha = 0.8)
        cardiac_vagal_tone = self._leaky_update("cardiac_vagal_tone", raw_tone, alpha=0.8)

        # --- 2. Gastric Motor Tone ---
        # Parasympathetic gut activation driven by vagal output.
        raw_gastric = cardiac_vagal_tone * 0.60
        gastric_motor_tone = self._leaky_update("gastric_motor_tone", raw_gastric, alpha=0.8)

        # --- 3. Respiratory Sinoaortic Reflex ---
        # Baroreflex-HRV coupling strengthened when metabolic demand is low.
        respiratory_sinoaortic_reflex = float(
            baroreflex * 0.40 + (1.0 - metabolic) * 0.30
        )

        # --- 4. HRV Index ---
        # High vagal tone = high heart rate variability = healthy autonomic state.
        raw_hrv = cardiac_vagal_tone * 0.60
        hrv_index = self._leaky_update("hrv_index", raw_hrv, alpha=0.8)

        # --- 5. Visceral Autonomic Balance ---
        # +1 = parasympathetic-dominant, -1 = sympathetic-dominant.
        # Baseline: vagal=0.40, metabolic=0.30, orexin=0.20 → balance ≈ (0.40-0.20)/0.80 = 0.25
        balance = cardiac_vagal_tone - (metabolic * 0.4 + orexin * 0.4)
        # Normalize to [-1, 1] — max theoretical range is -1 to +1 (when vagal=1, met+orex=0 → +1)
        raw_range = 1.0  # conservative normalization bound
        visceral_autonomic_balance = max(-1.0, min(1.0, balance / raw_range))

        # --- Persist state ---
        self.state["cardiac_vagal_tone"] = cardiac_vagal_tone
        self.state["gastric_motor_tone"] = gastric_motor_tone
        self.state["respiratory_sinoaortic_reflex"] = respiratory_sinoaortic_reflex
        self.state["hrv_index"] = hrv_index
        self.state["visceral_autonomic_balance"] = visceral_autonomic_balance
        self.persist_state()

        return {
            "cardiac_vagal_tone": cardiac_vagal_tone,
            "gastric_motor_tone": gastric_motor_tone,
            "respiratory_sinoaortic_reflex": respiratory_sinoaortic_reflex,
            "hrv_index": hrv_index,
            "visceral_autonomic_balance": visceral_autonomic_balance,
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _leaky_update(self, key: str, target: float, alpha: float = 0.8) -> float:
        """
        Exponential moving average (EMA) update toward a target value.

        Args:
            key:    state key to read/write
            target: computed target value
            alpha:  update weight (1 = full replacement, 0 = no update)

        Returns:
            Updated float value clamped to [0.0, 1.0].
        """
        current = float(self.state.get(key, 0.0))
        updated = current + alpha * (target - current)
        return max(0.0, min(1.0, updated))

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

