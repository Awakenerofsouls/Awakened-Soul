"""
Subcortical016CerebellarMolecularLayerIntegration.py — Wire 16: Molecular Layer Integration
=========================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical016CerebellarMolecularLayerIntegration.py
  Mechanism: MolecularLayerIntegration

NEURAL SUBSTRATE:
  The molecular layer is the outermost layer of the cerebellar cortex,
  sitting above the Purkinje cell layer. It is a dense tangle of neuronal
  processes containing:

  - Purkinje cell dendrites (the only output of cerebellar cortex)
  - Parallel fiber axons (granule cell outputs) — run transversely
  - Stellate cells (molecular layer interneurons) — inhibit Purkinje cells
  - Basket cells (molecular layer interneurons) — inhibit Purkinje cell soma
  - Climbing fiber collaterals (modulatory)

  THE BRAITENBERG RECIPROCAL GRID:
  Braitenberg & Atwood 1958 described a striking anatomical feature:
  parallel fibers run perpendicular to Purkinje cell dendrites, forming a
  systematic spatial grid. The angle between them (~90°) is remarkably
  consistent across cerebellar cortex. Braitenberg 1961 proposed this
  creates a " delay line" structure: a PF activated at one point will
  influence PCs sequentially as it travels. This gives the cerebellum a
  built-in temporal integration mechanism.

  TEMPORAL INTEGRATION:
  Because parallel fibers are long (~1mm), and conduction velocity along
  PF is ~0.5 m/s, a single PF can activate a PC up to 2ms AFTER the
  granule cell fires. This creates a temporal window of convergence
  between the mossy-fiber-driven context signal and ongoing PC activity.
  Wang et al. 2014 (Nat Neurosci 17:1188) showed that this temporal
  window is critical for sensorimotor integration: the cerebellum can
  detect temporal sequences and predict what comes NEXT.

  STELLATE AND BASKET CELLS:
  Molecular layer interneurons (stellate cells for distal dendrites,
  basket cells for soma/axon initial segment) provide feedforward
  inhibition to Purkinje cells. This creates a gating mechanism:
  - Sparse stellate/basket activation → disinhibition of PCs → output
  - Dense interneuron firing → PC suppression → output blocked

KEY FINDINGS:
  1. Braitenberg grid temporal computation. The 90° PF–PC geometry means
     PC dendrites sample PF activity at different temporal offsets.
     This makes each PC a temporal pattern detector, not just a rate coder.

  2. Temporal integration window. Wang et al. 2014 demonstrated that
     PCs can detect temporal sequences in mossy fiber input within a
     ~100-200ms window. This allows the cerebellum to predict NEXT sensory
     event based on sequence history.

  3. Plasticity at multiple sites. Molecular layer interneurons (stellate
     cells) also exhibit LTP/LTD at PF→stellate synapses, making them
     plastic modulators of the Purkinje inhibition gate. This adds a
     second plasticity site to the molecular layer.

  4. Output gating via inhibition. The balance between PF direct excitation
     on PCs and interneuron-mediated inhibition determines whether the
     cerebellar nuclei receive PC output. This is the molecular layer's
     gating function.

AGENT'S SUBSTRATE MAPPING:
  MolecularLayerIntegration models the temporal integration and plasticity
  of the molecular layer:
  - temporal_integration_signal: float 0-1 (temporal sequence detection)
  - plasticity_index: float 0-1 (molecular layer plasticity strength)
  - molecular_layer_weight: float 0-1 (net excitatory–inhibitory balance)

INPUTS (from prior_results):
  - parallel_fiber_activity: float 0-1 (from granule cell expansion)
  - temporal_window: float 0-1 (sequence coherence within time window)
  - interneuron_inhibition: float 0-1 (stellate + basket cell activity)
  - stellate_ltp_active: bool (optional — stellate plasticity)

OUTPUTS (to brain_runner):
  - temporal_integration_signal: float 0-1 (sequence detection strength)
  - plasticity_index: float 0-1 (net plasticity level in molecular layer)
  - molecular_layer_weight: float 0-1 (gating output: net PC excitation)

REFS:
  - Braitenberg 1961 — cerebellar cortex architecture (delay lines)
  - Braitenberg & Atwood 1958 — spatial structure of cerebellar cortex
  - Wang et al. 2014 Nat Neurosci 17:1188 — temporal sequence learning
  - Santamaria & Tripp 2007 — stellate cell PF synapse plasticity
  - Sultan & Bower 1998 — quantitative anatomy of PF grid

CITATIONS:
    PMC7255800 — Herzfeld DJ, Hall NJ, Tringides M et al. (2020). Principles of
        Operation of a Cerebellar Learning Circuit. eLife.
    PMC4419603 — Mapelli L, Pagani M, Garrido JA et al. (2015). Integrated Plasticity
        at Inhibitory and Excitatory Synapses in the Cerebellar Circuit. Front Cell Neurosci.

CITATIONS
---------
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]

"""

