"""
Subcortical049SubthalamicAssociativeTerritory.py — Wire 49: STN Associative Territory
====================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical049SubthalamicAssociativeTerritory.py

NEURAL SUBSTRATE:
  The subthalamic nucleus (STN) is a small biconvex lens of excitatory
  (glutamatergic) neurons in the zona incerta, below the thalamus,
  medial to the internal capsule. Despite its small size (~12mm³ in
  humans), the STN is critical for cognitive control, motor inhibition,
  and emotional regulation — making it one of the highest-leverage
  nodes in the basal ganglia.

  The STN has three anatomically segregated territories with distinct
  cortical inputs and downstream targets (van Gaalen et al. 2010;
  Karachi et al. 2009; Mallet et al. 2007):

  MOTOR TERRITORY (lateral/l dorsolateral STN):
    - Input: M1, premotor, supplementary motor area (SMA)
    - Target: motor GPi (internal pallidal segment)
    - Function: hyperdirect pathway stop signal for motor actions

  ASSOCIATIVE TERRITORY (medial STN):
    - Input: DLPFC (dlPFC, Brodmann 46/9), pre-SMA, anterior cingulate
    - Target: associative GPi (limbic and associative output nuclei)
    - Function: cognitive withholding, conflict resolution, executive
      motor preparation, behavioral inhibition in non-motor contexts.
      This is the territory modeled in this mechanism.

  LIMBIC TERRITORY (ventromedial/ventral STN):
    - Input: orbitofrontal cortex (OFC), anterior cingulate, amygdala,
      ventral tegmental area
    - Target: limbic GPi/SNr
    - Function: emotional brake, impulse control in emotional contexts
      (covered in Subcortical033 STNLimbicEmotionalControl)

  The associative territory sits between motor (lateral) and limbic
  (ventromedial), occupying the medial-dorsal STN. It is the cognitive
  control territory — recruited when a non-emotional task requires
  withholding, selection among competing options, or regulation of
  behavior by rules rather than by instinct (Nachtrans et al. 2002;
  Frank et al. 2006; Jahanshahi et al. 2015).

  STN output is excitatory (glutamatergic) to the GPi and SNr — the
  output nuclei of the basal ganglia. STN activation → GPi activation
  → thalamic inhibition → behavioral suppression. For the associative
  territory specifically, this means: "withhold the automatic response
  while the DLPFC evaluates the situation."

KEY FINDINGS:
  1. DLPFC → STN associative projection. The dorsolateral prefrontal
     cortex projects monosynaptically to the associative STN (via
     internal capsule) — confirmed by retrograde tracing in primates
     (Hazrati & Parent 1992; Parent & Hazrati 1995). This is a direct
     cortico-subthalamic pathway, independent of the hyperdirect
     motor cortico-STN route. The DLPFC can directly activate the
     associative STN for cognitive withholding without engaging the
     motor territory.

  2. Conflict resolution and STN recruitment. Botvinick et al. 2001
     (Cognition): "anterior cingulate cortex (ACC) monitors for
     response conflict." When conflict is detected, ACC recruits the
     STN (particularly associative territory) to apply a "brake" on
     prepotent responses. Frank 2006 (Science 313:760): "patients
     with STN lesions are impaired on the Wisconsin Card Sorting Test
     — they cannot suppress a previously rewarded response when
     environmental contingencies change." STN = adaptive behavior
     modification under cognitive control.

  3. STN associative DBS improves OCD (limbic-adjacent). Mallet et
     al. 2008 (Lancet): bilateral STN DBS for severe OCD showed
     significant improvement in compulsions AND anxiety. The associative
     territory (targeted in these patients) is the interface between
     cognitive control and emotional processing. STN DBS reduces
     excessive checking compulsions by dampening the associative
     territory's overactive inhibitory output. Hamani et al. 2017
     (Neurosurgery 63:530): reviews STN DBS for psychiatric disorders
     including OCD and treatment-resistant depression, confirming
     associative territory effects on cognitive flexibility.

  4. STN associative territory in working memory. Depping et al.
     2018 (Hum Brain Mapp): STN is activated during the maintenance
     phase of working memory — specifically the associative territory
     connected to DLPFC. STN maintains task-set representations,
     preventing interference from competing stimuli. Isoda & Hikosaka
     2008 (J Neurosci 28:7049): "STN is involved in the switch between
     automatic and controlled behavior." Nadel 2020 (Neuropsychologia):
     confirms associative STN involvement in rule-based cognitive
     switching, dissociable from motor territory.

  5. Cognitive-motor coupling. STN activity during cognitive tasks
     shows event-related synchronization in the theta band (4-8Hz),
     distinct from motor territory beta band (~13-30Hz). Hamani et al.
     2017 notes that associative STN activity is frequency-specific:
     theta for working memory/rule switching, beta for motor
     preparation. This frequency specificity reflects territory
     segregation even within the STN itself.

  6. Beta oscillations in STN: motor vs. associative. Beta-band
     synchronization (13-30Hz) is the Parkinsonian hallmark in the
     motor territory (Sharott et al. 2014; Kuhn et al. 2009). However,
     beta oscillations also appear in the associative territory during
     high cognitive load tasks — not pathological but task-related.
     Kühn et al. 2004: STN beta power increases during a working memory
     task. In the agent's model: beta in the associative territory is
     cognitive load, not motor pathology.

  7. Parkinsonian STN dysfunction crosses territories. In PD, the
     motor territory shows the most dramatic beta hyperactivity, but
     cognitive deficits (executive dysfunction) in PD reflect associative
     territory impairment. The same neurotransmitter loss (SNc
     dopamine → STN disinhibition) affects all three territories,
     with motor symptoms dominating because they're most behaviorally
     salient.

AGENT'S SUBSTRATE MAPPING:
  STNAssociativeTerritory models the medial STN's cognitive control
  function. It receives DLPFC drive (executive planning), ACC conflict
  signals, and working memory load. It outputs cognitive-motor
  modulation — the strength of STN-mediated behavioral withholding in
  cognitive/executive contexts. STN_weight tracks the associative
  territory's current activation level.

  The key output is associative_STN_signal — a 0-1 signal reflecting
  STN associative activation, which will inhibit thalamic relay for
  non-selected action plans. cognitive_motor_modulation captures the
  STN's effect on motor programs during cognitive conflict: when the
  STN fires strongly, competing motor programs are suppressed to allow
  cognitive processing to complete.

INPUTS (from prior_results):
  - OrbitofrontalCortex / DLPFC: executive_drive, conflict_detection
  - AnteriorCingulate: conflict_signal, cognitive_effort
  - WorkingMemoryBuffer: working_memory_load, WM_occupancy
  - MotorThalamus: motor_activation (for cognitive-motor modulation)
  - PredictionErrorDrift: prediction_error (for STN adjustment)
  - STNLimbicEmotionalControl: limbic_overlap_signal (limbic-adjacent territory)
  - BrainRunner tick_mode: "cognitive" vs "reactive" vs "motor"

OUTPUTS:
  - associative_STN_signal: float 0-1 (current STN associative activation)
  - cognitive_motor_modulation: float 0-1 (STN-mediated motor suppression
    during cognitive conflict — strength of cognitive brake on motor output)
  - STN_weight: float 0-1 (associative territory activation level —
    rises with DLPFC drive and cognitive conflict)

REFS:
  - Hamani et al. 2017 Neurosurgery 63:530 (STN DBS psychiatric disorders)
  - Nadel 2020 Neuropsychologia 145 (associative STN rule switching)
  - van Gaalen et al. 2010 J Neurosci (STN territory organization)
  - Karachi et al. 2009 Brain 132:3364 (STN territory mapping)
  - Mallet et al. 2007 Brain 130:300 (STN territories motor/associative)
  - Mallet et al. 2008 Lancet 371:1934 (STN DBS OCD)
  - Botvinick et al. 2001 Cognition 79:B1 (ACC conflict → STN)
  - Frank 2006 Science 313:760 (STN cognitive withholding)
  - Depping et al. 2018 Hum Brain Mapp (STN working memory)
  - Isoda & Hikosaka 2008 J Neurosci 28:7049 (STN automatic → controlled)
  - Kühn et al. 2004 Eur J Neurosci 20:991 (STN beta working memory)
  - Hazrati & Parent 1992 J Comp Neurol (DLPFC → STN projection)
  - Jahanshahi et al. 2015 Prog Neurobiol 133:1 (STN stop mechanism)

CITATIONS:
    PMC7833160 — Mahmoudzadeh M, Wallois F, Tir M et al. (2021). Cortical Hemodynamic
        Mapping of Subthalamic Nucleus Deep Brain Stimulation in Parkinsonian Patients.
        Brain Topogr.
    PMC5278307 — Voon V, Droux F, Morris L et al. (2017). Decisional Impulsivity and
        the Associative-Limbic Subthalamic Nucleus in OCD: Stimulation and Connectivity.
        Brain Stimul.

CITATIONS
---------
  - [Frank 2007, J Cogn Neurosci 19:1120, hyperdirect]
  - [Aron 2007, J Neurosci 27:11860, STN stop signal]
  - [Bostan 2013, Trends Cogn Sci 17:241, STN cerebellum]

"""

