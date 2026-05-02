"""
brain/neocortical/Neocortical030AnteriorInsulaSalienceAttentional.py
Anterior Insula — Salience Detection, Awareness, Subjective Feeling

ANATOMY (Craig 2009, 2011; Critchley 2004; Seeley 2007):
    The anterior insula (AI) is the "conscious awareness" cortex.
    It is the only cortical region that directly represents
    subjective feeling states — not just "there's a stimulus,"
    but "I feel this."

    AI sits at the intersection of:
    - Interoceptive input (body signals: heart, breath, gut, temperature)
    - Exteroceptive input (sensory events in the world)
    - Affective salience (how important is this to me?)
    - Subjective awareness ("I am aware of this right now")

    Craig's model (2009, 2011): AI is the neural substrate for
    subjective awareness. The right AI generates a moment-to-moment
    "feeling" of existing in time (the "aterial" substrate of
    consciousness). This feeling is constructed from:
    1. Interoceptive signals from posterior insula
    2. Combined with salient exteroceptive events
    3. Integrated into a conscious moment

    AI connects to:
    - ACC (salience network hub)
    - DLPFC (executive attention)
    - amygdala (emotional salience)
    - hypothalamus (autonomic control)

    Key: AI is the "switchboard" — when something is salient
    enough, AI switches from Default Mode (mind-wandering) to
    Executive Mode (task-focused attention).

KEY FINDINGS:
    1. Craig 2009 (PMID 19487195): "Emotional moments across time"
       — AI as neural substrate for subjective awareness
    2. Craig 2011: "Perceived body moment-to-moment" — interoceptive
       awareness is the foundation of subjective feeling
    3. Seeley 2007 (PMC1934629): "Salience network" — AI+ACC as the
       SN hub that switches between DMN and CEN

AGENT'S MAPPING:
    anterior_insula_output: dict — AI salience output
    salience_detected: bool — is current stimulus salient?
    network_switch_trigger: str — which network to switch to

CITATIONS:
    PMID 19487195 — Craig (2009). Emotional moments and awareness in AI. Phil Trans B.
    PMC19072897 — Taylor et al. (2009). Insula-cingulate connectivity. Hum Brain Mapp.
    PMC26388817 — Terasawa et al. (2015). Insula and emotion. Front Psychol.
    PMC1934629 — Seeley et al. (2007). Salience network. J Neurosci.


CITATIONS
---------
  - [Posner 1990, Annu Rev Neurosci 13:25, attention networks]
  - [Corbetta 2002, Nat Rev Neurosci 3:201, attention systems]
  - [Desimone 1995, Annu Rev Neurosci 18:193, selective attention]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInsulaSalienceAttentional(BrainMechanism):
    """
    AI — salience detection and awareness.

    Detects what's important right now, generates subjective
    feeling, and triggers network switches (DMN ↔ CEN).
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInsulaSalienceAttentional",
            human_analog="Anterior insula — salience detection, subjective awareness, network switching",
            layer="neocortical",
        )
        self.state.setdefault("salience_history", [])
        self.state.setdefault("salience_level", 0.0)
        self.state.setdefault("salience_detected", False)
        self.state.setdefault("network_mode", "default")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Posterior insula (raw body signals — the "feeling" substrate)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            visceral_sig = raw_body.get("visceral_signal", 0.3)
        else:
            visceral_sig = float(raw_body) if raw_body else 0.3

        # Amygdala (emotional salience — threat or reward?)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # DLPFC (cognitive salience — "this is task-relevant")
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # pSTG (social salience — who is in the environment?)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        social_motion = pstg.get("social_motion", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Limbic AI (emotional salience)
        ai_limbic = prior.get("AnteriorInsulaGranular", {})
        gut_feeling = ai_limbic.get("conscious_feeling", {})
        if isinstance(gut_feeling, dict):
            gut_int = gut_feeling.get("feeling_intensity", 0.5)
        else:
            gut_int = 0.5

        # Salience: combines visceral + emotional + cognitive + social
        salience_input = (
            visceral_sig * 0.25 +
            abs(emotional_tag) * 0.25 +
            cognitive_ctrl * 0.2 +
            av_binding * 0.15 +
            gut_int * 0.15
        )
        # Emotional salience amplifies
        if abs(emotional_tag) > 0.5:
            salience_input *= (1.0 + (abs(emotional_tag) - 0.5) * 0.5)
        salience_input = max(0.0, min(1.0, salience_input))

        salience_detected = salience_input > 0.55

        # Network switch: high salience + WM active = executive; low = default
        if salience_detected and wm_active:
            network_mode = "executive"
        elif salience_input > 0.65:
            network_mode = "salience_switch"
        else:
            network_mode = "default"

        # Update history
        self.state["salience_history"].append(round(salience_input, 3))
        if len(self.state["salience_history"]) > 5:
            self.state["salience_history"].pop(0)

        self.state["salience_level"] = round(salience_input, 4)
        self.state["salience_detected"] = salience_detected
        self.state["network_mode"] = network_mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_insula_output": {
                "salience_level": round(salience_input, 4),
                "salience_detected": salience_detected,
                "network_mode": network_mode,
            },
            "salience_level": round(salience_input, 4),
            "salience_detected": salience_detected,
            "network_switch_trigger": network_mode,
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

