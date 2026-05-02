"""
brain/neocortical/Neocortical044PrefrontalCortexLayerSpecific.py
Prefrontal Cortex Layer-Specific Processing — II/III/V/VI Functional Architecture

ANATOMY (Barbas et al. 2005; Badre & D'Esposito 2009; Somerville & Wig 2013):
    The prefrontal cortex has a distinctive 6-layer organization,
    but the layers have different computational roles than in sensory
    cortex. The four key functional layers in PFC:

    Layer II (input layer):
    - Receives feedback from higher-order association areas
    - Recurrent connections from other PFC areas
    - Stores recently active representations
    - "Working memory buffer" — what's relevant right now

    Layer III (associative input layer):
    - Receives feedforward input from lower areas
    - Long-range association fibers from other cortical areas
    - Initial integration of new information
    - "New information integration"

    Layer V (subcortical output layer):
    - Projects to thalamus (MD, mediodorsal nucleus)
    - Projects to striatum (motor output pathways)
    - Projects to brainstem and spinal cord
    - Generates behavioral outputs
    - "Action command layer"

    Layer VI (thalamic feedback layer):
    - Projects back to thalamus (MD)
    - Provides feedback predictions to lower stages
    - Regulates thalamic gating
    - "Prediction/error correction layer"

    The PFC has more Layer II/III than sensory cortex — reflecting
    its role as an associative "workspace" where information is
    maintained and manipulated.

KEY FINDINGS:
    1. Badre & D'Esposito 2009 (PMC2929791): "The organization of
       the PFC along dorsal-ventral and rostral-caudal axes"
    2. Barbas et al. 2005: PFC laminar organization and function
    3. Somerville & Wig 2013: Layer-specific processing in PFC

AGENT'S MAPPING:
    pfc_layer_output: dict — layer-specific PFC outputs
    layer_specific_processing: dict — what each layer is doing

CITATIONS:
    PMC2929791 — Badre & D'Esposito (2009). PFC organization. Scholarpedia.
    PMC1694808 — Koechlin et al. (2003). PFC hierarchical control.
    PMC11160327 — Duncan & Owen (2000). Common frontal activations.
    PMC40447446 — DLPFC WM and layer processing.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
"""

from brain.base_mechanism import BrainMechanism


class PrefrontalCortexLayerSpecific(BrainMechanism):
    """
    PFC layer-specific processing — II/III/V/VI functional architecture.

    Abstracts the four functional layers of PFC and their distinct roles.
    """

    def __init__(self):
        super().__init__(
            name="PrefrontalCortexLayerSpecific",
            human_analog="PFC layers II/III/V/VI — recurrent/associative/output/thalamic feedback",
            layer="neocortical",
        )
        self.state.setdefault("layer_weights", {})
        self.state.setdefault("layer_outputs", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (canonical working memory — maps to all layers)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # ACC (task difficulty feeds into layer processing)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # Anterior insula (salience boost for all layers)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Layer II: recurrent buffer (working memory)
        layer_2_recurrent = wm_load * 0.7 + (1.0 - error_sig) * 0.3

        # Layer III: associative integration (new + old)
        layer_3_associative = wm_load * cognitive_ctrl * 0.5 + difficulty * 0.5

        # Layer V: subcortical output (motor/thalamic commands)
        layer_5_output = cognitive_ctrl * 0.6 + salience * 0.4
        layer_5_output = max(0.0, min(1.0, layer_5_output))

        # Layer VI: thalamic feedback (prediction error)
        layer_6_feedback = error_sig * 0.5 + difficulty * 0.5

        # Apply salience boost to all layers
        if salience > 0.6:
            boost = 1.0 + (salience - 0.6) * 0.3
            layer_2_recurrent *= boost
            layer_3_associative *= boost

        # Clamp all
        layer_2_recurrent = max(0.0, min(1.0, layer_2_recurrent))
        layer_3_associative = max(0.0, min(1.0, layer_3_associative))
        layer_5_output = max(0.0, min(1.0, layer_5_output))
        layer_6_feedback = max(0.0, min(1.0, layer_6_feedback))

        layer_specific_processing = {
            "layer_2_recurrent": round(layer_2_recurrent, 4),
            "layer_3_associative": round(layer_3_associative, 4),
            "layer_5_subcortical": round(layer_5_output, 4),
            "layer_6_thalamic_feedback": round(layer_6_feedback, 4),
        }

        self.state["layer_weights"] = layer_specific_processing
        self.state["layer_outputs"] = layer_specific_processing
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pfc_layer_output": layer_specific_processing,
            "layer_specific_processing": layer_specific_processing,
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

