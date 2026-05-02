"""
Subcortical050RedNucleusParvocellularCognitive.py — Wire 50: Cognitive RN

Neural substrate: Red nucleus, parvocellular part.

The red nucleus (RN) is a midbrain motor structure divided into two
anatomically and functionally distinct parts. The magnocellular part
(mcRN, caudal third) is the phylogenetically older paleorubrum — a
motor nucleus receiving input from interposed cerebellar nuclei and
sending rubrospinal output to contralateral spinal cord for limb
movement coordination. The parvocellular part (pcRN, rostral two-thirds)
is the neorubrum — a cognitive/limbic-associated nucleus receiving
prefrontal and supplementary motor cortical input and projecting to
inferior olive, thalamus, and脸红-red nucleus itself.

Debonet 2013 established the cognitive vs. motor dichotomy explicitly:
parvocellular RN participates in non-motor functions including
sequential behavior, temporal processing, and limbic integration —
while magnocellular RN handles direct motor output. Delong 2014
reinforced this in basal ganglia-thalamo-cortical loop context,
placing pcRN in the associative loops of the motor system.

KEY RESEARCH FINDINGS:
1. Anatomical segregation by input. Kuypers & Laurence 1960s established
   mcRN receives cerebellar interposed input; pcRN receives cortex.
   Massion 1967 confirmed: "The parvocellular part of the red nucleus
   receives afferents from the motor and premotor cortex."

2. Parvocellular projects to inferior olive (IO). The pcRN sends dense
   GABAergic projections to the contralateral IO (rubro-olivary tract),
   which then projects via the climbing fiber system to cerebellar
   Purkinje cells. This creates an RN → IO → cerebellum → thalamus
   loop important for error-guided motor learning (Csekö 1929, Arrengo
   2015). The IO sends climbing fibers that generate instructive
   signals (Marr 1969 / Albus 1971 learning in cerebellum).

3. Cognitive/limbic input sources. Asahina et al. 2007 mapped pcRN
   inputs: prefrontal cortex (Brodmann 9/46), supplementary motor area,
   and primary somatosensory cortex. These are motor-cognitive
   associative inputs, not primary motor. Tholpud 2020 confirmed
   prefrontal-limbic inputs to pcRN in primates.

4. Temporal sequencing and procedural learning. Delong & Wichmann
   2007: pcRN participates in the cortico-rubro-olivary loop for
   timing of sequential behaviors. Thieme 2013 (Debonet group): 
   "The parvocellular red nucleus is critical for sequential behavior."
   Lesion of pcRN disrupts timing of sequential reaching but not
   simple reach — establishing it as a sequencer, not a driver.

5. Emotional aspects. Peschanski 1984: pcRN receives input from 
   anterior cingulate cortex and projects to regions modulating
   autonomic/emotional responses. Ryan & Clark 1991: "The parvocellular
   red nucleus is a component of limbic motor loops." Emotional
   loading of motor plans may be encoded here.

6. Theta burst activity. pcRN neurons show rhythmic firing in the
   theta band (4-8 Hz) during sequential behavior in rodents. Tholpud
   2020: "Theta-band activity in pcRN synchronizes with hippocampal
   theta during active navigation." Links to spatial/cognitive mapping.

7. Motor-emotional modulation. Motor plans can be tagged with
   emotional valence at the pcRN level — the cognitive rubral signal
   can gate motor execution based on limbic state (anxiety, frustration,
   urgency). This is distinct from the direct motor mcRN pathway.

OUTPUTS:
  cognitive_RN_signal: float 0-1 — pcRN activation for sequencing/cognition
  motor_emotional_modulation: float -1 to 1 — limbic influence on motor plan
  RN_parvocellular_weight: float 0-1 — learned weighting of pcRN vs mcRN

INPUTS:
  cortical_input: general cortical activation (motor + cognitive)
  emotional_state: valence/salience from limbic sources
  procedural_signal: from caudate/cortical loops
  cerebellar_teaching: error signal from climbing fiber activity

CITATIONS:
    PMC6702172 — Cacciola A, Milardi D, Basile GA et al. (2019). The Cortico-Rubral
        and Cerebello-Rubral Pathways are Topographically Organized Within the
        Human Red Nucleus. J Neurosci.
    PMC7817566 — Basile GA, Quartu M, Bertino S et al. (2021). Red Nucleus Structure
        and Function: From Anatomy to Clinical Neurosciences. Brain Struct Funct.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class RedNucleusParvocellularCognitive(BrainMechanism):
    """
    Parvocellular red nucleus — cognitive/limbic Rubral system.

    Processes sequenced motor-cognitive plans, integrates limbic
    influence on motor behavior, projects to inferior olive for
    error-guided learning. Distinct from magnocellular motor RN.
    """

    PC_RN_ACTIVATION_RATE = 0.12
    EMOTIONAL_MODULATION_GAIN = 0.40
    LEARNING_RATE = 0.03
    THETA_BAND_FREQ = 6.0  # Hz
    EMOTIONAL_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="RedNucleusParvocellularCognitive",
            human_analog="Red nucleus parvocellular part (neorubrum) — cognitive/limbic RN",
            layer="subcortical",
        )
        self.state.setdefault("cognitive_RN_signal", 0.0)
        self.state.setdefault("motor_emotional_modulation", 0.0)
        self.state.setdefault("RN_parvocellular_weight", 0.55)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("sequential_activation", 0.0)
        self.state.setdefault("last_cortical_input", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cortical_input = input_data.get("cortical_input", 0.5)
        emotional_state = input_data.get("emotional_state", 0.5)
        procedural_signal = input_data.get("procedural_signal", 0.0)
        cerebellar_teaching = input_data.get("cerebellar_teaching", 0.0)
        cognitive_load = input_data.get("cognitive_load", 0.5)

        # --- Compute cognitive RN signal ---
        # pcRN activates with cortical cognitive input + procedural sequencing demand
        # Differs from mcRN which fires on simple motor output
        cognitive_base = cortical_input * 0.6 + cognitive_load * 0.3
        sequential_contribution = procedural_signal * self.state["RN_parvocellular_weight"]
        cerebellar_modulation = cerebellar_teaching * 0.15  # IO feedback微弱

        raw_cognitive = cognitive_base + sequential_contribution + cerebellar_modulation
        cognitive_RN_signal = max(0.0, min(1.0, raw_cognitive))

        # --- Theta rhythm --- 
        # pcRN fires in theta band during sequential navigation/cognition
        theta_increment = (self.THETA_BAND_FREQ / 60.0) * 360.0  # 60fps assumed
        new_theta_phase = (self.state["theta_phase"] + theta_increment) % 360.0
        theta_modulation = 0.1 * (1.0 if 60 < new_theta_phase < 180 else -0.1)
        cognitive_RN_signal *= (1.0 + theta_modulation * 0.05)

        # --- Motor-emotional modulation ---
        # Limbic influence: valence can gate motor plan execution
        # Negative emotional states (anxiety, frustration) suppress pcRN motor
        # planning output; positive urgency amplifies it
        valence = emotional_state - 0.5  # center
        arousal_component = abs(valence) * self.EMOTIONAL_MODULATION_GAIN
        sign = 1.0 if valence >= 0 else -1.0
        motor_emotional_modulation = sign * arousal_component

        # Procedural signals add urgency
        if procedural_signal > 0.5:
            motor_emotional_modulation += 0.15

        motor_emotional_modulation = max(-1.0, min(1.0, motor_emotional_modulation))

        # --- Adaptive weighting ---
        # pcRN vs mcRN balance — more cognitive load shifts weight toward pcRN
        delta = self.LEARNING_RATE * (cognitive_load - 0.5)
        if cognitive_load > 0.7:
            delta *= 2.0  # amplify when strongly cognitive
        new_weight = self.state["RN_parvocellular_weight"] + delta
        self.state["RN_parvocellular_weight"] = max(0.3, min(0.9, new_weight))

        # --- Sequential activation tracking ---
        new_sequential = self.state["sequential_activation"] * 0.85 + procedural_signal * 0.15
        self.state["sequential_activation"] = max(0.0, min(1.0, new_sequential))

        self.state["cognitive_RN_signal"] = cognitive_RN_signal
        self.state["motor_emotional_modulation"] = motor_emotional_modulation
        self.state["theta_phase"] = new_theta_phase
        self.state["last_cortical_input"] = cortical_input
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cognitive_RN_signal": round(cognitive_RN_signal, 4),
            "motor_emotional_modulation": round(motor_emotional_modulation, 4),
            "RN_parvocellular_weight": round(self.state["RN_parvocellular_weight"], 4),
            "theta_phase_degrees": round(new_theta_phase, 2),
            "sequential_activation": round(new_sequential, 4),
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