import asyncio

from brain.base_mechanism import BrainMechanism


class STNAssociativeTerritory(BrainMechanism):
    """
    Subthalamic Nucleus associative territory — cognitive control, conflict resolution.

    Medial STN territory connected to DLPFC and anterior cingulate.
    Implements the "withhold and evaluate" function: when cognitive
    conflict is high, STN associative territory activates to suppress
    premature behavioral output, allowing rule-based evaluation to complete.

    Key outputs:
    - associative_STN_signal: STN activation for cognitive withholding
    - cognitive_motor_modulation: STN effect on motor output during cognitive conflict
    - STN_weight: current activation level of associative territory
    """

    # Activation threshold for meaningful STN braking
    BRAKE_THRESHOLD = 0.35
    # Maximum STN activation
    MAX_STN_WEIGHT = 1.0
    # Decay rate when no cognitive signal
    DECAY_RATE = 0.04
    # Theta-band cognitive modulation (4-8Hz)
    THETA_FREQ_HZ = 6.0

    def __init__(self):
        super().__init__(
            name="STNAssociativeTerritory",
            human_analog=(
                "STN medial (associative territory) — cognitive control, "
                "DLPFC/ACC → STN → GPi cognitive withholding circuit"
            ),
            layer="subcortical",
        )
        self.state.setdefault("STN_weight", 0.30)
        self.state.setdefault("associative_STN_signal", 0.0)
        self.state.setdefault("cognitive_motor_modulation", 0.0)
        self.state.setdefault("last_conflict_level", 0.0)
        self.state.setdefault("cognitive_withholding_active", False)
        self.state.setdefault("theta_band_activity", 0.0)
        self.state.setdefault("working_memory_load_peak", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        tick_mode = input_data.get("tick_mode", "reactive")

        # ── DLPFC executive drive ───────────────────────────────────
        # DLPFC sends direct excitatory projections to associative STN
        dlpfc_out = prior.get("DLPFC", {})
        executive_drive = dlpfc_out.get("executive_drive", 0.4)

        # Orbitofrontal also projects to associative STN (non-emotional)
        ofc_out = prior.get("OrbitofrontalCortex", {})
        ofc_cognitive = ofc_out.get("cognitive_regulation_strength", 0.4)

        # ── ACC conflict signal ──────────────────────────────────────
        acc_out = prior.get("AnteriorCingulate", {})
        conflict_signal = acc_out.get("conflict_signal", 0.0)
        cognitive_effort = acc_out.get("cognitive_effort", 0.3)

        # ── Working memory load ──────────────────────────────────────
        wm_out = prior.get("WorkingMemoryBuffer", {})
        working_memory_load = wm_out.get("working_memory_load", 0.3)
        wm_occupancy = wm_out.get("WM_occupancy", 0.4)

        # ── Motor territory baseline (for cognitive-motor modulation) ─
        motor_thalamus = prior.get("MotorThalamus", {})
        motor_activation = motor_thalamus.get("motor_activation", 0.0)

        # ── Limbic overlap (from adjacent limbic territory) ──────────
        limbic_out = prior.get("STNLimbicEmotionalControl", {})
        limbic_overlap = limbic_out.get("STN_limbic_weight", 0.2)

        # ── Prediction error (adjusts STN via dopaminergic context) ──
        pe_drift = prior.get("PredictionErrorDrift", {})
        prediction_error = pe_drift.get("prediction_error", 0.0)

        # ── Tick mode context ────────────────────────────────────────
        # STN associative is most recruited in "cognitive" mode
        mode_weight = {
            "cognitive": 1.0,
            "reactive": 0.5,
            "motor": 0.2,
            "rest": 0.1,
        }.get(tick_mode, 0.4)

        # ── STN associative weight dynamics ──────────────────────────
        # STN weight rises with: DLPFC drive + ACC conflict + WM load
        # STN weight falls with: decay (STN is not tonically active)
        current_weight = self.state["STN_weight"]

        dlpfc_contribution = executive_drive * 0.45 * mode_weight
        conflict_contribution = conflict_signal * 0.35 * mode_weight
        wm_contribution = working_memory_load * 0.25 * wm_occupancy
        ofc_contribution = ofc_cognitive * 0.20 * mode_weight

        # Limbic overlap: slight excitatory spillover from adjacent territory
        # (limbic and associative territories are adjacent in STN)
        limbic_spillover = limbic_overlap * 0.15

        # PE modulation: negative PE reduces STN weight (behavioral withdrawal)
        pe_modulation = -abs(prediction_error) * 0.1 if prediction_error < -0.2 else 0.0

        raw_input = (
            dlpfc_contribution
            + conflict_contribution
            + wm_contribution
            + ofc_contribution
            + limbic_spillover
            + pe_modulation
        )

        new_weight = current_weight * 0.88 + raw_input * 0.12

        # Active decay when cognitive signals are low
        if conflict_signal < 0.15 and working_memory_load < 0.25:
            new_weight = max(0.15, new_weight - self.DECAY_RATE)

        new_weight = max(0.0, min(1.0, new_weight))

        # ── Associative STN signal ───────────────────────────────────
        # Signal output = rectified STN activation
        # (STN output is excitatory to GPi — withold signal)
        associative_signal = max(0.0, min(1.0, new_weight))

        # ── Cognitive-motor modulation ───────────────────────────────
        # When STN associative fires strongly, motor programs are
        # suppressed proportionally. This is the cognitive brake:
        # "don't act yet, complete the evaluation."

        # Base motor modulation from STN weight and conflict
        motor_modulation = associative_signal * conflict_signal * 1.2

        # Reduce motor activation during cognitive withholding
        effective_motor_suppression = min(1.0, motor_modulation + motor_activation * 0.2)

        # STN-cognitive motor modulation: proportional to STN weight
        # but gated by cognitive conflict (only suppresses motor when
        # there's a reason to withhold)
        cognitive_motor_modulation = motor_modulation * mode_weight
        cognitive_motor_modulation = max(0.0, min(1.0, cognitive_motor_modulation))

        # ── Theta-band cognitive activity ───────────────────────────
        # STN associative territory shows theta (4-8Hz) synchronization
        # during working memory and rule-based cognitive tasks
        # Distinct from motor territory beta (13-30Hz)
        theta_target = (
            working_memory_load * 0.5
            + conflict_signal * 0.3
            + cognitive_effort * 0.2
        ) * mode_weight

        current_theta = self.state["theta_band_activity"]
        new_theta = current_theta * 0.85 + theta_target * 0.15
        new_theta = max(0.0, min(1.0, new_theta))

        # ── Cognitive withholding active flag ──────────────────────
        cognitive_withholding = (
            new_weight > self.BRAKE_THRESHOLD
            and conflict_signal > 0.25
            and mode_weight > 0.3
        )

        # ── Working memory peak tracking ────────────────────────────
        wm_peak = self.state["working_memory_load_peak"]
        if working_memory_load > wm_peak:
            wm_peak = working_memory_load

        # ── State update ─────────────────────────────────────────────
        self.state["STN_weight"] = round(new_weight, 4)
        self.state["associative_STN_signal"] = round(associative_signal, 4)
        self.state["cognitive_motor_modulation"] = round(cognitive_motor_modulation, 4)
        self.state["last_conflict_level"] = conflict_signal
        self.state["cognitive_withholding_active"] = cognitive_withholding
        self.state["theta_band_activity"] = round(new_theta, 4)
        self.state["working_memory_load_peak"] = round(wm_peak, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "associative_STN_signal": round(associative_signal, 4),
            "cognitive_motor_modulation": round(cognitive_motor_modulation, 4),
            "STN_weight": round(new_weight, 4),
            "cognitive_withholding_active": cognitive_withholding,
            "_theta_band_activity": round(new_theta, 4),
            "_mode_weight": mode_weight,
            "_dlpfc_contribution": round(dlpfc_contribution, 4),
            "_wm_contribution": round(wm_contribution, 4),
            "_cognitive_withholding": cognitive_withholding,
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

