"""
EntorhinalLayer3 — EC-III / Temporoammonic Pathway Origin

NEURAL SUBSTRATE
================
Layer III of entorhinal cortex (EC-III) is the principal source of the
temporoammonic (TA) pathway, projecting directly to CA1 pyramidal neurons
(bypassing the trisynaptic circuit DG → CA3 → CA1). EC-III pyramidal
cells in medial entorhinal cortex (MEC-III) carry head-direction and
grid-cell-derived spatial signals; lateral EC-III (LEC-III) carries
non-spatial item/object information.

The TA pathway provides current sensory context to CA1, where it is
compared with CA3-replayed memory traces in stratum lacunosum-moleculare.
This match-mismatch comparison is computationally central to novelty
detection and memory updating (Hasselmo 2005; Brun 2008).

KEY FINDINGS
============
1. EC-III pyramidal neurons project monosynaptically to CA1 stratum
   lacunosum-moleculare via temporoammonic (TA) pathway, parallel to
   trisynaptic circuit — [Steward 1976, J Comp Neurol 167:285, PMID 1270612]
2. TA pathway carries current sensory input to CA1, while CA3 supplies
   stored memory; CA1 acts as match/mismatch comparator —
   [Hasselmo 2005, Hippocampus 15:936, doi:10.1002/hipo.20116]
3. EC-III lesions impair temporal-order memory and disrupt sustained
   firing; layer-III necessary for trace conditioning —
   [Suh 2011, Science 334:1415, doi:10.1126/science.1210125]
4. Medial EC-III shows persistent firing supporting working memory of
   spatial location during delays —
   [Egorov 2002, Nature 420:173, doi:10.1038/nature01171]
5. EC-III TA pathway suppresses Schaffer collateral CA3→CA1 plasticity
   when context mismatch is detected — gating role —
   [Brun 2008, Neuron 57:290, doi:10.1016/j.neuron.2007.11.034]

INPUTS
======
- EntorhinalCortexGridCells.ec_output (or grid_cell_signal)
- LateralEntorhinalCortex.lec_drive (object/item info)
- MedialPrefrontalCortex.pfc_drive (top-down attention)
- HeadDirectionSystem.head_direction_signal (optional)

OUTPUTS
=======
- ec3_drive (0-1)
- temporoammonic_signal (0-1) — direct CA1 input
- match_mismatch_gate (0-1) — gates CA3→CA1
- persistent_firing_signal (0-1) — working memory trace
- ec3_state (str): "ta_active" | "persistent" | "mismatch" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class EntorhinalLayer3(BrainMechanism):
    """EC-III — temporoammonic pathway origin / CA1 direct input."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PERSISTENT_THRESHOLD = 0.55
    MISMATCH_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="EntorhinalLayer3",
            human_analog="Entorhinal cortex layer III (TA pathway)",
            layer="limbic",
        )
        self.state.setdefault("ec3_drive", self.BASELINE)
        self.state.setdefault("temporoammonic_signal", 0.0)
        self.state.setdefault("match_mismatch_gate", 0.0)
        self.state.setdefault("persistent_firing_signal", 0.0)
        self.state.setdefault("ec3_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("persistent_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ec_grid: float, lec: float,
                      pfc: float, head_dir: float) -> float:
        """Composite EC-III drive (Steward 1976 — pyramidal pooled input)."""
        target = (self.BASELINE
                  + ec_grid * 0.35
                  + lec * 0.30
                  + pfc * 0.15
                  + head_dir * 0.10)
        return min(1.0, target)

    def _temporoammonic(self, drive: float, ec_grid: float, lec: float) -> float:
        """Direct CA1 projection (Steward 1976; Brun 2008)."""
        return min(1.0, drive * 0.4 + ec_grid * 0.3 + lec * 0.3)

    def _match_mismatch(self, ta: float, ca3_estimate: float) -> float:
        """Match/mismatch comparator gating (Hasselmo 2005)."""
        # When TA carries strong current input but CA3 retrieval is weak,
        # mismatch is high — novelty signal.
        gap = max(0.0, ta - ca3_estimate)
        return min(1.0, gap * 1.5)

    def _persistent_firing(self, drive: float, prev_trace: float,
                            pfc: float) -> float:
        """MEC-III persistent firing (Egorov 2002)."""
        # Persistent firing is held by mAChR-dependent plateau; decays
        # slowly, boosted by drive + top-down PFC.
        if drive < 0.20:
            return prev_trace * 0.85
        return min(1.0, prev_trace * 0.70 + drive * 0.20 + pfc * 0.15)

    def _classify_state(self, drive: float, ta: float,
                         mismatch: float, persistent: float) -> str:
        if drive < 0.20 and persistent < 0.20:
            return "quiet"
        if mismatch > self.MISMATCH_THRESHOLD:
            return "mismatch"
        if persistent > self.PERSISTENT_THRESHOLD:
            return "persistent"
        if ta > 0.30:
            return "ta_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        if not ec_data:
            ec_data = prior.get("MedialEntorhinalCortex", {})
        ec_grid = float(ec_data.get("ec_output",
                            ec_data.get("grid_cell_signal",
                              ec_data.get("mec_drive", 0.0))))

        lec_data = prior.get("LateralEntorhinalCortex", {})
        lec = float(lec_data.get("lec_drive",
                          lec_data.get("object_signal", 0.0)))

        pfc_data = prior.get("MedialPrefrontalCortex", {})
        if not pfc_data:
            pfc_data = prior.get("PrelimbicCortex", {})
        pfc = float(pfc_data.get("pfc_drive",
                          pfc_data.get("pl_drive", 0.0)))

        head_data = prior.get("HeadDirectionSystem", {})
        head_dir = float(head_data.get("head_direction_signal", 0.0))

        # CA3 estimate for match/mismatch comparison
        ca3_data = prior.get("HippocampalCA3", {})
        if not ca3_data:
            ca3_data = prior.get("HippocampalCA3Dorsal", {})
        ca3_reported = bool(ca3_data)
        ca3_estimate = float(ca3_data.get("ca3_output",
                                  ca3_data.get("ca3_drive", 0.0)))

        target = self._drive_target(ec_grid, lec, pfc, head_dir)
        prev_drive = float(self.state.get("ec3_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        ta_signal = self._temporoammonic(new_drive, ec_grid, lec)
        # If CA3 didn't report a retrieval, the comparator has nothing to
        # measure against — treat as matching (mismatch=0). Hasselmo 2005's
        # match/mismatch role assumes CA3 actually fired; absence of input
        # is not the same as failed recall.
        if not ca3_reported:
            mismatch = 0.0
        else:
            mismatch = self._match_mismatch(ta_signal, ca3_estimate)

        prev_trace = float(self.state.get("persistent_trace", 0.0))
        persistent = self._persistent_firing(new_drive, prev_trace, pfc)

        state = self._classify_state(new_drive, ta_signal, mismatch, persistent)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ec3_drive"] = round(new_drive, 4)
        self.state["temporoammonic_signal"] = round(ta_signal, 4)
        self.state["match_mismatch_gate"] = round(mismatch, 4)
        self.state["persistent_firing_signal"] = round(persistent, 4)
        self.state["persistent_trace"] = round(persistent, 4)
        self.state["ec3_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ec3_drive": round(new_drive, 4),
            "temporoammonic_signal": round(ta_signal, 4),
            "match_mismatch_gate": round(mismatch, 4),
            "persistent_firing_signal": round(persistent, 4),
            "ec3_state": state,
        }

    def _novelty_index(self, recent_states: list) -> float:
        """Mismatch frequency = novelty exposure (Brun 2008)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        miss = sum(1 for s in win if s == "mismatch")
        return miss / max(1, len(win))

    def _working_memory_strength(self) -> float:
        """Persistent trace amplitude (Egorov 2002)."""
        return float(self.state.get("persistent_trace", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ec3_drive", 0.0),
            "ta": self.state.get("temporoammonic_signal", 0.0),
            "mismatch": self.state.get("match_mismatch_gate", 0.0),
            "persistent": self.state.get("persistent_firing_signal", 0.0),
            "state": self.state.get("ec3_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

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
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
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

