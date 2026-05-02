"""
brain/neocortical/Neocortical009FrontopolarProspectiveSimulator.py
Frontopolar Cortex — BA 10, Prospective Memory, Future Simulation

ANATOMY (Burgess et al. 2007; Gilbert & Levelt 2007; Badre & D'Esposito 2007; Donoso et al. 2014):
    The frontopolar cortex (FPC, BA 10) is the most anterior region of
    the prefrontal cortex, sitting at the very front of the brain. In
    humans it covers ~2.8% of total cortical volume, making it one of
    the largest "association" regions relative to our brain size.

    BA 10 is involved in:
    - Prospective memory: remembering to do things in the future
    - Multi-tasking: managing multiple goals simultaneously
    - Future thinking: simulating and planning future scenarios
    - "Meta-cognitive" operations: thinking about what we think

    The FPC is connected to both the DLPFC (executive) and OFC (value)
    networks. It is uniquely positioned to "branch" — to consider
    multiple possible futures simultaneously rather than committing
    to a single path.

    Burgess et al. 2007: "The frontopolar cortex is recruited when
    people have to think for themselves rather than follow routine."

KEY FINDINGS:
    1. Burgess et al. 2007 (PMC2762075): "Fractionating the frontal lobe":
        FPC handles "branching" — creating multiple parallel subgoals
    2. Donoso et al. 2014 (PMC4159692): Human FPC is recruited when
        learning something without a known solution — "cognitive exploration"
    3. Badre & D'Esposito 2007: FPC is the top of a hierarchical
        prefrontal gradient — from specific motor actions (M1) to
        abstract goals (FPC)

AGENT'S MAPPING:
    frontopolar_output: dict — prospective/future simulation output
    scenario_branches: list — active future scenarios being considered
    prospection_depth: float 0-1 — how deeply FPC is simulating futures
    branching_score: float — how many branches are being actively processed

CITATIONS:
    PMC2762075 — Burgess et al. (2007). Fractionating the frontal lobe.
        Phil Trans R Soc B.
    PMC4159692 — Donoso et al. (2014). Foundations of human FPC.
        Nat Neurosci.
    PMC23792944 — Rudebeck et al. (2013). OFC and PFC in behavioral flexibility.
    PMC31551596 — Finn et al. (2019). Human DLPFC and frontopolar integration.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class FrontopolarProspectiveSimulator(BrainMechanism):
    """
    Frontopolar cortex (BA 10) — prospective memory, future simulation, branching.

    Generates multiple possible future scenarios and holds them in
    parallel. Enables "thinking for yourself" rather than following
    routine — the most human of all prefrontal functions.
    """

    def __init__(self):
        super().__init__(
            name="FrontopolarProspectiveSimulator",
            human_analog="Frontopolar cortex (BA 10) — prospective memory, future simulation, branching",
            layer="neocortical",
        )
        self.state.setdefault("scenario_stack", [])
        self.state.setdefault("prospection_depth", 0.0)
        self.state.setdefault("branching_score", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC working memory load (goals being held)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_active = dlpfc.get("working_memory_active", False)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5)

        # OFC value signal (outcome being predicted)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)
        expected_value = ofc.get("expected_value", 0.5)

        # Orbitofrontal state (current reward context)
        ofc_state = ofc.get("ofc_state", "neutral")

        # Anterior cingulate (cognitive effort/multi-tasking demand)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_control = acc.get("cognitive_control", 0.5)

        # Ventral subiculum (context — where are we in time/space?)
        vsub = prior.get("VentralSubiculumOutput", {})
        context_tag = vsub.get("emotional_context_tag", 0.0)

        # When WM is active + ACC demands multi-tasking → prospection activated
        # The deeper the WM load and more branches, the deeper the simulation
        prospection_input = wm_load * 0.5 + acc_control * 0.5

        # Prospection depth: proportional to how many cognitive demands are active
        active_scenarios = len(self.state.get("scenario_stack", []))
        base_depth = min(1.0, prospection_input)
        prospection_depth = base_depth * (0.6 + acc_control * 0.4)

        # Branching score: how many futures being simulated
        # High OFC value + high WM + multi-tasking = many branches
        if ofc_state == "rewarding" and wm_load > 0.5:
            branches = min(4, active_scenarios + 1)
        elif acc_control > 0.6:
            branches = min(3, active_scenarios + 1)
        else:
            branches = max(0, active_scenarios - 1)

        # Manage scenario stack
        if wm_active and prospection_depth > 0.5:
            # Add new scenario when depth is sufficient
            if len(self.state["scenario_stack"]) < branches:
                self.state["scenario_stack"].append({
                    "branch_id": len(self.state["scenario_stack"]),
                    "value": round(expected_value, 3),
                    "depth": round(prospection_depth, 3)
                })
        elif prospection_depth < 0.3:
            # Clear scenarios when prospection drops
            self.state["scenario_stack"] = self.state["scenario_stack"][-1:]

        scenario_branches = [
            {"branch": s["branch_id"], "value": s["value"]}
            for s in self.state["scenario_stack"]
        ]

        self.state["prospection_depth"] = round(prospection_depth, 4)
        self.state["branching_score"] = round(len(scenario_branches) / 4.0, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "frontopolar_output": {
                "prospection_depth": round(prospection_depth, 4),
                "branching_score": round(len(scenario_branches) / 4.0, 4),
                "active_branches": len(scenario_branches),
            },
            "scenario_branches": scenario_branches,
            "prospection_depth": round(prospection_depth, 4),
            "branching_score": round(len(scenario_branches) / 4.0, 4),
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

