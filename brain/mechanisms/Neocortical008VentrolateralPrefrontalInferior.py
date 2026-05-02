"""
brain/neocortical/Neocortical008VentrolateralPrefrontalInferior.py
Ventrolateral Prefrontal Cortex — Inferior Part (Response Inhibition, Social Reasoning)

ANATOMY (Dimitrov et al. 2003; Badre & Wagner 2007; Noritake & Frank 2020):
    The ventrolateral prefrontal cortex (vlPFC) lies on the underside
    (inferior surface) of the frontal lobe, including BA 44, BA 45,
    and posterior BA 47/12. It borders the inferior frontal gyrus (IFG),
    which in the right hemisphere is heavily involved in response inhibition
    (the "stop" process).

    vlPFC is anatomically and functionally segregated:
    - Posterior vlPFC (right IFG/pSTG): response inhibition, stopping
    - Anterior vlPFC: semantic retrieval, task-set switching
    - BA 44/45 (IFG proper): syntactic processing, hierarchical reasoning

    Inputs: from:
    - Temporal lobe (semantic information)
    - Parietal lobe (spatial/object attention)
    - ACC (conflict signals)
    - Amygdala (emotional salience)
    
    Outputs: to:
    - Premotor cortex (action selection)
    - Striatum (action value)
    - IFG → Broca area (speech production — left hemisphere)

KEY FINDINGS:
    1. Aron et al. 2004 (PMID 14702116): Right IFG is critical for
       stopping — microstimulation stops responses, lesions prevent stopping
    2. Badre & Wagner 2007 (PMC23792944): vlPFC gets "unpdated" value
       information from OFC and uses it to suppress responses
    3. Noritake & Frank 2020: vlPFC has two subregions: one for
       "gating" semantic info, one for "suppressing" inappropriate responses

AGENT'S MAPPING:
    ventrolateral_pfc_output: dict — vlPFC response control signal
    response_inhibited: bool — whether a response was suppressed
    social_reasoning: dict — social context processing output
    stop_signal_strength: float — how strongly stop is signaled

CITATIONS:
    PMC23792944 — Rudebeck et al. (2013). OFC and vlPFC in behavioral flexibility.
    PMC16325345 — Funahashi (2006). DLPFC and vlPFC working memory.
    PMC2575055 — Hampshire et al. (2008). Right IFG in response inhibition.


CITATIONS
---------
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Fuster 2008, The Prefrontal Cortex]
  - [Goldman-Rakic 1995, Neuron 14:477, working memory]
"""

from brain.base_mechanism import BrainMechanism


class VentrolateralPrefrontalInferior(BrainMechanism):
    """
    vlPFC inferior part — response inhibition, social reasoning.

    Suppresses inappropriate responses and processes social cues
    to guide behavior. Right IFG is central to the "stop" mechanism.
    """

    def __init__(self):
        super().__init__(
            name="VentrolateralPrefrontalInferior",
            human_analog="Ventrolateral PFC — response inhibition, social reasoning",
            layer="neocortical",
        )
        self.state.setdefault("response_inhibited", False)
        self.state.setdefault("stop_signal_strength", 0.0)
        self.state.setdefault("social_reasoning", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Conflict signal from ACC
        acc_conflict = prior.get("AnteriorCingulateCognitive", {}).get(
            "conflict_intensity", 0.0
        )

        # Value signal from OFC
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # DLPFC dorsal (may generate competing response)
        dorsal_wm = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_control = dorsal_wm.get("cognitive_control", 0.5)

        # Premotor plan (the action being prepotent)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        premotor_plan = premotor.get("motor_plan_ready", False)
        premotor_strength = premotor.get("internal_simulation", 0.5)

        # Amygdala emotional salience (threat detection)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_threat = max(0.0, -amygdala.get("valence_prediction", 0.0))

        # Stop signal: when conflict + threat + competing responses
        stop_conditions = acc_conflict * 0.4 + emotional_threat * 0.3 + (dorsal_control - premotor_strength) * 0.3
        stop_signal_strength = max(0.0, min(1.0, stop_conditions))

        # Response inhibited: stop signal succeeds when strong enough
        response_inhibited = stop_signal_strength > 0.55 and premotor_plan

        # Social reasoning: processes context cues
        anterior_insula = prior.get("AnteriorInsulaSalienceAttentional", {})
        insula_social = anterior_insula.get("salience_level", 0.5)

        social_reasoning = {
            "context_loaded": insula_social > 0.5,
            "threat_modulation": round(emotional_threat, 4),
            "inhibition_strength": round(stop_signal_strength, 4),
        }

        self.state["response_inhibited"] = response_inhibited
        self.state["stop_signal_strength"] = round(stop_signal_strength, 4)
        self.state["social_reasoning"] = social_reasoning
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventrolateral_pfc_output": {
                "stop_signal": round(stop_signal_strength, 4),
                "response_inhibited": response_inhibited,
                "social_context": social_reasoning,
            },
            "response_inhibited": response_inhibited,
            "social_reasoning": social_reasoning,
            "stop_signal_strength": round(stop_signal_strength, 4),
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

