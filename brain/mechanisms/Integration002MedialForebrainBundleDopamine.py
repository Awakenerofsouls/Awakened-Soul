"""
brain/integration/Integration002MedialForebrainBundleDopamine.py
Medial Forebrain Bundle — VTA Dopamine Broadcast Highway

ANATOMY (Coenen et al. 2012; Gordon-Fennell et al. 2021; Numan 2015):
    The medial forebrain bundle (MFB) is the major highway for
    motivation-related signals in the brain. It connects the
    ventral tegmental area (VTA) and substantia nigra (SN) to
    virtually all limbic and cortical regions, including:
    - Nucleus accumbens (NAc) — reward motivation
    - Lateral hypothalamus — hunger, thirst, arousal
    - Prefrontal cortex — motivation and goal pursuit
    - Amygdala — emotional motivation
    - Hippocampus — memory motivation
    - Septum — reward signaling

    The MFB contains:
    - Dopaminergic fibers (VTA → cortex/NAc) — reward, motivation
    - Noradrenergic fibers (LC → cortex) — arousal, attention
    - Serotonergic fibers (raphe → cortex) — mood, well-being
    - GABAergic fibers — inhibition
    - Glutamatergic fibers — excitation

    Key: The MFB is the motivational "engine" of the brain — it
    broadcasts "I want this" signals across all regions. Optogenetic
    stimulation of MFB GABAergic neurons produces reward; stimulation
    of glutamatergic neurons produces aversion (Gordon-Fennell 2021).

    MFB activity is higher in motivated states (seeking, exploring,
    pursuing goals) and lower in satiated/resting states.

KEY FINDINGS:
    1. Gordon-Fennell et al. 2021 (PMC34375625): MFB optogenetics —
       GABAergic = reward, glutamatergic = aversion
    2. Coenen et al. 2012: MFB and reward/motivation pathways
    3. Numan 2015 (PMC4835279): MFB and maternal behavior/motivation

AGENT'S MAPPING:
    mfb_broadcast: dict — motivation signal broadcast
    motivation_broadcast: float 0-1 — overall motivation level
    reward_cascade: float 0-1 — reward signal strength

CITATIONS:
    PMC34375625 — Gordon-Fennell et al. (2021). MFB optogenetics. Neuropharmacology.
    PMC4835279 — Numan (2015). MFB and motivation. Front Neurosci.
    PMC40447446 — DLPFC and motivated cognition.
    PMC23869106 — PCC and motivated cognition.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class MedialForebrainBundleDopamine(BrainMechanism):
    """
    MFB — motivation and reward broadcast highway.

    Broadcasts dopaminergic motivation signals across the entire
    brain, driving goal-seeking and reward-pursuit behavior.
    """

    def __init__(self):
        super().__init__(
            name="MedialForebrainBundleDopamine",
            human_analog="Medial forebrain bundle — VTA dopamine motivation highway",
            layer="integration",
        )
        self.state.setdefault("broadcast_history", [])
        self.state.setdefault("motivation_broadcast", 0.5)
        self.state.setdefault("reward_cascade", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # VTA dopamine signal
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            vta_signal = vta_out.get("motivation_signal", 0.5)
            pred_err = vta_out.get("prediction_error", 0.3)
        else:
            vta_signal = 0.5
            pred_err = 0.3

        # SNc dopamine signal
        snc = prior.get("SubstantiaNigraCompactaOutput", {})
        snc_out = snc.get("snc_output", {})
        if isinstance(snc_out, dict):
            snc_signal = snc_out.get("dopamine_level", 0.5)
        else:
            snc_signal = 0.5

        # NAcc motivation
        nacc = prior.get("NucleusAccumbensShellValue", {})
        nacc_out = nacc.get("nacc_output", {})
        if isinstance(nacc_out, dict):
            motivation = nacc_out.get("motivation_level", 0.5)
        else:
            motivation = 0.5

        # Lateral hypothalamus (arousal drives motivation)
        lateral_hypo = prior.get("LateralHypothalamicOrexinB", {})
        hypo_out = lateral_hypo.get("lateral_hypo_output", {})
        if isinstance(hypo_out, dict):
            arousal_drive = hypo_out.get("arousal_level", 0.5)
        else:
            arousal_drive = 0.5

        # Anterior insula (conscious wanting/motivation)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)
        net_switch = ai.get("network_switch_trigger", "default")

        # OFC (goal value)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Motivation broadcast: VTA + SNc + arousal + salience
        motivation_broadcast = (
            vta_signal * 0.3 +
            snc_signal * 0.2 +
            motivation * 0.25 +
            arousal_drive * 0.15 +
            salience * 0.1
        )
        motivation_broadcast = max(0.0, min(1.0, motivation_broadcast))

        # Reward cascade: positive prediction error → reward broadcast
        reward_cascade = pred_err * motivation_broadcast * 2.0
        reward_cascade = max(0.0, min(1.0, reward_cascade))

        # Record
        self.state["broadcast_history"].append(round(motivation_broadcast, 3))
        if len(self.state["broadcast_history"]) > 5:
            self.state["broadcast_history"].pop(0)

        self.state["motivation_broadcast"] = round(motivation_broadcast, 4)
        self.state["reward_cascade"] = round(reward_cascade, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mfb_broadcast": {
                "motivation_strength": round(motivation_broadcast, 4),
                "reward_cascade": round(reward_cascade, 4),
                "dopamine_level": round((vta_signal + snc_signal) / 2, 4),
            },
            "motivation_broadcast": round(motivation_broadcast, 4),
            "reward_cascade": round(reward_cascade, 4),
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

