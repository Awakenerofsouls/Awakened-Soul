"""
Subcortical051CaudateCognitiveLoop.py — Wire 51: Caudate Cognitive Loop

Neural substrate: Caudate nucleus, cognitive associative loop.

The caudate nucleus is the medial component of the dorsal striatum,
forming the upper limb of the caudate-putamen complex (together called
the dorsal striatum). Unlike the putamen (which is somatotopically
organized and strongly motor), the caudate has a more distributed
organization and is critically involved in cognitive functions:
procedural learning, working memory, reinforcement learning, and
goal-directed behavior.

Graybiel 2000 established the chunking architecture: the caudate
contains "critically placed neurons" that learn to chunk sequences
of motor and cognitive events into reusable procedural units. Hikosaka
2019 detailed how the caudate participates in reinforcement learning,
habit formation, and memory-guided behavior in the context of the
oculomotor system.

KEY RESEARCH FINDINGS:
1. Loop architecture. Alexander, DeLong & Strick 1986: the caudate is
   part of five parallel cortico-striato-pallido-thalamo-cortical loops.
   The cognitive loop involves: PFC → caudate → GPi/SNr → VA/VLo
   thalamus → frontal cortex. Each loop processes different domains
   (motor, oculomotor, cognitive, limbic).

2. Head of caudate = working memory. Ozyurt & Turaf 2018: the caudate
   head receives dense input from prefrontal cortex (areas 8, 9, 46)
   and is critically involved in working memory maintenance. Goldman-
   Rakic 1995: "The caudate may be the basal ganglia contribution to
   the neural basis of working memory." Caudate neurons maintain
   spatially selective persistent activity during WM delay periods.

3. Procedural learning and chunking. Graybiel 1998/2000: "Cortico-
   striatal systems process habits and skills by establishing
   procedural chunks." Caudate-dependent learning produces behavior
   that becomes progressively autonomous — the caudate learns to
   chunk action sequences into single behavioral units. Lesions of
   caudate disrupt serial reaction time task (SRTT) learning.

4. Reinforcement vs. habit systems. Yin & Knowlton 2006: "The dorsal
   striatum contains two partially dissociable systems: a dorsal-
   medial (DMS) caudate system for goal-directed actions and a
   dorsal-lateral (DLS) putamen system for habits." Caudate loss
   shifts behavior toward habitual — confirming it supports
   goal-directed instrumental learning.

5. Dopamine modulation. DA from SNc modulates caudate: D1 receptors
   on direct pathway neurons (Go) and D2 receptors on indirect
   pathway neurons (NoGo). Both necessary — D1 for learning positive
   outcomes, D2 for avoiding negative ones. Frank 2005: "Dopamine
   encodes both reward prediction errors and uncertainty signals in
   the caudate." Caudate DA burst encodes positive RPE.

6. Oculomotor function. Hikosaka's group at NIMH mapped caudate
   involvement in saccade generation. caudate neurons fire during
   saccade preparation, encode target selection, and show reward-
   dependent modulation. The caudate→SNr pathway gates which saccade
   targets are selected based on expected value.

7. Aversive processing. Seymour et al. 2012: caudate processes aversive
   prediction errors too — negative RPE signals in dorsomedial caudate
   (DMS). Negative PE activates NoGo indirect pathway → behavioral
   suppression/avoidance.

8. Caudate in OCD and ADHD. The caudate is hyperactive in OCD ( Saxena
   2001) — too much top-down inhibition of motor programs, causing
   perseveration. In ADHD, caudate activity is reduced (Casey 1997) —
   difficulty maintaining the sustained activity needed for working
   memory and behavioral inhibition.

OUTPUTS:
  caudate_cognitive_signal: float 0-1 — overall caudate activation level
  procedural_learning_weight: float 0-1 — strength of chunked procedural traces
  working_memory_link: float 0-1 — caudate-PFC working memory integration

INPUTS:
  PFC_signal: prefrontal cortical input
  reward_signal: positive RPE from SNc/VP
  motor_plan: motor intention from M1/SMA
  behavioral_context: current behavioral state (learning, performing)

CITATIONS:
    PMC10681666 — Paulo DL, Qian H, Subramanian D et al. (2023). Corticostriatal
        Beta Oscillation Changes Associated With Cognitive Function in Parkinson's
        Disease. NPJ Parkinsons Dis.
    PMC5473424 — Anderson JR, Fincham JM, Qin Y et al. (2008). A Central Circuit of
        the Mind. Trends Cogn Sci.

CITATIONS
---------
  - [Grahn 2008, Prog Neurobiol 86:141, caudate cognition]
  - [Seger 2008, Front Neurosci 2:104, caudate learning]
  - [Grahn 2009, Brain Cogn 71:39, caudate goal-directed]

"""

from brain.base_mechanism import BrainMechanism


