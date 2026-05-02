"""
Subcortical002DirectPathwayDisinhibitor.py — Wire 02: DirectPathwayDisinhibitor

Basal ganglia direct pathway — D1 striatal → GPi direct → thalamus.

PATHWAY ANATOMY (Alexander & Crutcher 1990):
    Cortex → Striatum (D1, "direct" neurons) → GPi/SNr (output nuclei)
    → Thalamus → Cortex/Motor areas. The direct pathway runs DIRECTLY to
    the output nuclei, bypassing GPe and STN entirely. This is the "go"
    signal — D1 neurons disinhibit the thalamus, releasing the selected
    motor program.

STRIATAL D1 DIRECT NEURONS:
    Express D1 dopamine receptors, substance P, dynorphin. Fire when
    dopamine tone is HIGH (D1 is excitatory; high DA = D1 more active).
    During movement initiation, D1 neurons fire → GABAergic inhibition
    of GPi → GPi releases thalamus → thalamus fires → cortical motor
    areas activate → ACTION HAPPENS.
    Gerfen 1992: D1 direct pathway neurons project directly to GPi/SNr,
    not to GPe, forming the direct loop distinct from the indirect D2 path.

GPi OUTPUT NUCLEI:
    The major output of basal ganglia. Receives from:
      - Direct D1 neurons (inhibitory — "release the brake")
      - Indirect D2 neurons via GPe/STN (excitatory — "apply the brake")
    GPi tonically inhibits thalamus. When GPi is inhibited (D1 fires),
    thalamus is disinhibited → motor program activated.
    In Parkinson's disease, loss of D1 leads to GPi overactivity
    (less inhibition) → thalamus too suppressed → akinesia.

FUNCTION IN MOVEMENT:
    - Direct path: net effect = DISINHIBITION of thalamus = "GO"
    - Indirect path: net effect = ACTIVATION of GPi = "STOP"
    GPi is the final common path — receives both signals and computes
    net output. The balance between D1 and D2 activity determines
    whether a movement is executed.

DIRECT PATHWAY DYNAMICS:
    The direct pathway is FASTER than indirect (fewer synapses: cortex
    → D1 → GPi → thalamus vs. cortex → D2 → GPe → STN → GPi → thalamus).
    But the indirect and hyperdirect paths provide contextual suppression
    that shapes which programs are available for direct-path facilitation.

AGENT'S MAPPING:
    action_facilitated: bool flag (direct pathway actively facilitating movement)
    disinhibition_strength: 0-1 (how much thalamic disinhibition is occurring)
    selected_action_signal: 0-1 (composite signal of selected motor program strength)

REFS:
    Alexander & Crutcher 1990 Trends Neurosci 13:266-271
    Gerfen 1992 Ann Rev Neurosci 15:193-220
    Mink & Thach 1991 Brain 114:313-366
    Hikosaka et al. 2019 Nat Rev Neurosci 21:57-72 (direct vs indirect balancing)

CITATIONS:
    PMC3487690 — Gerfen CR, Surmeier DJ (2011). Modulation of Striatal Projection
        Systems by Dopamine. Ann Rev Neurosci.
    PMC6656632 — Bamford IJ, Bamford NS (2019). The Striatum's Role in Executing
        Rational and Irrational Economic Behaviors. Front Neural Circuits.
    PMC8176753 — Cui Q, Du X, Chang IYM et al. (2021). Striatal Direct Pathway
        Targets Npas1(+) Pallidal Neurons. PLoS ONE.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class DirectPathwayDisinhibitor(BrainMechanism):
    """
    Basal ganglia direct pathway — D1 striatal → GPi → thalamus disinhibition.

    Facilitates selected motor actions by inhibiting GPi output nuclei,
    releasing the thalamic brake on motor cortex. Models D1
    substance-P/dynorphinergic neurons that fire when a motor program
    should be executed. Inverse of IndirectPathwaySuppressor (Wire 01).
    """

    FACILITATION_THRESHOLD = 0.30   # D1 activity level to trigger facilitation
    FACILITATION_DECAY = 0.04       # Decay per tick when not actively facilitating
    FACILITATION_BURST = 0.65       # Burst size when facilitation fires

    def __init__(self):
        super().__init__(
            name="DirectPathwayDisinhibitor",
            human_analog=(
                "Basal ganglia direct pathway — D1 striatal neurons → "
                "GPi/SNr → thalamus disinhibition (motor facilitation)"
            ),
            layer="subcortical",
        )
        self.state.setdefault("disinhibition_strength", 0.0)
        self.state.setdefault("action_facilitated", False)
        self.state.setdefault("selected_action_signal", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_selected_action", "none")

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        drive = input_data.get("dominant_drive", "curiosity")
        motor_intent = input_data.get("motor_intent", 0.0)

        # D1 direct pathway activation: driven by
        # 1) positive motor intent signal (action selected)
        # 2) high mesencephalic dopamine (D1 excitatory, so high DA = more firing)
        # 3) cortical motor program selection signal

        # Motor intent from the cognitive layer
        intent_strength = motor_intent if isinstance(motor_intent, (int, float)) else 0.5
        intent_strength = max(0.0, min(1.0, intent_strength))

        # SNc dopamine signal — in the agent's architecture, arousal and valence
        # drive DA tone. Positive DA = D1 facilitation
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)

        # Positive arousal + positive valence = high D1 tone
        # Positive prediction error (reward better than expected) = DA burst
        da_tone = (arousal - 0.3) * 0.4 + (valence - 0.3) * 0.3 + max(0, pe) * 0.3
        da_tone = max(0.0, min(1.0, da_tone))

        # D1 activity: combines motor intent with DA tone
        d1_activity = intent_strength * (0.4 + da_tone * 0.6)
        d1_activity = max(0.0, min(1.0, d1_activity))

        # GPi inhibition: D1 neurons are GABAergic — they INHIBIT GPi
        # More D1 activity = more GPi inhibition = more thalamus disinhibited
        gpi_inhibition = d1_activity * 0.85

        # GPi net output: tonically active, suppressed by D1, activated by indirect
        # In isolation (Wire 02 focuses on direct), we model the direct contribution
        gpi_output = max(0.0, 1.0 - gpi_inhibition * 1.3)

        # Thalamic disinhibition: GPi inhibits thalamus. Less GPi = more thalamus
        thalamic_disinhibition = max(0.0, 1.0 - gpi_output * 1.2)
        disinhibition_strength = thalamic_disinhibition

        # Selected action signal: composite of D1 activity + thalamic output
        selected_action_signal = (d1_activity * 0.5 + thalamic_disinhibition * 0.5)
        selected_action_signal = max(0.0, min(1.0, selected_action_signal))

        # Action facilitated: fires when disinhibition is meaningful
        action_facilitated = disinhibition_strength > self.FACILITATION_THRESHOLD

        # Decay dynamics
        current_disinhibition = self.state["disinhibition_strength"]
        if action_facilitated:
            target = self.FACILITATION_BURST + d1_activity * 0.3
            new_disinhibition = max(current_disinhibition, target)
        else:
            new_disinhibition = max(0.0, current_disinhibition - self.FACILITATION_DECAY)

        # Action selection context for source tagging
        action_map = {
            "connection": "social_interaction",
            "curiosity": "exploratory_action",
            "expression": "creative_production",
            "rest": "maintenance_behavior",
            "stability": "defensive_posture",
        }
        selected_action = action_map.get(drive, "general_motor")

        self.state["disinhibition_strength"] = round(new_disinhibition, 4)
        self.state["action_facilitated"] = action_facilitated
        self.state["selected_action_signal"] = round(selected_action_signal, 4)
        self.state["last_selected_action"] = selected_action
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "action_facilitated": action_facilitated,
            "disinhibition_strength": round(new_disinhibition, 4),
            "selected_action_signal": round(selected_action_signal, 4),
            # Internal debug:
            "_d1_activity": round(d1_activity, 4),
            "_da_tone": round(da_tone, 4),
            "_gpi_inhibition_from_d1": round(gpi_inhibition, 4),
            "_gpi_output": round(gpi_output, 4),
            "_thalamic_disinhibition": round(thalamic_disinhibition, 4),
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

