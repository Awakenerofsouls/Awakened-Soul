"""
Subcortical015CerebellarGranuleCellExpansion.py — Wire 15: Granule Cell Expansion Encoder
=======================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical015CerebellarGranuleCellExpansion.py
  Mechanism: GranuleCellExpansion

NEURAL SUBSTRATE:
  Cerebellar granule cells are the most numerous neurons in the entire human
  brain by cell count. Estimates place the human cerebellar granule cell
  population at approximately 3–4 BILLION cells — outnumbering all other
  neuron types combined. They are located in the granular layer of the
  cerebellar cortex, the deepest cortical layer.

  THE EXPANSION RECODER (Marr 1969):
  Each granule cell receives mossy fiber input from a very small receptive
  field (often just a single joint or small skin region). Each granule cell
  then projects its axon upward as a PARALLEL FIBER, which forms excitatory
  synapses on the dendritic trees of Purkinje cells (and other molecular
  layer interneurons) across a wide transverse span (~0.5–1mm).

  This creates a massive EXPANSION RECODER:
  - ~1000 mossy fiber inputs (brainstem/spinal cord)
  - → ~3-4 billion granule cells
  - → ~200,000 parallel fiber synapses per Purkinje cell

  The ratio of input diversity to granule cell population is approximately
  1000:1. This huge expansion allows the cerebellum to form
  highly SPARSE, SPECIFIC codes for sensory-motor contexts.

  ALBUS 1971 refined Marr's theory: granule cells act as a "random
  expansion" that creates a rich combinatorial space for Purkinje cells
  to learn context-specific reactions. Not all Purkinje cells respond to
  the same granule cell inputs.

KEY FINDINGS:
  1. Massive numerical expansion. The cerebellar cortex contains roughly
     80% of all brain neurons (Azevedo et al. 2009, Brain Research Bulletin
     80:127) — mostly granule cells. This means the cerebellum is not
     "small brain" but "granule cell brain."

  2. Sparse coding. Granule cells fire at very low rates (~0.5 Hz) under
     baseline conditions, despite massive excitatory mossy fiber input.
     This is because Golgi cells provide strong inhibition to the granular
     layer. Only highly specific, context-matched inputs overcome this
     inhibition → sparse, specific codes.

  3. Expansion recoder capacity. With 1000:1 expansion, the granule cell
     layer can theoretically represent 2^1000 unique sensory contexts
     (extremely rough). Real capacity is limited by sparsity requirements.

  4. Pattern separation function. Granule cells perform a pattern
     separation operation: similar mossy fiber inputs can produce
     very different granule cell output patterns due to the sparse
     competitive coding. This is analogous to hippocampal dentate gyrus
     pattern separation (Kohonen 1984; McNaughton & Nadel 1990).

  5. Purkinje cell dendritic computation. Each Purkinje cell samples
     ~200,000 parallel fiber synapses. The expansion recoder means each
     Purkinje cell has access to a unique combinatorial subset of the
     granule cell population — enabling context-specific error learning.

AGENT'S SUBSTRATE MAPPING:
  GranuleCellExpansion models the expansion recoder operation:
  - expansion_factor: computed ratio of granule activation vs mossy input
  - encoding_resolution: how finely the granule layer can distinguish inputs
  - sparse_code_output: float 0-1 describing how sparse the current code is

INPUTS (from prior_results):
  - mossy_fiber_input: float 0-1 (aggregate sensory input to granular layer)
  - sensory_receptive_field_diversity: float 0-1 (input variety)
  - golgi_inhibition: float 0-1 (inhibition strength, 0=none, 1=max)

OUTPUTS (to brain_runner):
  - expansion_factor: float (the effective expansion ratio achieved)
  - encoding_resolution: float 0-1 (pattern separation quality)
  - sparse_code_output: float 0-1 (granule cell code sparsity)

REFS:
  - Marr 1969 — cerebellar cortex as expansion recoder (seminal theory)
  - Albus 1971 — refined theory: granule cells as random basis functions
  - Eccles 1973 — anatomical mapping of granule cell layer
  - Sokic et al. 2014 — granule cell sparse coding review
  - Billings et al. 2014 — mossy fiber → granule cell transmission
  - Buzsaki & Mizuseki 2022 — granule cell census (human brain)

CITATIONS:
    PMC3030675 — Mugnaini E, Sekerková G, Martina M (2011). The Unipolar Brush Cell:
        A Remarkable Neuron Finally Receiving Deserved Attention. Brain Res Rev.
    PMC3139583 — Diwakar S, Lombardo P, Solinas S et al. (2011). Local Field Potential
        Modeling Predicts Dense Activation in Cerebellar Granule Cell Clusters. J Neurosci.

CITATIONS
---------
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]

"""

