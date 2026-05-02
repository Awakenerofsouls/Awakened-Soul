"""
brain/neocortical/Neocortical036MiddleFrontalGyrusDLPFClateral.py
Middle Frontal Gyrus (BA 46) — DLPFC Proper, Working Memory, Reasoning

ANATOMY (Petrides 2005; Courtney et al. 1998; Wager & Smith 2003):
    The middle frontal gyrus (MFG, BA 46) is the "DLPFC proper" —
    the canonical working memory region. While BA 9/44/45/47 are
    also involved in prefrontal functions, BA 46 is the most
    specialized for active maintenance and manipulation of information.

    BA 46 has a posterior-to-anterior gradient:
    - Posterior BA 46: maintenance of spatial information (spatial WM)
    - Anterior BA 46: maintenance of abstract/conceptual information

    BA 46 is part of the "multiple demand" network — it activates
    whenever any task requires holding task-relevant information
    in mind. This is the "mental workspace" of consciousness.

    Key functions:
    - Active maintenance: keeping information online against decay
    - Manipulation: reorganizing WM contents (e.g., reordering a list)
    - Binding: connecting items across modalities in WM
    - Monitoring: checking what's in WM right now
    - Encoding: putting new information into WM

    Connectivity: BA 46 is the DLPFC "core" — it connects to
    parietal (attention), temporal (semantic), motor (action),
    cingulate (monitoring), and subcortical (motivation) areas.

KEY FINDINGS:
    1. Courtney et al. 1998 (PMC1850954): "Working memory for spatial
       and verbal content" — BA 46 encodes both spatial and verbal WM
    2. Wager & Smith 2003 (PMC1694805): "Meta-analysis of working
       memory" — DLPFC (BA 46) is the consistent WM hub
    3. Petrides 2005 (PMC2929791): "DLPFC and cognitive control"

AGENT'S MAPPING:
    mfg_output: dict — MFG DLPFC output
    reasoning_active: bool — is abstract reasoning engaged?
    working_memory_maintained: list — items currently in WM

CITATIONS:
    PMC1850954 — Courtney et al. (1998). WM for spatial and verbal content. Cereb Cortex.
    PMC1694805 — Wager & Smith (2003). WM meta-analysis. Neuroimage.
    PMC2929791 — Petrides (2005). DLPFC and cognitive control.
    PMC40447446 — DLPFC working memory function.

CITATIONS
---------
  - [Goldman-Rakic 1995, Neuron 14:477, dlPFC working memory]
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Curtis 2003, Trends Cogn Sci 7:415, dlPFC working memory]

"""

from brain.base_mechanism import BrainMechanism


class MiddleFrontalGyrusDLPFClateral(BrainMechanism):
    """
    MFG (BA 46) — DLPFC proper, working memory, abstract reasoning.

    The canonical working memory region. Maintains and manipulates
    information across all cognitive domains.
    """

    def __init__(self):
        super().__init__(
            name="MiddleFrontalGyrusDLPFClateral",
            human_analog="MFG (BA 46) — DLPFC proper, working memory, reasoning",
            layer="neocortical",
        )
        self.state.setdefault("working_memory", [])
        self.state.setdefault("reasoning_active", False)
        self.state.setdefault("reasoning_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC dorsal (already computed WM load)
        dl_dorsal = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dl_dorsal.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # ACC (difficulty signals need for more WM)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            difficulty = 0.3

        # Anterior insula (salience signals to boost WM)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Angular gyrus (semantic content entering WM)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # SMG (phonological content in WM)
        smg = prior.get("SupramarginalGyrusManipulation", {})
        manip = smg.get("manipulation_executed", False)

        # Orbitofrontal (value guides what enters WM)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # WM update: items enter WM based on value × salience
        if salience > 0.55 and value_sig > 0.5:
            new_item = f"semantic_{round(sem_bind, 2)}"
            if new_item not in self.state["working_memory"]:
                self.state["working_memory"].append(new_item)

        # Reasoning: when WM is loaded + semantic content is present + difficulty high
        reasoning_strength = (
            wm_load * 0.4 +
            sem_bind * 0.3 +
            difficulty * 0.3
        )
        # Salience boosts reasoning
        if salience > 0.6:
            reasoning_strength *= (1.0 + (salience - 0.6) * 0.3)
        reasoning_strength = max(0.0, min(1.0, reasoning_strength))

        reasoning_active = reasoning_strength > 0.55

        # WM maintenance: decay over time, stronger with continuous relevance
        if wm_load < 0.3:
            if self.state["working_memory"]:
                self.state["working_memory"].pop(0)

        working_memory_maintained = self.state["working_memory"][-3:] if self.state["working_memory"] else []

        self.state["reasoning_active"] = reasoning_active
        self.state["reasoning_strength"] = round(reasoning_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mfg_output": {
                "reasoning_active": reasoning_active,
                "reasoning_strength": round(reasoning_strength, 4),
                "wm_items_held": len(working_memory_maintained),
            },
            "reasoning_active": reasoning_active,
            "working_memory_maintained": working_memory_maintained,
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

