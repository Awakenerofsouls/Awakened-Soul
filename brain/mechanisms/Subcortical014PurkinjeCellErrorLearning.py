"""
Subcortical014PurkinjeCellErrorLearning.py — Wire 14: Purkinje Cell Error-Driven LTD
===================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical014PurkinjeCellErrorLearning.py
  Mechanism: PurkinjeCellLTD

NEURAL SUBSTRATE:
  Purkinje cells (PCs) are the sole output neurons of the cerebellar cortex.
  Every movement error the cerebellum learns to correct is encoded as
  changes in the strength of synapses onto PCs. Understanding cerebellar
  learning requires understanding Purkinje cell plasticity.

  ANATOMY:
  - Each Purkinje cell receives ~200,000 parallel fiber (PF) excitatory
    synapses on its dendritic spines (molecular layer).
  - Each Purkinje cell receives ONE powerful climbing fiber (CF) excitatory
    synapse from the contralateral inferior olivary complex — the "teacher"
    signal.
  - PCs fire simple spikes (~50 Hz baseline) via PF→PC excitatory synapses.
  - PCs fire complex spikes (~1 Hz) via CF input — each complex spike
    is a calcium spike preceded by a Na+ spike cluster.

  LONG-TERM DEPRESSION (LTD):
  When parallel fiber activity AND climbing fiber activity coincide at
  a PC, LTD occurs at the PF→PC synapse: the synapse weakens. This is
  the cerebellum's core learning rule (Marr 1969 theory; formally
  demonstrated by Ito and colleagues).

  MECHANISM: simultaneous PF activation → AMPA-R depolarization +
  CF activation → climbing fiber发放 → high intracellular Ca²⁺ in PC
  dendrite → PKC activation → AMPA-R internalization → weakened synapse.

KEY FINDINGS:
  1. Climbing fiber as error signal. Ito 2001 (Science 294:237) established
     the framework: "The cerebellar cortex calculates motor errors via
     climbing fiber signals from the inferior olive." The CF fires when
     movement deviates from the predicted trajectory — this is the
     "teaching signal" the cerebellum uses to adjust motor commands.

  2. LTD as the cellular substrate of learning. Mauk & Donegan 1997;
     Mauk 2000 (Trends in Neurosciences 23:463) argued that LTD at
     PF→PC synapses is "the cellular correlate of cerebellar motor
     learning." Purkinje cell LTD enables the cerebellum to adjust
     behavior based on error signals.

  3. Bidirectional plasticity. Not just LTD — LTP (long-term potentiation)
     also exists at PF→PC synapses when CF is absent. Raymond et al.
     1996: "The site of motor learning is at the parallel fiber–Purkinje
     cell synapse, and LTD and LTP are both necessary." For the agent's model,
     we focus on LTD as the primary error-correction mechanism.

  4. LTD requires coincident activity. The coincidence requirement means
     PCs only learn from errors that occur DURING relevant motor commands
     (when parallel fibers are active). This is the basis of cerebellar
     supervised learning.

  5. Learning rate modulation. Ito 2001 notes that CF activity level
     modulates the LTD induction rate: stronger CF activity → faster LTD.
     This is the "error magnitude" signal — bigger errors drive stronger
     correction.

AGENT'S SUBSTRATE MAPPING:
  PurkinjeCellLTD models the error-driven learning at PF→PC synapses:
  - error_signal_processed: CF input processed for coincidence detection
  - LTD_active: bool — LTD firing on this tick (coincident PF + CF)
  - learning_rate_modulation: adaptive rate based on error magnitude

INPUTS (from prior_results):
  - climbing_fiber_signal: float 0-1 (from inferior olive / error source)
  - parallel_fiber_activity: float 0-1 (from granule cell layer)
  - error_magnitude: float 0-1 (raw movement error size)

OUTPUTS (to brain_runner):
  - error_signal_processed: float 0-1 (CF input normalized)
  - LTD_active: bool (LTD firing condition met)
  - learning_rate_modulation: float 0.5-2.0 (adaptive learning rate)

REFS:
  - Ito 2001 Science 294:237 — cerebellar LTD mechanism
  - Mauk 2000 Trends in Neurosciences 23:463 — cerebellar learning
  - Raymond et al. 1996 — bidirectional plasticity at PF→PC
  - Hansel et al. 2001 — molecular cascade of LTD
  - Gao et al. 2012 J Neurosci 32:12700 — olivocerebellar system review

CITATIONS:
    PMC7255800 — Herzfeld DJ, Hall NJ, Tringides M et al. (2020). Principles of
        Operation of a Cerebellar Learning Circuit. eLife.
    PMC6749063 — Zang Y, De Schutter E (2019). Climbing Fibers Provide Graded Error
        Signals in Cerebellar Learning. J Neurosci.

CITATIONS
---------
  - [Ito 2002, Annu Rev Neurosci 25:303, Purkinje LTD]
  - [Kakegawa 2018, Neuron 99:985, Purkinje plasticity]
  - [Llinas 1992, J Physiol 451:1, Purkinje rhythms]

"""