class CaudateCognitiveLoop(BrainMechanism):
    """
    Caudate nucleus — cognitive/procedural/working memory system.

    Implements the cognitive associative loop of the basal ganglia,
    supporting procedural learning, working memory, and goal-directed
    action selection. Medial (DMS) portion emphasized.
    """

    PROCEDURAL_LEARNING_RATE = 0.04
    WM_LINK_LEARNING_RATE = 0.05
    DA_BOOST_GAIN = 1.5
    CAUDATE_ACTIVATION_RATE = 0.15
    WORKING_MEMORY_DECAY = 0.08

    def __init__(self):
        super().__init__(
            name="CaudateCognitiveLoop",
            human_analog="Caudate nucleus — cognitive associative loop, DMS",
            layer="subcortical",
        )
        self.state.setdefault("caudate_cognitive_signal", 0.0)
        self.state.setdefault("procedural_learning_weight", 0.4)
        self.state.setdefault("working_memory_link", 0.5)
        self.state.setdefault("dopamine_modulation", 0.5)
        self.state.setdefault("WM_activation", 0.0)
        self.state.setdefault("chunk_trace", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        PFC_signal = input_data.get("PFC_signal", 0.5)
        reward_signal = input_data.get("reward_signal", 0.0)
        motor_plan = input_data.get("motor_plan", 0.0)
        behavioral_context = input_data.get("behavioral_context", "learning")
        negative_pe = input_data.get("negative_prediction_error", 0.0)

        # --- Dopamine modulation ---
        # DA boost encodes positive RPE; negative PE suppresses activity
        DA_mod = self.state["dopamine_modulation"]
        if reward_signal > 0.3:
            # Positive RPE — DA burst, caudate activates
            DA_mod += self.DA_BOOST_GAIN * reward_signal * 0.1
        if negative_pe > 0.2:
            # Negative RPE — caudate suppressed via indirect pathway
            DA_mod -= negative_pe * 0.15

        DA_mod = max(0.0, min(1.0, DA_mod))
        self.state["dopamine_modulation"] = DA_mod

        # --- Cognitive signal computation ---
        # Caudate integrates PFC (cognitive), motor plan (procedural), and DA
        PFC_contribution = PFC_signal * 0.4 * (0.5 + DA_mod)
        motor_contribution = motor_plan * 0.25 * self.state["procedural_learning_weight"]
        context_factor = 1.0 if behavioral_context == "learning" else 0.6
        DA_contribution = DA_mod * 0.35

        raw_cognitive = (PFC_contribution + motor_contribution + DA_contribution) * context_factor
        caudate_cognitive_signal = max(0.0, min(1.0, raw_cognitive))

        # --- Working memory integration ---
        # Caudate head maintains WM via persistent activity during delay
        # WM_activation tracks how strongly WM is being maintained
        WM_delta = (PFC_signal - self.state["WM_activation"]) * self.WM_LINK_LEARNING_RATE
        if behavioral_context == "holding":
            WM_delta *= 1.5  # amplified when actively holding WM
        WM_activation = self.state["WM_activation"] + WM_delta
        WM_activation = max(0.0, min(1.0, WM_activation))

        # Decay WM activation when motor action fires
        if motor_plan > 0.6:
            WM_activation *= 0.7

        self.state["WM_activation"] = WM_activation

        # WM link: stronger when PFC and caudate are co-active
        WM_link_delta = self.WM_LINK_LEARNING_RATE * (PFC_signal * caudate_cognitive_signal - self.state["working_memory_link"])
        new_WM_link = self.state["working_memory_link"] + WM_link_delta
        self.state["working_memory_link"] = max(0.2, min(0.95, new_WM_link))

        # --- Procedural learning ---
        # Motor plan + reward = chunk formation (Graybiel 2000)
        if reward_signal > 0.3 and motor_plan > 0.3:
            chunk_increment = self.PROCEDURAL_LEARNING_RATE * reward_signal * motor_plan
            self.state["chunk_trace"] = min(1.0, self.state["chunk_trace"] + chunk_increment)
        else:
            self.state["chunk_trace"] *= 0.95

        # Procedural weight grows with chunk trace
        if self.state["chunk_trace"] > 0.5:
            self.state["procedural_learning_weight"] = min(
                0.9, self.state["procedural_learning_weight"] + 0.02
            )
        else:
            self.state["procedural_learning_weight"] *= 0.995

        self.state["caudate_cognitive_signal"] = caudate_cognitive_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "caudate_cognitive_signal": round(caudate_cognitive_signal, 4),
            "procedural_learning_weight": round(self.state["procedural_learning_weight"], 4),
            "working_memory_link": round(self.state["working_memory_link"], 4),
            "WM_activation": round(WM_activation, 4),
            "dopamine_modulation": round(DA_mod, 4),
            "chunk_trace": round(self.state["chunk_trace"], 4),
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