from brain.base_mechanism import BrainMechanism
import random


class GranuleCellExpansion(BrainMechanism):
    """
    Cerebellar granule cell expansion recoder.

    Models the 1000:1 expansion recoder that transforms sparse mossy fiber
    inputs into rich, sparse granule cell population codes. Computes
    expansion_factor, encoding_resolution, and sparse_code_output.
    """

    THEORETICAL_EXPANSIONS = {
        "rat": 50,      # ~50:1 in rodent cerebellum
        "cat": 200,     # ~200:1 in cat
        "human": 1000,  # ~1000:1 in human
    }
    EXPANSION_RATIO = 1000    # target expansion ratio
    SPARSE_CODE_BASE = 0.20   # baseline granule sparsity (~0.5 Hz firing)
    RESOLUTION_DECAY = 0.02  # encoding resolution decay per tick

    def __init__(self):
        super().__init__(
            name="GranuleCellExpansion",
            human_analog="Cerebellar granule cell layer — expansion recoder / pattern separator",
            layer="subcortical",
        )
        self.state.setdefault("expansion_factor", 1.0)
        self.state.setdefault("encoding_resolution", 0.0)
        self.state.setdefault("sparse_code_output", self.SPARSE_CODE_BASE)
        self.state.setdefault("previous_pattern_seed", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Mossy fiber input ---
        mossy_raw = input_data.get("mossy_fiber_input", 0.3)
        receptive_diversity = input_data.get(
            "sensory_receptive_field_diversity", 0.5
        )
        golgi_inhibition = input_data.get("golgi_inhibition", 0.3)

        # Derive from other cerebellar mechanisms if not directly provided
        if mossy_raw == 0.3:
            icp = prior.get("ICPInput", {})
            mossy_raw = (
                icp.get("vestibular_input_strength", 0.0) * 0.4
                + icp.get("proprioceptive_weight", 0.0) * 0.6
            )

        # --- Expansion factor ---
        # The effective expansion ratio depends on mossy input strength
        # and how many receptive fields are active simultaneously.
        # High diversity + high input → large expansion
        input_complexity = mossy_raw * receptive_diversity
        # Map to expansion factor: 1x (minimal) to 1000x (max possible)
        expansion = 1.0 + input_complexity * (self.EXPANSION_RATIO - 1.0)
        expansion = max(1.0, expansion)

        # --- Encoding resolution ---
        # Resolution depends on granule cell population activity diversity.
        # More active granule cells (with low golgi inhibition) = higher resolution.
        # Penalized by low mossy input.
        inhibition_effect = 1.0 - golgi_inhibition * 0.7
        resolution = mossy_raw * inhibition_effect * receptive_diversity
        resolution = max(0.0, min(1.0, resolution))

        # --- Sparse code output ---
        # Granule cells are sparse by default: most are silent even with strong input.
        # Inhibition from Golgi cells ensures sparsity.
        # Sparsity INCREASES with stronger input (fewer specific cells dominate).
        # Sparsity DECREASES (more active) with reduced Golgi inhibition.
        golgi_penalty = 1.0 - golgi_inhibition * 0.5
        raw_sparsity = self.SPARSE_CODE_BASE * golgi_penalty
        input_boost = mossy_raw * 0.3  # strong input recruits more granule cells
        sparsity = raw_sparsity + input_boost
        sparsity = max(0.05, min(1.0, sparsity))

        # --- Pattern separation detection ---
        # Compute a pseudo-pattern seed from current inputs
        pattern_seed = (mossy_raw + receptive_diversity) * 1000
        pattern_changed = (
            abs(pattern_seed - self.state["previous_pattern_seed"]) > 1.0
        )

        self.state["expansion_factor"] = round(expansion, 2)
        self.state["encoding_resolution"] = round(resolution, 4)
        self.state["sparse_code_output"] = round(sparsity, 4)
        self.state["previous_pattern_seed"] = pattern_seed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "expansion_factor": round(expansion, 2),
            "encoding_resolution": round(resolution, 4),
            "sparse_code_output": round(sparsity, 4),
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

