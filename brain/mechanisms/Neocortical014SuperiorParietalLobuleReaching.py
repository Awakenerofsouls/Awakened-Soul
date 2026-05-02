"""
brain/neocortical/Neocortical014SuperiorParietalLobuleReaching.py
Superior Parietal Lobule — BA 7, Reaching, Spatial Attention

ANATOMY (Colby & Goldberg 1999; Galletti et al. 2022; Sulpizio et al. 2023):
    The superior parietal lobule (SPL, BA 7) occupies the upper half of
    the parietal lobe above the intraparietal sulcus. It is the "spatial
    attention and reach planning" center.

    SPL subdivisions:
    - V6 (area V6, dorsal V6): visual guidance of reaching, visual RFs
      in scene-centered coordinates, sensitivity to gaze direction
    - V6A: visuomotor integration, reach-to-grasp coordination, visual RFs
    - AIP (anterior intraparietal area): grasp formation (but AIP is in IPL,
      not SPL — mediates between SPL spatial and IPL grasp)
    - PE (somatosensory area PE): somatosensory spatial coordinates

    Function: SPL computes "where to reach" in scene-centered coordinates.
    Unlike IPL (which handles the "how to grasp"), SPL handles the
    "where to go" — spatial targeting of the arm.

    Lesions: spatial neglect (when right SPL is damaged), reaching errors,
    optic ataxia (misreaching under visual guidance).

KEY FINDINGS:
    1. Galletti et al. 2022 (PMID 35961383): V6A controls all phases of
       reach-to-grasp — both transport (reaching) and grasping
    2. Sulpizio et al. 2023 (PMID 37572972): Human SPL caudal part handles
       a series of perceptive, visuomotor and somatosensory processes;
       anterior POs uses attention to guide reach
    3. Shomstein & Behrmann 2006 (PMC16407540): SPL mediates voluntary
       control of spatial and nonspatial auditory attention

AGENT'S MAPPING:
    spl_output: dict — spatial targeting output
    spatial_target: dict — target coordinates in space
    reaching_signal: float 0-1 — strength of reaching motor plan

CITATIONS:
    PMC37572972 — Sulpizio et al. (2023). Functional organization of SPL.
        Neurosci Biobehav Rev.
    PMC35961383 — Galletti et al. (2022). Posterior parietal area V6A and attention.
        Neurosci Biobehav Rev.
    PMC16407540 — Shomstein & Behrmann. (2006). Parietal cortex and attention.
        J Neurosci.
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL/SPL.


CITATIONS
---------
  - [Andersen 2002, Annu Rev Neurosci 25:189, parietal cortex]
  - [Husain 2007, Nat Rev Neurosci 8:30, parietal attention]
  - [Goldberg 2006, Nature 444:374, lateral intraparietal]
"""

from brain.base_mechanism import BrainMechanism


class SuperiorParietalLobuleReaching(BrainMechanism):
    """
    SPL (BA 7) — reaching and spatial attention.

    Computes spatial targets in scene-centered coordinates for
    arm movement planning. Works with IPL (grasp) and premotor (action).
    """

    def __init__(self):
        super().__init__(
            name="SuperiorParietalLobuleReaching",
            human_analog="Superior parietal lobule (BA 7) — reaching, spatial attention, V6/V6A",
            layer="neocortical",
        )
        self.state.setdefault("spatial_map", {})
        self.state.setdefault("spatial_target", {})
        self.state.setdefault("reaching_signal", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From IPL sensorimotor integration (object location and grasp)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # From ventral visual stream (object location)
        ventral = prior.get("TemporoOccipitalVisualAssembler", {})
        object_scene = ventral.get("scene_representation", {})

        # From DLPFC (abstract goal coordinates)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_active = dlpfc.get("working_memory_active", False)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5)

        # From anterior insula (salience — what to attend to)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # From posterior cingulate (memory-guided spatial attention)
        pc = prior.get("PosteriorCingulateMemoryAttention", {})
        memory_attention = pc.get("attention_signal", 0.3)

        # Spatial targeting: combines object location + salience + memory
        object_reach = object_scene.get("object_constructed", 0.5) if isinstance(object_scene, dict) else 0.5

        spatial_input = (
            object_reach * 0.3 +
            ipl_int * 0.25 +
            salience * 0.25 +
            memory_attention * 0.2
        )
        spatial_input = max(0.0, min(1.0, spatial_input))

        # Reaching signal: stronger when WM is active and spatial input is high
        reaching_signal = spatial_input * (0.5 + wm_load * 0.5)
        reaching_signal = max(0.0, min(1.0, reaching_signal))

        # Spatial target: where in space the reach is directed
        spatial_target = {
            "scene_coords": "scene_centered",
            "confidence": round(reaching_signal, 4),
            "memory_guided": wm_active and memory_attention > 0.5,
        }

        # Update spatial map
        if reaching_signal > 0.4:
            self.state["spatial_map"]["last_target"] = spatial_target

        self.state["spatial_target"] = spatial_target
        self.state["reaching_signal"] = round(reaching_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "spl_output": {
                "spatial_input": round(spatial_input, 4),
                "reaching_signal": round(reaching_signal, 4),
                "memory_guided": wm_active and memory_attention > 0.5,
            },
            "spatial_target": spatial_target,
            "reaching_signal": round(reaching_signal, 4),
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

