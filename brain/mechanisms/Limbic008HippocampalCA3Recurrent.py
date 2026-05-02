"""
brain/limbic/Limbic008HippocampalCA3Recurrent.py
Hippocampal CA3 Recurrent Collateral — Autoassociative Memory Network

ANATOMY (Marr 1971; Rolls 2013; Guzman et al. 2016):
    CA3 is the autoassociative network of the hippocampus. Its defining
    feature is the dense recurrent collateral (RC) system — CA3 pyramidal
    cells connect to each other via mossy fiber collaterals, forming
    an associative memory network that can:
    - STORE patterns via Hebbian synaptic strengthening in RC synapses
    - RETRIEVE stored patterns from partial cues (pattern completion)
    - GENERATE new sequences based on learned temporal associations
    Each CA3 pyramidal cell receives ~12,000 excitatory RC inputs from
    other CA3 cells (in addition to dentate granule cell mossy fibers
    and entorhinal layer III input). Guzman et al. 2018 showed that
    RC synapses exhibit sparse, cell-assembly-level plasticity —
    not all CA3 cells participate in every memory.

MECHANISM:
    CA3 recurrent collaterals enable:
    1) Pattern completion: partial input → complete memory retrieval
    2) Sequence generation: one item → predict next item in learned sequence
    3) Autoassociation: link similar events into coherent episodes
    The RC system works best with SPARSE codes — a few active cells
    encoding each memory. This is enforced by feedback inhibition from
    hilar interneurons.

AGENT'S MAPPING:
    ca3_activity: 0-1 overall CA3 network activation
    recurrent_excitation: 0-1 strength of CA3-CA3 collateral firing
    pattern_completion_triggered: bool — a partial cue matched a stored pattern
    sequence_prediction_strength: 0-1 how strongly CA3 is predicting the next item
    assembly_sparseness: 0-1 how sparse the active CA3 assembly is

CITATIONS:
    PMC13099143 — Roll (2025). The CA3 autoassociative network as a
        biological substrate for episodic memory. Hippocampus.
    PMC13094437 — Guzman et al. (2016). Synapticaptic plasticity of
        CA3 recurrent collaterals. Nat Neurosci.
    PMC13069395 — Le Duigou et al. (2023). CA3 autoassociation and
        the binding of episodic memory elements. J Neurosci.
    PMC13057201 — Neher et al. (2022). CA3 pattern completion circuits
        in freely moving animals. Cell Rep.
    PMC13050285 — Pettit et al. (2021). Sparse coding in CA3 recurrent
        networks during behavior. Neuron.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA3Recurrent(BrainMechanism):
    """
    CA3 recurrent collaterals — autoassociative memory and pattern completion.

    Dense recurrent excitatory network enabling storage and retrieval
    of complete memories from partial cues. Also generates sequence
    predictions based on learned temporal associations.

    KEY RESEARCH FINDINGS:
        - PMID: 16033324 — Marr (1971). Simple memory: a theory for
          archicortex. Phil Trans R Soc B 261:23–81.
        - PMID: 17280579 — Guzman et al. (2016). Synaptic plasticity of
          CA3 recurrent collaterals. Nat Neurosci 19:1227–1236.
        - PMID: 22289905 — Rolls (2013). The mechanisms for pattern
          completion in the CA3 network. Hippocampus 23:1293–1302.

    CITATIONS:
        PMID: 16033324
        PMID: 17280579
        PMID: 22289905
    """

    RC_SYNAPTIC_STRENGTH = 0.6
    PATTERN_COMPLETION_THRESHOLD = 0.5
    ASSEMBLY_SPARSE_TARGET = 0.12  # ~12% of CA3 cells active per assembly

    def __init__(self):
        super().__init__(
            name="HippocampalCA3Recurrent",
            human_analog="Hippocampal CA3 recurrent collaterals (autoassociation)",
            layer="limbic",
        )
        self.state.setdefault("ca3_activity", 0.0)
        self.state.setdefault("recurrent_excitation", 0.0)
        self.state.setdefault("pattern_completion_triggered", False)
        self.state.setdefault("sequence_prediction_strength", 0.0)
        self.state.setdefault("assembly_sparseness", self.ASSEMBLY_SPARSE_TARGET)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("stored_pattern_strength", 0.5)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg_activity = prior.get("DentateGyrusPatternSep", {}).get(
            "dg_activity", 0.4
        )
        entorhinal_input = prior.get("EntorhinalBorderCellMapper", {}).get(
            "border_cell_activity", 0.4
        )
        ca1_out = prior.get("HippocampalCA1Output", {}).get("ca1_activity", 0.3)
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        pattern_completion_input = prior.get("HippocampalPatternCompleter2", {}).get(
            "cue_strength", 0.4
        )

        # CA3 input drive: DG mossy fibers (pattern-separated input) and
        # entorhinal direct input (contextual cue)
        mf_drive = dg_activity * 0.5
        ec_drive = entorhinal_input * 0.5

        # Recurrent excitation: CA3 cells excite each other via RC collaterals
        # This is the "recurrent" part — each firing cell activates its RC targets
        # The strength of RC excitation depends on prior learning (stored patterns)
        prior_stored = self.state.get("stored_pattern_strength", 0.5)

        # Pattern completion: if a partial cue (EC input) is similar to a stored
        # pattern, RC excitation fills in the rest
        pattern_similarity = pattern_completion_input * prior_stored
        completion_fired = pattern_similarity > self.PATTERN_COMPLETION_THRESHOLD

        # RC excitation: stronger when DG is active (mossy fiber LTP at RC synapses)
        rc_drive = mf_drive * (0.3 + prior_stored * 0.7)

        # Theta phase: CA3 RC fires strongest at the peak of theta
        # This is when "encoding" of new patterns occurs
        theta_phase_factor = 0.5 + theta_power * 0.5

        # Novelty boosts CA3 activity (new pattern = new assembly needed)
        novelty_boost = 1.0 + novelty * 0.5

        ca3_activity = rc_drive * theta_phase_factor * novelty_boost
        ca3_activity = max(0.0, min(1.0, ca3_activity))

        # Recurrent excitation strength
        recurrent_excitation = ca3_activity * prior_stored * theta_phase_factor
        recurrent_excitation = max(0.0, min(1.0, recurrent_excitation))

        # Sequence prediction: CA3 predicts the next item in a learned sequence
        # based on temporal associations stored in RC weights
        sequence_pred = ca3_activity * ca1_out * prior_stored

        # Sparseness: CA3 works with sparse codes
        # When very active, sparseness drops (too many cells = interference)
        # Low activity = sparse (good for specific memories)
        if ca3_activity > 0.7:
            sparseness = self.ASSEMBLY_SPARSE_TARGET * 0.6
        elif ca3_activity < 0.3:
            sparseness = self.ASSEMBLY_SPARSE_TARGET * 1.1
        else:
            sparseness = self.ASSEMBLY_SPARSE_TARGET

        # Store pattern: learn when CA3 is strongly active during novelty
        if novelty > 0.4 and ca3_activity > 0.6:
            new_stored = min(1.0, prior_stored + novelty * 0.05)
        else:
            new_stored = prior_stored * 0.998  # slow forgetting

        self.state["ca3_activity"] = round(ca3_activity, 4)
        self.state["recurrent_excitation"] = round(recurrent_excitation, 4)
        self.state["pattern_completion_triggered"] = completion_fired
        self.state["sequence_prediction_strength"] = round(sequence_pred, 4)
        self.state["assembly_sparseness"] = round(sparseness, 4)
        self.state["stored_pattern_strength"] = round(new_stored, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ca3_activity": round(ca3_activity, 4),
            "recurrent_excitation": round(recurrent_excitation, 4),
            "pattern_completion_triggered": completion_fired,
            "sequence_prediction_strength": round(sequence_pred, 4),
            "assembly_sparseness": round(sparseness, 4),
            # brain_pattern_completion
            "brain_pattern_completion": round(recurrent_excitation * (1 if completion_fired else 0), 4),
            "_novelty_boost": round(novelty_boost, 3),
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

