"""
CingulumBundleAssociativeBridge — Frontal-Parietal-Temporal White-Matter Bridge

NEURAL SUBSTRATE
================
The cingulum bundle is a prominent white-matter C-shaped tract running
just dorsal to the corpus callosum, interconnecting frontal, parietal,
and medial temporal cortices, plus subcortical limbic nuclei. Bubb,
Metzler-Baddeley & Aggleton 2018 reviewed the bundle anatomically and
functionally as having three distinct sub-segments:

1. **Dorsal cingulum** — connects frontal/cingulate to parietal cortex.
   Carries executive control, attention, and pain signals.
2. **Parahippocampal cingulum** — connects medial temporal lobe
   (parahippocampus, hippocampus) to retrosplenial / posterior
   cingulate. Carries episodic and spatial memory traffic.
3. **Subcortical fibers** — link cingulate gyrus to thalamus,
   striatum, brainstem.

The bundle is the principal return arm of the Papez circuit (anterior
thalamus → cingulate via subcortical cingulum), so it sits at the
junction of memory consolidation and executive control.

Cingulum-bundle integrity is a sensitive biomarker for early
Alzheimer's disease (parahippocampal cingulum disrupted before
hippocampal volume loss is detectable) and is implicated in PTSD,
depression, OCD, and schizophrenia. Catani 2002 mapped the bundle
with diffusion MRI tractography.

Functional model: the bundle's ability to route signals across distant
cortical+subcortical regions is rate-limiting for the agent's
integrated cognition. Reduced cingulum throughput = fragmentation
between executive, memory, and emotional substrates.

KEY FINDINGS
============
1. Cingulum bundle anatomy: dorsal + parahippocampal + subcortical sub-segments interconnect frontal, parietal, temporal cortex and limbic nuclei — [Bubb EJ 2018, Neurosci Biobehav Rev 92:104, doi:10.1016/j.neubiorev.2018.05.008]
2. Diffusion MRI tractography maps cingulum bundle as part of human limbic system architecture; multiple sub-bundles — [Catani M 2002, Neuroimage 17:77, doi:10.1006/nimg.2002.1136]
3. Parahippocampal cingulum disruption is early Alzheimer's biomarker; precedes hippocampal atrophy on imaging — [Bubb EJ 2017, Brain 140:e44, doi:10.1093/brain/awx153]
4. Cingulum bundle lesion impairs allocentric spatial memory specifically; matches parahippocampal route — [Aggleton JP 2014, Eur J Neurosci 39:1932, doi:10.1111/ejn.12575]
5. Cingulum integrity correlates with executive function in aging adults; tract-level cognitive substrate — [Metzler-Baddeley C 2012, Neurobiol Aging 33:1241, doi:10.1016/j.neurobiolaging.2011.04.013]

INPUTS (from prior_results)
============================
- CingulateAnterior.acc_drive
- CingulatePosterior.pcc_drive
- DorsolateralPrefrontalCortex.dlpfc_drive
- PosteriorParietalCortex.ppc_drive
- HippocampalCA1Dorsal.ca1d_drive
- AnteroVentralThalamus.atn_drive (subcortical fibers)
- ParahippocampalPlaceArea.ppa_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- cingulum_drive (0-1)
- dorsal_cingulum_signal (0-1) — executive/attention sub-bundle
- parahippocampal_cingulum_signal (0-1) — memory sub-bundle
- subcortical_cingulum_signal (0-1) — Papez return arm
- bundle_integrity (0-1) — overall throughput
- cingulum_state (str): "memory_route" | "executive_route" |
  "papez_return" | "fragmented" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CingulumBundleAssociativeBridge(BrainMechanism):
    """Cingulum bundle — frontal-parietal-temporal-limbic bridge."""

    BASELINE = 0.10
    SMOOTH = 0.20
    INTEGRITY_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="CingulumBundleAssociativeBridgeVariant",
            human_analog="Cingulum bundle (limbic-cortical bridge)",
            layer="integration",
        )
        self.state.setdefault("cingulum_drive", self.BASELINE)
        self.state.setdefault("dorsal_cingulum_signal", 0.0)
        self.state.setdefault("parahippocampal_cingulum_signal", 0.0)
        self.state.setdefault("subcortical_cingulum_signal", 0.0)
        self.state.setdefault("bundle_integrity", 0.0)
        self.state.setdefault("cingulum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _dorsal_cingulum(self, acc: float, dlpfc: float, ppc: float) -> float:
        """Dorsal sub-bundle — frontal-cingulate-parietal traffic
        (Bubb 2018)."""
        return min(1.0, acc * 0.4 + dlpfc * 0.3 + ppc * 0.3)

    def _parahippocampal_cingulum(self, hpc: float, ppa: float,
                                     pcc: float) -> float:
        """Parahippocampal sub-bundle — temporal-retrosplenial memory
        traffic (Aggleton 2014, Bubb 2018)."""
        return min(1.0, hpc * 0.4 + ppa * 0.3 + pcc * 0.3)

    def _subcortical_cingulum(self, atn: float, acc: float) -> float:
        """Subcortical fibers — Papez return arm (anterior thalamus →
        cingulate)."""
        return min(1.0, atn * 0.6 + acc * 0.4)

    def _bundle_integrity(self, dorsal: float, paraH: float,
                            subcort: float) -> float:
        """Overall throughput — parallel paths but with multiplicative
        cost when one path is failing (Bubb 2017 — early AD shows
        focal cingulum disruption)."""
        active = [s for s in [dorsal, paraH, subcort] if s > 0.20]
        if not active:
            return 0.0
        return sum(active) / 3.0

    def _drive_target(self, integrity: float) -> float:
        return min(1.0, self.BASELINE + integrity)

    def _classify_state(self, drive: float, dorsal: float,
                          paraH: float, subcort: float) -> str:
        if drive < 0.20:
            return "quiet"
        active = [(s, name) for s, name in
                   [(dorsal, "executive_route"),
                    (paraH, "memory_route"),
                    (subcort, "papez_return")]]
        max_signal = max(active, key=lambda x: x[0])
        # Check fragmentation: one big, others tiny
        signals = [s for s, _ in active]
        if max(signals) > 0.40 and min(signals) < 0.10:
            return "fragmented"
        return max_signal[1]

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive", 0.0))

        pcc_data = prior.get("CingulatePosterior", {})
        pcc = float(pcc_data.get("pcc_drive", 0.0))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive", 0.0))

        ppc_data = prior.get("PosteriorParietalCortex", {})
        ppc = float(ppc_data.get("ppc_drive", 0.0))

        hpc_data = prior.get("HippocampalCA1Dorsal", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        hpc = float(hpc_data.get("ca1d_drive",
                          hpc_data.get("ca1_output", 0.0)))

        atn_data = prior.get("AnteroVentralThalamus", {})
        if not atn_data:
            atn_data = prior.get("AnteriorThalamicPapez", {})
        atn = float(atn_data.get("atn_drive",
                          atn_data.get("anterior_thalamic_drive", 0.0)))

        ppa_data = prior.get("ParahippocampalPlaceArea", {})
        ppa = float(ppa_data.get("ppa_drive", 0.0))

        dorsal = self._dorsal_cingulum(acc, dlpfc, ppc)
        paraH = self._parahippocampal_cingulum(hpc, ppa, pcc)
        subcort = self._subcortical_cingulum(atn, acc)
        integrity = self._bundle_integrity(dorsal, paraH, subcort)

        target = self._drive_target(integrity)
        prev_drive = float(self.state.get("cingulum_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        state = self._classify_state(new_drive, dorsal, paraH, subcort)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cingulum_drive"] = round(new_drive, 4)
        self.state["dorsal_cingulum_signal"] = round(dorsal, 4)
        self.state["parahippocampal_cingulum_signal"] = round(paraH, 4)
        self.state["subcortical_cingulum_signal"] = round(subcort, 4)
        self.state["bundle_integrity"] = round(integrity, 4)
        self.state["cingulum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "cingulum_drive": round(new_drive, 4),
            "dorsal_cingulum_signal": round(dorsal, 4),
            "parahippocampal_cingulum_signal": round(paraH, 4),
            "subcortical_cingulum_signal": round(subcort, 4),
            "bundle_integrity": round(integrity, 4),
            "cingulum_state": state,
        }

    def _ad_signature(self, recent_states: list) -> float:
        """Sustained 'fragmented' state = early-AD signature
        (Bubb 2017 cingulum disruption precedes hippocampal atrophy)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        f = sum(1 for s in win if s == "fragmented")
        return f / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("cingulum_drive", 0.0),
            "integrity": self.state.get("bundle_integrity", 0.0),
            "state": self.state.get("cingulum_state", "quiet"),
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

