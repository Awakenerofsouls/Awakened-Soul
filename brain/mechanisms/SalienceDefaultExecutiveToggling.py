"""
SalienceDefaultExecutiveToggling — Triple-Network Switching Coordinator

NEURAL SUBSTRATE
================
The brain operates on a triple-network architecture (Menon 2011): the
salience network (SN, anchored at anterior insula + dorsal ACC), the
default mode network (DMN, anchored at vmPFC + posterior cingulate +
angular gyrus), and the central executive / frontoparietal network
(CEN, anchored at DLPFC + posterior parietal). At any given moment,
typically ONE network dominates while the others are suppressed.

The salience network monitors interoceptive + external input and
decides which network should currently dominate. When salience detects
a goal-relevant stimulus, it switches control TO the executive network
(focused task processing). When salience is low, control reverts to
the default mode (mind-wandering, autobiographical, self-referential).

Sridharan 2008 used Granger causality on resting-state fMRI to
demonstrate the right anterior insula causally drives transitions
between DMN and CEN — establishing the salience network as the
arbiter of network switching. Goulden 2014 confirmed this with dynamic
causal modeling.

The toggling computation: when salience signal exceeds threshold,
suppress DMN + activate CEN. When salience drops, release CEN
suppression + reactivate DMN.

KEY FINDINGS
============
1. Triple-network model: salience, default mode, central executive
   networks coordinate via switching dynamics — [Menon V 2011, Trends Cogn Sci 15:483, doi:10.1016/j.tics.2011.08.003]
2. Right anterior insula causally drives transitions between DMN and
   CEN; salience network is arbiter — [Sridharan D 2008, PNAS 105:12569, doi:10.1073/pnas.0800005105]
3. Anti-correlated activity: DMN and CEN show reciprocal task-induced
   activation patterns — [Fox MD 2005, PNAS 102:9673, doi:10.1073/pnas.0504136102]
4. Dynamic causal modeling confirms anterior insula initiates DMN-to-CEN
   transitions on cognitively demanding tasks — [Goulden N 2014, Neuroimage 99:180, doi:10.1016/j.neuroimage.2014.05.052]
5. Aberrant network switching is a signature of psychiatric disorders
   including depression, anxiety, schizophrenia — [Menon V 2011, Trends Cogn Sci 15:483, doi:10.1016/j.tics.2011.08.003]

INPUTS (from prior_results)
============================
- InsulaAnterior.aic_drive (salience anchor)
- CingulateAnterior.acc_drive (salience anchor)
- VentromedialPrefrontalCortex.vmpfc_drive (DMN anchor)
- CingulatePosterior.pcc_drive (DMN anchor)
- DorsolateralPrefrontalCortex.dlpfc_drive (CEN anchor)
- PosteriorParietalCortex.ppc_drive (CEN anchor)
- ValenceTagger.valence_intensity (external stimulus salience)

OUTPUTS (to brain_runner enrichment)
=====================================
- salience_network_dominance (0-1)
- default_network_dominance (0-1)
- executive_network_dominance (0-1)
- toggling_signal (0-1) — magnitude of network-switching event
- dominant_network (str): "salience" | "default" | "executive" | "none"
- switching_state (str): "stable" | "switching" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SalienceDefaultExecutiveToggling(BrainMechanism):
    """Triple-network switching coordinator (Menon 2011)."""

    BASELINE = 0.0
    SMOOTH = 0.20
    SWITCH_THRESHOLD = 0.40
    SALIENCE_TRIGGER = 0.35   # threshold above which SN takes over

    def __init__(self):
        super().__init__(
            name="SalienceDefaultExecutiveTogglingVariant",
            human_analog="Triple-network switching coordinator",
            layer="integration",
        )
        self.state.setdefault("salience_network_dominance", 0.0)
        self.state.setdefault("default_network_dominance", 0.0)
        self.state.setdefault("executive_network_dominance", 0.0)
        self.state.setdefault("toggling_signal", 0.0)
        self.state.setdefault("dominant_network", "none")
        self.state.setdefault("switching_state", "quiet")
        self.state.setdefault("recent_dominant", [])
        self.state.setdefault("prev_dominant", "none")
        self.state.setdefault("tick_count", 0)

    def _salience_drive(self, aic: float, acc: float,
                          intensity: float) -> float:
        """Salience network = AIC + dACC + external salience."""
        return min(1.0, aic * 0.45 + acc * 0.35 + intensity * 0.25)

    def _default_drive(self, vmpfc: float, pcc: float,
                         salience: float) -> float:
        """DMN = vmPFC + PCC, suppressed by salience (Fox 2005 anti-correlation)."""
        raw = vmpfc * 0.5 + pcc * 0.5
        suppression = max(0.0, salience - self.SALIENCE_TRIGGER) * 1.5
        return max(0.0, min(1.0, raw - suppression))

    def _executive_drive(self, dlpfc: float, ppc: float,
                           salience: float) -> float:
        """CEN = DLPFC + PPC, ACTIVATED by salience above threshold
        (Sridharan 2008 — SN drives transition INTO CEN)."""
        raw = dlpfc * 0.5 + ppc * 0.5
        # Salience above trigger boosts CEN; below trigger it can still
        # operate but with no SN amplification
        boost = max(0.0, salience - self.SALIENCE_TRIGGER) * 0.6
        return min(1.0, raw + boost)

    def _toggling(self, prev_dom: str, current_dom: str,
                   salience: float) -> float:
        """Magnitude of switching event — high when dominance changes."""
        if prev_dom == current_dom or prev_dom == "none":
            return 0.0
        # Switch event amplitude proportional to salience strength
        return min(1.0, 0.5 + salience * 0.5)

    def _arbitrate(self, salience: float, default: float,
                     executive: float) -> str:
        """Pick dominant network."""
        max_v = max(salience, default, executive)
        if max_v < 0.20:
            return "none"
        if max_v == salience:
            return "salience"
        if max_v == default:
            return "default"
        return "executive"

    def _classify_switching(self, toggling: float, salience: float) -> str:
        """Track whether we're in stable dominance or actively switching."""
        if salience < 0.10 and toggling < 0.10:
            return "quiet"
        if toggling > self.SWITCH_THRESHOLD:
            return "switching"
        return "stable"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        aic_data = prior.get("InsulaAnterior", {})
        aic = float(aic_data.get("aic_drive",
                          aic_data.get("salience_signal", 0.0)))

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive",
                          acc_data.get("conflict_signal", 0.0)))

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive",
                            vmpfc_data.get("default_mode_engagement", 0.0)))

        pcc_data = prior.get("CingulatePosterior", {})
        pcc = float(pcc_data.get("pcc_drive",
                          pcc_data.get("cingulate_drive", 0.0)))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive",
                            dlpfc_data.get("working_memory_signal", 0.0)))

        ppc_data = prior.get("PosteriorParietalCortex", {})
        ppc = float(ppc_data.get("ppc_drive",
                          ppc_data.get("spatial_attention_signal", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        salience_target = self._salience_drive(aic, acc, intensity)
        prev_sal = float(self.state.get("salience_network_dominance", 0.0))
        salience = self._smooth(prev_sal, salience_target)

        default_target = self._default_drive(vmpfc, pcc, salience)
        prev_def = float(self.state.get("default_network_dominance", 0.0))
        default = self._smooth(prev_def, default_target)

        exec_target = self._executive_drive(dlpfc, ppc, salience)
        prev_exec = float(self.state.get("executive_network_dominance", 0.0))
        executive = self._smooth(prev_exec, exec_target)

        current_dom = self._arbitrate(salience, default, executive)
        prev_dom = self.state.get("prev_dominant", "none")
        toggling = self._toggling(prev_dom, current_dom, salience)
        switching = self._classify_switching(toggling, salience)

        recent = list(self.state.get("recent_dominant", []))
        recent.append(current_dom)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["salience_network_dominance"] = round(salience, 4)
        self.state["default_network_dominance"] = round(default, 4)
        self.state["executive_network_dominance"] = round(executive, 4)
        self.state["toggling_signal"] = round(toggling, 4)
        self.state["dominant_network"] = current_dom
        self.state["switching_state"] = switching
        self.state["prev_dominant"] = current_dom
        self.state["recent_dominant"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "salience_network_dominance": round(salience, 4),
            "default_network_dominance": round(default, 4),
            "executive_network_dominance": round(executive, 4),
            "toggling_signal": round(toggling, 4),
            "dominant_network": current_dom,
            "switching_state": switching,
        }

    def _switch_rate(self, recent: list) -> float:
        """How often network dominance changes — high rate = unstable
        triple-network signature (Menon 2011 psychiatric correlate)."""
        if len(recent) < 2:
            return 0.0
        switches = sum(1 for i in range(1, len(recent))
                          if recent[i] != recent[i-1])
        return switches / max(1, len(recent) - 1)

    def _summary(self) -> dict:
        return {
            "salience": self.state.get("salience_network_dominance", 0.0),
            "default": self.state.get("default_network_dominance", 0.0),
            "executive": self.state.get("executive_network_dominance", 0.0),
            "dominant": self.state.get("dominant_network", "none"),
            "switching": self.state.get("switching_state", "quiet"),
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