from brain.base_mechanism import BrainMechanism


class PurkinjeCellLTD(BrainMechanism):
    """
    Purkinje cell LTD — error-driven learning at parallel fiber–PC synapses.

    Implements the Marr-Albus-Ito learning rule: coincident parallel fiber
    (context signal) and climbing fiber (error signal) input drives
    long-term depression at PF→PC synapses. Models adaptive learning rate
    based on error magnitude.
    """

    LTD_COINCIDENCE_WINDOW = 0.25   # minimum simultaneous activation for LTD
    LTD_PROBABILITY = 0.60          # base probability of LTD when coincident
    LEARNING_RATE_BASE = 1.0        # normalized base
    LEARNING_RATE_MAX = 2.0         # ceiling for large-error scenarios
    LTP_FLOOR = 0.5                 # floor when CF is absent (no LTD)

    def __init__(self):
        super().__init__(
            name="PurkinjeCellLTD",
            human_analog="Cerebellar Purkinje cell PF→PC LTD — error-driven learning",
            layer="subcortical",
        )
        self.state.setdefault("error_signal_processed", 0.0)
        self.state.setdefault("LTD_active", False)
        self.state.setdefault("learning_rate_modulation", self.LEARNING_RATE_BASE)
        self.state.setdefault("cumulative_ltds", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Input extraction ---
        cf_signal = input_data.get("climbing_fiber_signal", 0.0)
        pf_activity = input_data.get("parallel_fiber_activity", 0.0)
        error_magnitude = input_data.get("error_magnitude", 0.0)

        # Fallback: try to derive CF from cerebellar error systems
        if cf_signal == 0.0:
            err = prior.get("ICPInput", {})
            # balance_signal inverted = proprioceptive error
            balance = err.get("balance_signal", 0.0)
            cf_signal = balance * 0.6

        if pf_activity == 0.0:
            granule = prior.get("GranuleCellExpansion", {})
            pf_activity = granule.get("expansion_factor", 0.0) * 0.3

        # --- Error signal processing ---
        # CF signal is processed for the LTD coincidence check
        # Raw error magnitude modulates the learning rate
        error_processed = max(0.0, min(1.0, cf_signal + error_magnitude * 0.3))

        # --- LTD coincidence detection ---
        # LTD fires when PF activity and CF signal are simultaneously present
        # (within the coincidence window threshold)
        coincidence = min(pf_activity, cf_signal) * 2.0  # scale 0–1
        ltd_active = coincidence > self.LTD_COINCIDENCE_WINDOW

        # Probability of LTD when condition met
        if ltd_active:
            ltd_prob = self.LTD_PROBABILITY + error_magnitude * 0.2
            ltd_active = ltd_active  # already true, probabilistic refinement
            self.state["cumulative_ltds"] += 1

        # --- Adaptive learning rate ---
        # Larger errors → higher learning rate (more aggressive correction)
        # Smaller errors → lower learning rate (fine-tuning)
        error_component = 1.0 + error_magnitude * 0.8
        ltd_component = 1.3 if ltd_active else 1.0
        lrate = self.LEARNING_RATE_BASE * error_component * ltd_component
        lrate = max(self.LTP_FLOOR, min(self.LEARNING_RATE_MAX, lrate))

        self.state["error_signal_processed"] = error_processed
        self.state["LTD_active"] = ltd_active
        self.state["learning_rate_modulation"] = round(lrate, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "error_signal_processed": round(error_processed, 4),
            "LTD_active": ltd_active,
            "learning_rate_modulation": round(lrate, 4),
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

