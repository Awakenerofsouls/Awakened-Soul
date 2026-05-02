"""
Subcortical052PutamenSensorimotorAutomation.py — Wire 52: Putamen Automation

Neural substrate: Putamen — sensorimotor loop, habit formation.

The putamen is the lateral component of the dorsal striatum (together
with caudate forming the striatum). It is the somatotopic motor portion
of the striatum — receiving dense input from M1, SMA, and premotor
cortex, and heavily involved in movement execution, skill automation,
and habit formation.

Graybiel 2008 is the landmark paper on habit formation: "Habituation
is a basic process by which organisms come to ignore neutral stimuli
and focus on salient ones, but habit learning in the basal ganglia
is not just a process of ignoring — it is an active process of
building behavioral programs." Yin 2009 established putamen as the
dorsolateral striatum (DLS) — the habit system complementary to
caudate's (DMS) goal-directed system.

KEY RESEARCH FINDINGS:
1. Somatotopic organization. The putamen has a complex somatotopic
   map. Hoover & Strick 1993: motor cortex projects somatotopically
   to putamen — arm representation dorsally, face/head ventrally. 
   Miyachi et al. 1997: different body parts are processed in
   different regions of putamen. The face area is most ventral.

2. Sensorimotor loop (Loop V). Alexander et al. 1986: the fifth
   cortico-striatal loop involves premotor/M1 → putamen → GPi/SNr →
   VA/VLo thalamus → M1/SMA. This is the "motor" loop, distinct
   from the cognitive loop (caudate). The putamen is the entry stage.

3. Habit formation and automation. Yin et al. 2004: "The dorsolateral
   striatum (putamen) is necessary for habit formation." Lesions of
   DLS prevent development of habitual lever pressing in rats even
   after extensive training. Habits become automated via DA-dependent
   plasticity at cortico-striatal synapses in putamen.

4. Chunking of motor sequences. Graybiel 1998: putamen-dependent
   chunking produces "motor chunks" — sequences of elementary movements
   bundled into a single behavioral unit. Once chunked, the sequence
   executes without conscious attention. "The putamen may be the
   locus of habit learning because it chunks sequences." (Graybiel
   2008)

5. Automation and deconnection from cognitive control. Hardwick
   et al. 2019 (meta-analysis, n=164): "Motor skill learning produces
   systematic, domain-specific changes in putamen activity." The
   putamen becomes increasingly active during early skill learning
   (cognitive phase) then becomes less active once habit is formed
   (automatic phase) — the "automatization" process.

6. Beta band oscillations. Brittain et al. 2012: putamen generates
   beta (13-30 Hz) oscillations during automatic movement. Excessive
   beta is a marker of Parkinson's (see STN). In healthy putamen,
   beta power increases during motor automaticity — reflecting
   "motor routine" engagement.

7. Automation strength tracking. The putamen can track how "ready"
   a motor program is for automatic execution. Once procedural 
   learning reaches asymptotic performance, the putamen signals 
   that the program can run with minimal cortical oversight.

8. Putamen in OCD and Tourette. The putamen is implicated in both:
   hyperactivity in OCD (symptom generation), hypoactivity in
   Parkinson's (bradykinesia), and abnormal activity in Tourette's
   (motor tics).

OUTPUTS:
  putamen_sensorimotor_signal: float 0-1 — putamen activation for movement
  habit_formation_weight: float 0-1 — cumulative habit strength
  automation_strength: float 0-1 — readiness for automatic execution

INPUTS:
  motor_cortex_input: M1/SMA activation
  reinforcement_signal: DA reward signal
  skill_repetition: repeated same action → automation
  motor_context: current movement phase (acquisition vs automatic)

CITATIONS:
    PMC2862890 — Ashby FG, Turner BO, Horvitz JC (2010). Cortical and Basal Ganglia
        Contributions to Habit Learning and Automaticity. Trends Cogn Sci.
    PMC8675130 — Alm PA (2021). The Dopamine System and Automatization of Movement
        Sequences: A Review With Relevance for Speech and Stuttering. Front Neurosci.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

from brain.base_mechanism import BrainMechanism


class PutamenSensorimotorAutomation(BrainMechanism):
    """
    Putamen — sensorimotor loop, habit formation, skill automation.

    Implements the motor striatal loop (Loop V), supporting skill
    acquisition, chunking of motor sequences, and automatic execution.
    Dorsolateral striatum (DLS) emphasis.
    """

    MOTOR_ACTIVATION_RATE = 0.18
    HABIT_LEARNING_RATE = 0.03
    AUTOMATION_DECAY = 0.02
    SKILL_THRESHOLD = 0.65
    BETA_BAND_FREQ = 20.0  # Hz — motor automaticity marker

    def __init__(self):
        super().__init__(
            name="PutamenSensorimotorAutomation",
            human_analog="Putamen — sensorimotor striatum (DLS), habit system",
            layer="subcortical",
        )
        self.state.setdefault("putamen_sensorimotor_signal", 0.0)
        self.state.setdefault("habit_formation_weight", 0.3)
        self.state.setdefault("automation_strength", 0.0)
        self.state.setdefault("beta_power", 0.0)
        self.state.setdefault("chunk_strength", 0.0)
        self.state.setdefault("motor_automaticity", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor_cortex_input = input_data.get("motor_cortex_input", 0.4)
        reinforcement_signal = input_data.get("reinforcement_signal", 0.0)
        skill_repetition = input_data.get("skill_repetition", 0.0)
        motor_context = input_data.get("motor_context", "acquisition")
        motor_learning_rate = input_data.get("motor_learning_rate", 0.1)

        # --- Sensorimotor signal ---
        # Putamen fires with motor cortex input, amplified by DA reinforcement
        DA_gain = 1.0 + reinforcement_signal * 0.5
        base_signal = motor_cortex_input * DA_gain * 0.7
        skill_boost = skill_repetition * self.state["habit_formation_weight"] * 0.3
        raw_signal = base_signal + skill_boost
        putamen_sensorimotor_signal = max(0.0, min(1.0, raw_signal))

        # --- Habit formation ---
        # Repetition + reinforcement = habit weight increase (Yin 2009)
        # Habit develops during "acquisition" phase, consolidates in "automatic"
        if motor_context == "acquisition":
            habit_delta = self.HABIT_LEARNING_RATE * skill_repetition * reinforcement_signal
            # Repetition drives habit (Graybiel chunking)
            habit_delta += self.HABIT_LEARNING_RATE * 0.5 * skill_repetition
        else:
            # Automatic phase — habit already formed, stabilize
            habit_delta = 0.0

        new_habit_weight = self.state["habit_formation_weight"] + habit_delta
        self.state["habit_formation_weight"] = max(0.1, min(0.95, new_habit_weight))

        # --- Chunk formation ---
        # When motor pattern repeats, a chunk forms (Graybiel 2008)
        if skill_repetition > 0.6 and motor_cortex_input > 0.5:
            chunk_growth = 0.08 * self.state["habit_formation_weight"]
            self.state["chunk_strength"] = min(1.0, self.state["chunk_strength"] + chunk_growth)
        else:
            self.state["chunk_strength"] *= 0.97

        # --- Automation strength ---
        # Automation increases when: habit is strong + behavior is automatic context
        # Decreases when: motor novelty (new skill learning) disrupts habits
        if motor_context == "automatic" and self.state["chunk_strength"] > self.SKILL_THRESHOLD:
            # Skill ready for automatic execution
            auto_delta = 0.05 * self.state["chunk_strength"]
        else:
            auto_delta = -self.AUTOMATION_DECAY

        # Beta power: increases during automatic motor execution
        beta_phase = (self.state["tick_count"] * self.BETA_BAND_FREQ / 60.0) % 1.0
        beta_oscillation = 0.5 * (1.0 + (1.0 if beta_phase < 0.5 else -1.0))
        new_beta = beta_oscillation * (0.3 + 0.7 * self.state["motor_automaticity"])
        self.state["beta_power"] = max(0.0, min(1.0, new_beta))

        # Automation state
        new_auto = self.state["motor_automaticity"] + auto_delta
        if motor_learning_rate > 0.5:
            # New learning — temporarily disrupts automation
            new_auto -= 0.1
        self.state["motor_automaticity"] = max(0.0, min(1.0, new_auto))
        automation_strength = self.state["motor_automaticity"]

        self.state["putamen_sensorimotor_signal"] = putamen_sensorimotor_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "putamen_sensorimotor_signal": round(putamen_sensorimotor_signal, 4),
            "habit_formation_weight": round(self.state["habit_formation_weight"], 4),
            "automation_strength": round(automation_strength, 4),
            "beta_power": round(self.state["beta_power"], 4),
            "chunk_strength": round(self.state["chunk_strength"], 4),
            "motor_automaticity": round(self.state["motor_automaticity"], 4),
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