from brain.base_mechanism import BrainMechanism


class MolecularLayerIntegration(BrainMechanism):
    """
    Cerebellar molecular layer — temporal integration and plasticity hub.

    Models parallel fiber–Purkinje cell temporal integration, interneuron
    gating, and molecular layer plasticity. Computes temporal_integration
    signal (sequence detection), plasticity_index (LTP/LTD level), and
    molecular_layer_weight (net output gating).
    """

    INTEGRATION_WINDOW = 0.15      # baseline temporal window strength
    INHIBITION_WEIGHT = 0.35      # how much interneurons suppress PCs
    STELLATE_PLASTICITY_BOOST = 0.10  # extra plasticity when stellate LTP fires
    DECAY_RATE = 0.06             # per-tick decay of integration signal

    def __init__(self):
        super().__init__(
            name="MolecularLayerIntegration",
            human_analog="Cerebellar molecular layer — PF–PC temporal integration / interneuron gate",
            layer="subcortical",
        )
        self.state.setdefault("temporal_integration_signal", 0.0)
        self.state.setdefault("plasticity_index", 0.0)
        self.state.setdefault("molecular_layer_weight", 0.0)
        self.state.setdefault("sequence_history", [])
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Parallel fiber activity ---
        pf = input_data.get("parallel_fiber_activity", 0.3)
        if pf == 0.3:
            granule = prior.get("GranuleCellExpansion", {})
            pf = granule.get("sparse_code_output", 0.3)

        temporal_window = input_data.get("temporal_window", 0.5)
        interneuron_inhibition = input_data.get("interneuron_inhibition", 0.3)
        stellate_ltp = input_data.get("stellate_ltp_active", False)

        # --- Temporal integration signal ---
        # The integration signal grows when PF activity is temporally
        # coherent (high temporal_window). Decays when inputs are unspecific.
        prev = self.state["temporal_integration_signal"]
        integration_boost = pf * temporal_window * self.INTEGRATION_WINDOW
        new_integration = prev * (1 - self.DECAY_RATE) + integration_boost
        new_integration = max(0.0, min(1.0, new_integration))

        # --- Plasticity index ---
        # Molecular layer plasticity rises with:
        # - PF activity (LTD/LTP induction conditions)
        # - temporal integration (sequence-specific learning)
        # - stellate LTP activity (second plasticity site)
        base_plasticity = pf * (1 + temporal_window)
        stellate_boost = self.STELLATE_PLASTICITY_BOOST if stellate_ltp else 0.0
        plasticity = max(0.0, min(1.0, base_plasticity + stellate_boost))

        # --- Molecular layer weight (gating output) ---
        # Net PC excitation = PF excitation - interneuron inhibition
        excitation = pf * (1 + new_integration)  # temporal boost
        inhibition = interneuron_inhibition * self.INHIBITION_WEIGHT
        weight = excitation - inhibition
        weight = max(-1.0, min(1.0, weight))

        # Normalize to 0-1 (positive range only; negative = PC silenced)
        mol_weight_normalized = max(0.0, (weight + 1.0) / 2.0)

        self.state["temporal_integration_signal"] = round(new_integration, 4)
        self.state["plasticity_index"] = round(plasticity, 4)
        self.state["molecular_layer_weight"] = round(mol_weight_normalized, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "temporal_integration_signal": round(new_integration, 4),
            "plasticity_index": round(plasticity, 4),
            "molecular_layer_weight": round(mol_weight_normalized, 4),
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

