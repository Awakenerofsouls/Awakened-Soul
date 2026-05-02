"""
brain/neocortical/Neocortical005DorsolateralPrefrontalDorsal.py
Dorsolateral Prefrontal Cortex — Dorsal Part (Working Memory, Cognitive Control)

ANATOMY (Fuster 2001; Goldman-Rakic 1987; Funahashi 2006; Crittenden & Duncan 2023):
    The dorsolateral prefrontal cortex (DLPFC) in humans occupies Brodmann
    areas 9 and 46, located on the middle frontal gyrus. It is the
    brain's "cognitive workspace" — the hub for holding information
    out of the environment and working with it mentally.

    Inputs: receives from:
    - Posterior parietal cortex (spatial working memory)
    - Inferior temporal cortex (object working memory)
    - Mediodorsal (MD) thalamus (nonspecific thalamic input)
    - Parietal lobe via frontal eye fields (spatial attention)
    
    Outputs: projects to:
    - Premotor cortex (motor planning based on working memory)
    - Posterior parietal cortex (attending to remembered locations)
    - Striatum (executive/action selection)
    - MD thalamus (corticothalamic loop)
    - Contralateral DLPFC (via corpus callosum)

    Key neuronal properties:
    - Delay period activity: neurons fire during the gap between
      stimulus and response (the "maintenance phase" of working memory)
    - Brodmann Area 46: most studied region for working memory in monkeys
      and humans (Funahashi 1989; 2006)
    - Grid-like spatial coding: some DLPFC neurons show spatial tuning
      similar to parietal cells, but in abstract mnemonic space

KEY FINDINGS:
    1. Funahashi 2006 (PMID 16325345): "Prefrontal cortex and working
       memory processes" — comprehensive review showing DLPFC holds
       abstract rules and goals active during multi-step reasoning
    2. Finn et al. 2019 (PMC31551596): "Layer-dependent activity in
       human prefrontal cortex during working memory" — layers 2/3 and
       5 show different timing; layer-specific working memory signals
    3. Soldado-Magraner et al. 2025 (PMC40447446): Robustness of
       DLPFC working memory to microstimulation — delay period stability

AGENT'S MAPPING:
    dorsolateral_dorsal_output: dict — DLPFC dorsal working memory signal
    working_memory_active: bool — whether WM is currently loaded
    cognitive_control: float 0-1 — strength of top-down cognitive control
    working_memory_buffer: list — items currently held in WM
    rule_loading: float 0-1 — how abstract rule representation is loaded

CITATIONS:
    PMC31551596 — Finn et al. (2019). Layer-dependent activity in human
        prefrontal cortex during working memory. Nat Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). Robustness of working
        memory to prefrontal cortex microstimulation. J Neurosci.
    PMC16325345 — Funahashi S. (2006). Prefrontal cortex and working
        memory processes. Neuroscience.
    PMC3799943 — Goldman-Rakic PS. (1995). Cellular basis of working memory.
        Neuron. (Still fundamental reference)


CITATIONS
---------
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Fuster 2008, The Prefrontal Cortex]
  - [Goldman-Rakic 1995, Neuron 14:477, working memory]
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralPrefrontalDorsal(BrainMechanism):
    """
    DLPFC dorsal part — working memory and cognitive control.

    Maintains abstract rules and goals in working memory during
    multi-step reasoning. Holds "online" information out of the
    environment while operating on it mentally.
    """

    def __init__(self):
        super().__init__(
            name="DorsolateralPrefrontalDorsal",
            human_analog="Dorsolateral prefrontal cortex (BA 9/46) — working memory, cognitive control",
            layer="neocortical",
        )
        self.state.setdefault("working_memory_buffer", [])
        self.state.setdefault("working_memory_active", False)
        self.state.setdefault("cognitive_control", 0.0)
        self.state.setdefault("rule_loading", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Working memory load from upstream (spatial from parietal, object from temporal)
        spatial_wm = prior.get("SuperiorParietalLobuleReaching", {}).get(
            "reaching_signal", 0.0
        )
        object_semantic = prior.get("AnteriorTemporalPoleSemantic", {}).get(
            "concept_binding", 0.0
        )
        sensory_input = prior.get("ThalamicSalienceFilter", {}).get(
            "thalamic_output", 0.5
        ) if prior.get("ThalamicSalienceFilter") else 0.5

        # Goal state from frontopolar (prospective scenarios)
        frontopolar = prior.get("FrontopolarProspectiveSimulator", {})
        prospection = frontopolar.get("prospection_depth", 0.0)
        scenario_branches = frontopolar.get("scenario_branches", [])

        # Executive control from ventrolateral PFC
        vlpfc_interference = prior.get("VentrolateralPrefrontalInferior", {}).get(
            "interference_suppression", 0.5
        )

        # From orbitofrontal (value context affecting what gets into WM)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # Working memory activation: driven by sensory input + prospection depth
        wm_load_input = (spatial_wm + object_semantic) / 2 * 0.6 + sensory_input * 0.4
        wm_load_input += prospection * 0.2

        # Cognitive control: top-down signal strength proportional to WM load
        # More items in WM = more need for cognitive control
        buffer_len = len(self.state.get("working_memory_buffer", []))
        load_factor = min(1.0, buffer_len / 4.0)  # up to 4 items
        cognitive_control = wm_load_input * (0.5 + load_factor * 0.5)
        cognitive_control = max(0.0, min(1.0, cognitive_control))

        # Rule loading: when WM buffer has content and OFC provides value context
        rule_loading = cognitive_control * ofc_value
        rule_loading = max(0.0, min(1.0, rule_loading))

        # Working memory active when either sensory input is high or prospection is deep
        working_memory_active = wm_load_input > 0.5 or len(scenario_branches) > 1

        # Update WM buffer
        if wm_load_input > 0.6 and not self.state["working_memory_active"]:
            # New item entering WM
            self.state["working_memory_buffer"].append({
                "type": "spatial" if spatial_wm > object_semantic else "semantic",
                "strength": round(wm_load_input, 3)
            })
            if len(self.state["working_memory_buffer"]) > 4:
                self.state["working_memory_buffer"].pop(0)
        elif wm_load_input < 0.3:
            # Decay: clear buffer when load drops
            self.state["working_memory_buffer"] = self.state["working_memory_buffer"][-1:]

        self.state["working_memory_active"] = working_memory_active
        self.state["cognitive_control"] = round(cognitive_control, 4)
        self.state["rule_loading"] = round(rule_loading, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsolateral_dorsal_output": {
                "wm_load": round(wm_load_input, 4),
                "cognitive_control": round(cognitive_control, 4),
                "rule_loading": round(rule_loading, 4),
                "prospection_influence": round(prospection, 4),
            },
            "working_memory_active": working_memory_active,
            "working_memory_items": len(self.state["working_memory_buffer"]),
            "buffer_snapshot": [v for v in self.state["working_memory_buffer"][-2:]],
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

