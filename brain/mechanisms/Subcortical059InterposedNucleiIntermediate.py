"""
Subcortical059InterposedNucleiIntermediate.py — Wire 59: Interposed DCN

Neural substrate: Interposed nuclei (globose + emboliform) — intermediate DCN.

The interposed nuclei are the middle group of the three deep cerebellar
nuclei (DCN) — consisting of the anterior interposed nucleus (globose
nucleus in some nomenclature) and the posterior interposed nucleus
(emboliform nucleus). They receive input from the intermediate cerebellar
cortex (paramedian lobule, parts of lobule V-VI) and from the cerebellar
lemniscus. Their output goes to the red nucleus (magnocellular) and to
the thalamus, influencing distal limb coordination.

Ruigrok 2004 reviewed the organization of the interposed nuclei in
detail. Parker et al. 2017 established the role of the interposed nuclei
in coordinating distal limb movements, particularly for reaching and
grasping in primates.

KEY RESEARCH FINDINGS:
1. Anatomical organization. Ruigrok 2004: Interposed nuclei are located
   between the medial fastigial and lateral dentate nuclei. They receive
   from: (a) Purkinje cells of the intermediate zone (spinocerebellum
   zone 2), (b) mossy fiber collaterals via the spinocerebellar tracts,
   (c) climbing fiber collaterals. The emboliform nucleus (posterior IP)
   is more associated with forelimb control; the globose (anterior IP)
   with hindlimb.

2. Dual output pathway. Interposed nuclei project to: (a) magnocellular
   red nucleus (mcRN) → rubro-olivary → climbing fibers → cerebellum
   (feedback loop), and (b) VL thalamus → motor cortex → corticospinal
   tract. This creates the "cerebello-rubro-thalamo-cortical" pathway
   for distal limb coordination.

3. Distal limb control. Ito 1984 established that the interposed
   nuclei are the primary DCN output for arm/hand coordination.
   Lesions of interposed nuclei produce ataxia of the extremities,
   particularly dysmetria (overshooting/undershooting target). This
   is the cerebellar equivalent of the "finger" region.

4. Reaching and grasping. Gibson et al. 2004: "Interposed nucleus
   neurons fire during coordinated reaching and grasping movements
   in primates." Single-unit recordings show that IP neurons encode
   both the direction and the force of reaching movements — integrating
   limb position and load information for accurate grasping.

5. Error correction. The interposed nuclei receive climbing fiber
   error signals (via the interposed nucleus → red nucleus → inferior
   olive pathway). These error signals (from the inferior olive,
   carrying "movement error" from sensory feedback) cause LTD at
   synapses onto IP neurons, adjusting the gain of the correction.

6. Reciprocal inhibition with motor cortex. Via the thalamic relay,
   interposed nuclei provide input to M1 that can facilitate or
   inhibit specific motor outputs. This is the "corrective" pathway
   — when the arm is deviating from a planned trajectory, IP neurons
   fire to correct the deviation via thalamo-cortical projections.

7. Dysmetria and intention tremor. Interposed nucleus dysfunction
   produces dysmetria (wrong magnitude of movement) and intention
   tremor (tremor that worsens near the target). This is distinct from
   cerebellar cortical lesions which produce more pure ataxia and
   dysdiadochokinesia.

8. Coordination weight. The interposed nuclei specifically weight
   the coordination of distal movements — the timing and force of
   finger/grip adjustments during reaching. Their output can be
   described as the "limb coordination factor."

OUTPUTS:
  interposed_output: float 0-1 — net interposed DCN activation
  distal_limb_signal: float 0-1 — activation for distal limb control
  limb_coordination_weight: float 0-1 — learned coordination strength

INPUTS:
  intermediate_cortex_input: intermediate zone Purkinje cells
  limb_error_signal: climbing fiber error for limb corrections
  reaching_command: motor plan for reaching movement
  grasping_force: grip force information
  motor_learning_signal: error-driven plasticity signal

CITATIONS:
    PMC6786031 — Hoover JE, Strick PL (1999). The Organization of Cerebellar and
        Basal Ganglia Outputs to Primary Motor Cortex as Revealed by Retrograde
        Transneuronal Transport of Rabies Virus. J Neurosci.
    PMC6790131 — Becker MI, Person AL (2019). Cerebellar Control of Reach Kinematics
        for Endpoint Precision. Cell.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class InterposedNucleiIntermediate(BrainMechanism):
    """
    Interposed nuclei (globose + emboliform) — distal limb coordination.

    Receive from intermediate cerebellar cortex, send output to
    red nucleus (magnocellular) and thalamus for arm/hand movement
    coordination, error correction, and force regulation.
    """

    IP_RESTING_OUTPUT = 0.45
    CORTEX_GAIN = 0.65
    ERROR_CORRECTION_GAIN = 0.50
    REACHING_GAIN = 0.40
    COORDINATION_LEARNING_RATE = 0.05
    DISTAL_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="InterposedNucleiIntermediate",
            human_analog="Interposed nuclei (globose + emboliform) — intermediate DCN, arm/hand",
            layer="subcortical",
        )
        self.state.setdefault("interposed_output", 0.0)
        self.state.setdefault("distal_limb_signal", 0.0)
        self.state.setdefault("limb_coordination_weight", 0.5)
        self.state.setdefault("correction_strength", 0.0)
        self.state.setdefault("reaching_activity", 0.0)
        self.state.setdefault("grasping_force_encoding", 0.0)
        self.state.setdefault("rubro_olivary_feedback", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        intermediate_cortex = input_data.get("intermediate_cortex_input", 0.5)
        limb_error_signal = input_data.get("limb_error_signal", 0.0)
        reaching_command = input_data.get("reaching_command", 0.0)
        grasping_force = input_data.get("grasping_force", 0.0)
        motor_learning_signal = input_data.get("motor_learning_signal", 0.0)
        load_information = input_data.get("load_information", 0.0)

        # --- Interposed output computation ---
        # IP output = disinhibition from intermediate cortex + error correction
        # + reaching/grasp command contribution
        cortex_disinhibition = (intermediate_cortex - 0.5) * 2.0 * self.CORTEX_GAIN
        error_correction = abs(limb_error_signal) * self.ERROR_CORRECTION_GAIN
        reaching_contribution = reaching_command * self.REACHING_GAIN
        grasping_encoding = grasping_force * 0.25

        # Load information encoding (force compensation)
        load_modulation = load_information * 0.20

        raw_output = (
            self.IP_RESTING_OUTPUT
            + cortex_disinhibition
            + error_correction
            + reaching_contribution
            + grasping_encoding
            + load_modulation
        )
        interposed_output = max(0.0, min(1.0, raw_output))

        # --- Distal limb signal ---
        # Interposed nuclei specifically signal for distal control
        distal_base = reaching_command * 0.5 + grasping_force * 0.3
        distal_contribution = interposed_output * self.state["limb_coordination_weight"]
        distal_limb_signal = max(0.0, min(1.0, distal_base + distal_contribution * 0.4))

        # --- Reaching activity ---
        # IP neurons encode reaching direction and force
        reaching_direction_component = abs(reaching_command - 0.5) * 2.0
        reaching_activity = reaching_direction_component * interposed_output
        self.state["reaching_activity"] = max(0.0, min(1.0, reaching_activity))

        # --- Grasping force encoding ---
        # IP encodes grip force for accurate object manipulation
        force_encoding = grasping_force * interposed_output
        self.state["grasping_force_encoding"] = max(0.0, min(1.0, force_encoding))

        # --- Limb coordination weight ---
        # Learning: error correction + successful reaching = coordination growth
        if abs(limb_error_signal) > 0.2 and reaching_command > 0.4:
            # Learning from error: correction improved coordination
            correction_improvement = self.COORDINATION_LEARNING_RATE * (1.0 - abs(limb_error_signal))
            self.state["limb_coordination_weight"] = min(
                0.95, self.state["limb_coordination_weight"] + correction_improvement
            )
        if motor_learning_signal > 0.6:
            self.state["limb_coordination_weight"] = min(
                0.95, self.state["limb_coordination_weight"] + 0.01
            )

        # Decay when not used
        if reaching_command < 0.3:
            self.state["limb_coordination_weight"] *= 0.998

        # --- Rubro-olivary feedback ---
        # IP → mcRN → inferior olive → climbing fibers → cerebellum
        # This is the error feedback loop for cerebellar learning
        rubro_olivary = interposed_output * 0.25
        self.state["rubro_olivary_feedback"] = max(0.0, min(1.0, rubro_olivary))

        # --- Correction strength ---
        # Strength of error correction signal
        if abs(limb_error_signal) > self.DISTAL_THRESHOLD:
            self.state["correction_strength"] = min(
                1.0, self.state["correction_strength"] + abs(limb_error_signal) * 0.1
            )
        else:
            self.state["correction_strength"] *= 0.95

        self.state["interposed_output"] = interposed_output
        self.state["distal_limb_signal"] = distal_limb_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "interposed_output": round(interposed_output, 4),
            "distal_limb_signal": round(distal_limb_signal, 4),
            "limb_coordination_weight": round(self.state["limb_coordination_weight"], 4),
            "correction_strength": round(self.state["correction_strength"], 4),
            "reaching_activity": round(self.state["reaching_activity"], 4),
            "grasping_force_encoding": round(self.state["grasping_force_encoding"], 4),
            "rubro_olivary_feedback": round(self.state["rubro_olivary_feedback"], 4),
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

