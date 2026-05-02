"""
Build 12: Foundational017PupilFocusRegulator — Edinger-Westphal Nucleus
======================================================================

PLACEMENT:
  Layer:    foundational (midbrain — Edinger-Westphal nucleus / pretectal area)
  Filename: brain/foundational/Foundational017PupilFocusRegulator.py
  Instance name: PupilFocusRegulator

NEURAL SUBSTRATE:
  Edinger-Westphal nucleus (EWN) in midbrain — preganglionic parasympathetic
  neurons projecting via the oculomotor nerve (CN III) to the ciliary ganglion,
  which innervates the sphincter pupillae muscle (pupil constriction) and ciliary
  muscle (lens accommodation for near focus). Sympathetic input from the
  locus coeruleus (LC) via alpha-1 adrenergic receptors on the dilator pupillae
  opposes this via the superior cervical ganglion. The net pupil diameter
  reflects the balance between parasympathetic constriction and sympathetic dilation.

KEY NEUROANATOMY:
  - EWN (preganglionic parasympathetic): projects to ciliary ganglion → pupil constriction
  - LC-NE sympathetic pathway: superior cervical ganglion → dilator pupillae → dilation
  - Near response: convergence + accommodation + miosis coordinated by EWN
  - Light reflex: direct retina → pretectal nucleus → EWN suppression (parasympathetics OFF → dilation)

INPUTS (prior_results):
  - SympatheticTone: sympathetic_tone (float 0-1) — LC output driving dilation
  - ParasympatheticTone: parasympathetic_tone (float 0-1) — EWN output driving constriction
  - CognitiveLoad: cognitive_load (float 0-1) — prefrontal demand, increases LC tone
  - LightLevel: light_level (float 0-1) — light reflex suppresses parasympathetic

OUTPUTS:
  - pupil_constriction: float [0.0–1.0] — parasympathetic constriction level
  - pupil_dilation: float [0.0–1.0] — sympathetic dilation level
  - net_pupil_size: float [0.0–1.0] — net diameter (0.0=fully constricted, 1.0=fully dilated)
  - accommodation_tone: float [0.0–1.0] — near-focus lens accommodation
  - cognitive_load_index: float [0.0–1.0] — normalized task demand indicator

CITATIONS:
    PMC8869431 — May PJ, Warren S (2020). Pupillary Light Reflex Circuits in the Macaque
        Monkey: The Olivary Pretectal Nucleus. J Comp Neurol.
    PMC6957570 — May PJ, Sun W, Wright NF et al. (2020). Pupillary Light Reflex Circuits
        in the Macaque Monkey: The Preganglionic Edinger-Westphal Nucleus. J Comp Neurol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PupilFocusRegulator(BrainMechanism):
    """
    Edinger-Westphal nucleus — pupil constriction and lens accommodation.

    EWN drives miosis (sphincter pupillae via ACh/muscarinic) and accommodation
    (ciliary muscle via CN III). Sympathetic input from LC drives mydriasis
    (dilator pupillae via alpha-1 NE). Cognitive load elevates LC tone, causing
    task-evoked pupil dilation. Light reflex modulates EWN via pretectal nucleus.

    Inputs: sympathetic_tone, parasympathetic_tone, cognitive_load, light_level.
    Outputs: constriction, dilation, net_pupil_size, accommodation_tone, cognitive_load_index.
    """

    # --- Gain constants ---
    CONSTRICTION_GAIN = 0.70   # parasympathetic → sphincter pupillae drive
    DILATION_GAIN = 0.70       # sympathetic → dilator pupillae drive
    ACCOMMODATION_GAIN = 0.60  # parasympathetic → ciliary muscle (near focus)
    COGNITIVE_GAIN = 0.80     # cognitive load → LC tone contribution

    # --- Defaults when inputs are absent ---
    DEFAULT_SYMPATHETIC_TONE = 0.30
    DEFAULT_PARASYMPATHETIC_TONE = 0.30
    DEFAULT_COGNITIVE_LOAD = 0.0
    DEFAULT_LIGHT_LEVEL = 0.50

    def __init__(self):
        super().__init__(
            name="PupilFocusRegulator",
            human_analog="Edinger-Westphal nucleus — pupil constriction and accommodation",
            layer="foundational",
        )
        self.state.setdefault("pupil_constriction", 0.30)
        self.state.setdefault("pupil_dilation", 0.30)
        self.state.setdefault("net_pupil_size", 0.50)
        self.state.setdefault("accommodation_tone", 0.20)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read inputs with defaults ---
        sympathetic_tone = (
            prior.get("SympatheticTone", {})
            .get("sympathetic_tone", self.DEFAULT_SYMPATHETIC_TONE)
        )
        parasympathetic_tone = (
            prior.get("ParasympatheticTone", {})
            .get("parasympathetic_tone", self.DEFAULT_PARASYMPATHETIC_TONE)
        )
        cognitive_load = (
            prior.get("CognitiveLoad", {})
            .get("cognitive_load", self.DEFAULT_COGNITIVE_LOAD)
        )
        light_level = (
            prior.get("LightLevel", {})
            .get("light_level", self.DEFAULT_LIGHT_LEVEL)
        )

        # --- Compute pupil constriction (EWN → sphincter pupillae via ACh/muscarinic) ---
        pupil_constriction = parasympathetic_tone * self.CONSTRICTION_GAIN
        pupil_constriction = max(0.0, min(1.0, pupil_constriction))

        # --- Compute pupil dilation (LC → dilator pupillae via alpha-1 NE) ---
        pupil_dilation = sympathetic_tone * self.DILATION_GAIN
        pupil_dilation = max(0.0, min(1.0, pupil_dilation))

        # --- Cognitive load elevates LC tone → additional dilation ---
        cognitive_load_index = cognitive_load * self.COGNITIVE_GAIN
        pupil_dilation += cognitive_load_index
        pupil_dilation = max(0.0, min(1.0, pupil_dilation))

        # --- Light reflex: bright light suppresses EWN → dilation ---
        # High light_level reduces parasympathetic constriction further,
        # biasing net_pupil_size toward dilation
        light_suppression = light_level * 0.15

        # --- Net pupil size: balance of constriction vs dilation ---
        # dilation (sympathetic) pushes toward 1.0, constriction (parasympathetic) pushes toward 0.0
        # Light suppression adds to dilation bias
        net_pupil_size = (pupil_dilation - pupil_constriction + light_suppression + 1.0) / 2.0
        net_pupil_size = max(0.0, min(1.0, net_pupil_size))

        # --- Accommodation tone: ciliary muscle for near-focus (EWN-mediated) ---
        accommodation_tone = parasympathetic_tone * self.ACCOMMODATION_GAIN
        accommodation_tone = max(0.0, min(1.0, accommodation_tone))

        # --- Persist ---
        self.state["pupil_constriction"] = pupil_constriction
        self.state["pupil_dilation"] = pupil_dilation
        self.state["net_pupil_size"] = net_pupil_size
        self.state["accommodation_tone"] = accommodation_tone
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pupil_constriction": pupil_constriction,
            "pupil_dilation": pupil_dilation,
            "net_pupil_size": net_pupil_size,
            "accommodation_tone": accommodation_tone,
            "cognitive_load_index": cognitive_load_index,
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

