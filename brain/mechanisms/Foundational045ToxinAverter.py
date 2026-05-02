"""
Build 45: Foundational045ToxinAverter — Area Postrema Chemoreceptor Trigger Zone
==========================================================================

PLACEMENT:
  Layer:    foundational (brainstem — area postrema, area postrema NTS)
  Filename: brain/foundational/Foundational045ToxinAverter.py
  Instance name: ToxinAverter

NEURAL SUBSTRATE:
  Area postrema (AP) — the chemoreceptor trigger zone (CTZ), located
  in the floor of the fourth ventricle, lacking a blood-brain barrier.
  The AP detects emetic (vomiting-inducing) substances in the blood:
  - Toxins: bacterial toxins (Staphylococcus aureus enterotoxin)
  - Chemotherapy agents: cisplatin, doxorubicin (activate 5-HT3 on AP neurons)
  - Motion sickness signals: vestibular input to AP → nausea
  - Cytokines: IL-1β, IL-6, TNF-α → sickness nausea via AP

  AP PROJECTS TO:
  - NTS (solitary tract): integration of emetic signals
  - Dorsal motor nucleus of vagus: vomiting motor program
  - Parabrachial nucleus: nausea/aversion learning

  EMETIC PATHWAY:
  AP/NTS → central pattern generator for vomiting → respiratory muscles,
  diaphragm, abdominal muscles → retrograde GI motility + antiperistalsis

  Human analog: nausea, emesis, toxin avoidance, motion sickness.

Output keys:
  nausea_intensity: float [0.0–1.0] — nausea level
  emetic_trigger: float [0.0–1.0] — vomiting trigger (thresholded)
  toxin_detection: float [0.0–1.0] — AP toxin signal
  motion_sickness_contribution: float [0.0–1.0] — vestibular nausea input
  defensive_gag_reflex: float [0.0–1.0] — anticipatory defensive response

CITATIONS:
    PMC1028578 — Baker PC, Bernat JL (1985). The Neuroanatomy of Vomiting in Man:
        Association of Projectile Vomiting With a Solitary Metastasis in the Lateral
        Tegmentum of the Pons. Mayo Clin Proc.
    PMC7364392 — Cohen DT, Craven C, Bragin I (2020). Ischemic Stroke Induced Area
        Postrema Syndrome With Intractable Nausea, Vomiting, and Hiccups.
        Neurologist.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ToxinAverter(BrainMechanism):
    """
    Area postrema: chemoreceptor trigger zone for nausea and emesis.

    Detects blood-borne toxins, chemotherapy agents, cytokines, and
    vestibular signals to generate nausea and trigger protective vomiting.
    """

    STATE_FIELDS = [
        "nausea_intensity", "emetic_trigger", "toxin_detection",
        "motion_sickness_contribution", "defensive_gag_reflex", "tick_count",
    ]

    NAUSEA_GAIN = 0.60
    EMETIC_THRESHOLD = 0.80
    TOXIN_GAIN = 0.55
    VESTIBULAR_GAIN = 0.40
    GAG_GAIN = 0.45

    def __init__(self, name: str = "ToxinAverter",
                 human_analog: str = "Area postrema — chemoreceptor trigger zone",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["nausea_intensity"] = 0.0
        self.state["emetic_trigger"] = 0.0
        self.state["toxin_detection"] = 0.0
        self.state["motion_sickness_contribution"] = 0.0
        self.state["defensive_gag_reflex"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cytokines = prior.get("ImmuneSignalRelay", {}).get("immune_activation", 0.0)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        gut_signal = prior.get("GutSignalRelay", {}).get("gastrointestinal_activity", 0.30)
        serotonin = prior.get("DorsalRapheSerotonin", {}).get("serotonin_level", 0.30)
        emetic_drug = prior.get("EmeticChemotherapySignal", {}).get("emetic_level", 0.0)

        # Toxin detection: cytokines + emetic drugs directly activate AP
        toxin_detection = (cytokines * self.TOXIN_GAIN) + (emetic_drug * 0.80)
        toxin_detection = min(1.0, toxin_detection)

        # Motion sickness: vestibular input to AP via NTS
        vestibular_nausea = abs(vestibular - 0.5) * self.VESTIBULAR_GAIN
        motion_sickness_contribution = vestibular_nausea

        # Nausea: sum of all emetic contributors
        nausea_raw = (
            toxin_detection * self.NAUSEA_GAIN +
            vestibular_nausea * self.NAUSEA_GAIN * 0.50 +
            gut_signal * 0.20
        )
        nausea_intensity = min(1.0, max(0.0, nausea_raw))

        # Emetic trigger: fires when nausea exceeds threshold
        if nausea_intensity > self.EMETIC_THRESHOLD:
            emetic_trigger = (nausea_intensity - self.EMETIC_THRESHOLD) / (1.0 - self.EMETIC_THRESHOLD)
        else:
            emetic_trigger = 0.0
        emetic_trigger = min(1.0, emetic_trigger)

        # Defensive gag reflex: anticipatory response before full emesis
        if nausea_intensity > 0.40 and emetic_trigger < 0.30:
            gag_reflex = nausea_intensity * self.GAG_GAIN
        else:
            gag_reflex = 0.0

        # --- Persist ---
        self.state["nausea_intensity"] = round(nausea_intensity, 4)
        self.state["emetic_trigger"] = round(emetic_trigger, 4)
        self.state["toxin_detection"] = round(toxin_detection, 4)
        self.state["motion_sickness_contribution"] = round(motion_sickness_contribution, 4)
        self.state["defensive_gag_reflex"] = round(gag_reflex, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "nausea_intensity": round(nausea_intensity, 4),
            "emetic_trigger": round(emetic_trigger, 4),
            "toxin_detection": round(toxin_detection, 4),
            "motion_sickness_contribution": round(motion_sickness_contribution, 4),
            "defensive_gag_reflex": round(gag_reflex, 4),
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

