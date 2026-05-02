"""
DorsolateralPrefrontalCortex — DLPFC / Working Memory & Executive Control

NEURAL SUBSTRATE
================
The dorsolateral prefrontal cortex (DLPFC) corresponds roughly to
Brodmann areas 9 and 46 on the lateral convexity of the frontal lobe,
flanking the principal sulcus in non-human primates. DLPFC pyramidal
neurons (especially in deep layer III) sustain persistent, stimulus-
selective firing across delay intervals — the canonical neural substrate
of working memory (Funahashi, Bruce, & Goldman-Rakic 1989).

DLPFC sits atop a frontal-parietal control network and exerts top-down
biasing influence on posterior sensory cortex, motor systems, and
subcortical structures. Its outputs implement goal-directed cognitive
control by maintaining task rules, attentional sets, and intermediate
plans (Miller & Cohen 2001).

KEY FINDINGS
============
1. DLPFC neurons exhibit spatially-tuned persistent activity across the
   delay period of an oculomotor delayed-response task — the canonical
   neural correlate of spatial working memory —
   [Funahashi S 1989, J Neurophysiol 61:331, doi:10.1152/jn.1989.61.2.331]
2. Recurrent excitatory microcircuits among layer III pyramidal cells,
   sculpted by GABAergic lateral inhibition, generate spatially-tuned
   delay-period firing —
   [Goldman-Rakic P 1995, Neuron 14:477, doi:10.1016/0896-6273(95)90304-6]
3. Cognitive control arises from active maintenance in PFC of patterns
   that represent goals and bias processing in posterior cortex —
   [Miller E 2001, Annu Rev Neurosci 24:167, doi:10.1146/annurev.neuro.24.1.167]
4. Persistent spiking activity in DLPFC underlies working memory, with
   delay-cell populations representing held information —
   [Constantinidis C 2018, J Neurosci 38:7020, doi:10.1523/JNEUROSCI.2486-17.2018]
5. DLPFC supports executive control by exerting top-down biasing on
   sensory and motor pathways via descending fronto-parietal signals —
   [Curtis C 2003, Trends Cogn Sci 7:415, doi:10.1016/S1364-6613(03)00197-9]

INPUTS
======
- prior_results["FrontoParietalControl"] — control demand signal
- prior_results["Pulvinar"] / sensory cortex — content streams to maintain
- prior_results["AnteriorCingulate"] — conflict / urgency
- prior_results["LocusCoeruleus"] — tonic/phasic NE arousal gain

OUTPUTS
=======
- working_memory_load (0-1)
- delay_activity (0-1)              — persistent firing magnitude
- top_down_bias (0-1)               — descending control signal
- executive_engagement (0-1)
- planning_signal (0-1)
- dlpfc_state (str): "engaged" | "maintenance" | "biasing" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralPrefrontalCortex(BrainMechanism):
    """DLPFC — working memory delay cells, executive control."""

    BASELINE = 0.08
    SMOOTH = 0.18
    ENGAGE_THRESHOLD = 0.30
    MAINT_THRESHOLD = 0.40
    BIAS_THRESHOLD = 0.50
    DECAY = 0.85  # decay of delay activity per tick when no input

    def __init__(self):
        super().__init__(
            name="DorsolateralPrefrontalCortex",
            human_analog="Dorsolateral prefrontal cortex (working memory)",
            layer="neocortical",
        )
        self.state.setdefault("working_memory_load", 0.0)
        self.state.setdefault("delay_activity", 0.0)
        self.state.setdefault("top_down_bias", 0.0)
        self.state.setdefault("executive_engagement", self.BASELINE)
        self.state.setdefault("planning_signal", 0.0)
        self.state.setdefault("dlpfc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("maintained_items", 0)
        self.state.setdefault("tick_count", 0)

    # ----- helper methods --------------------------------------------------

    def _control_demand(self, fp: float, acc: float, urgency: float) -> float:
        """Composite executive demand (Miller & Cohen 2001)."""
        return min(1.0, fp * 0.45 + acc * 0.30 + urgency * 0.25)

    def _delay_activity(self, prev_delay: float, content: float,
                         demand: float, ne: float) -> float:
        """Persistent delay-period firing (Funahashi 1989; Goldman-Rakic 1995).

        Delay activity is sustained by recurrent excitation when content is
        being held; decays slowly otherwise. NE gain (Constantinidis 2018)
        amplifies persistent firing.
        """
        if content < 0.05 and demand < 0.05:
            return prev_delay * self.DECAY
        recurrent = prev_delay * 0.65  # self-sustained recurrent excitation
        new_input = content * 0.40 + demand * 0.25
        gain = 1.0 + 0.3 * ne
        return min(1.0, (recurrent + new_input) * gain)

    def _wm_load(self, delay: float, content: float) -> float:
        """Estimate of cognitive working-memory load."""
        return min(1.0, delay * 0.7 + content * 0.3)

    def _top_down_bias(self, demand: float, delay: float) -> float:
        """Descending biasing signal to posterior cortex."""
        if demand < 0.10 and delay < 0.10:
            return 0.0
        return min(1.0, demand * 0.55 + delay * 0.45)

    def _planning_signal(self, demand: float, wm_load: float,
                         engagement: float) -> float:
        """Multi-step planning emerges when demand + WM are simultaneously high."""
        if engagement < self.ENGAGE_THRESHOLD:
            return 0.0
        return min(1.0, (demand * wm_load) * 1.4 + engagement * 0.2)

    def _classify_state(self, engagement: float, wm_load: float,
                         bias: float) -> str:
        if engagement < self.ENGAGE_THRESHOLD:
            return "quiet"
        if bias > self.BIAS_THRESHOLD:
            return "biasing"
        if wm_load > self.MAINT_THRESHOLD:
            return "maintenance"
        return "engaged"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _count_items(self, content_signals: dict) -> int:
        """Count distinct content streams present above threshold."""
        return sum(1 for v in content_signals.values()
                   if isinstance(v, (int, float)) and v > 0.20)

    # ----- main tick -------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        fp_data = prior.get("FrontoParietalControl", {})
        if not fp_data:
            fp_data = prior.get("PosteriorParietalCortex", {})
        fp = float(fp_data.get("control_demand",
                       fp_data.get("attention_signal", 0.0)))

        acc_data = prior.get("AnteriorCingulate", {})
        if not acc_data:
            acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("conflict_signal",
                        acc_data.get("acc_drive", 0.0)))

        lc_data = prior.get("LocusCoeruleus", {})
        if not lc_data:
            lc_data = prior.get("LocusCoeruleusCore", {})
        ne = float(lc_data.get("ne_release",
                        lc_data.get("ne_signal", 0.0)))

        # content streams to be maintained
        pulv_data = prior.get("Pulvinar", {})
        if not pulv_data:
            pulv_data = prior.get("PulvinarAttentionVisual", {})
        content_visual = float(pulv_data.get("attended_signal",
                              pulv_data.get("pulvinar_drive", 0.0)))

        aud_data = prior.get("AuditoryCortex", {})
        content_aud = float(aud_data.get("auditory_signal", 0.0))

        sem_data = prior.get("TemporalPole", {})
        content_sem = float(sem_data.get("semantic_drive", 0.0))

        urgency = float(prior.get("Urgency", {}).get("urgency", 0.0))

        content = max(content_visual, content_aud, content_sem)
        demand = self._control_demand(fp, acc, urgency)

        prev_delay = float(self.state.get("delay_activity", 0.0))
        new_delay = self._delay_activity(prev_delay, content, demand, ne)

        wm_load = self._wm_load(new_delay, content)
        bias = self._top_down_bias(demand, new_delay)

        prev_eng = float(self.state.get("executive_engagement", self.BASELINE))
        eng_target = min(1.0, self.BASELINE + demand * 0.55 + new_delay * 0.35)
        new_eng = self._smooth(prev_eng, eng_target)

        plan = self._planning_signal(demand, wm_load, new_eng)

        state = self._classify_state(new_eng, wm_load, bias)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        items = self._count_items({
            "visual": content_visual,
            "auditory": content_aud,
            "semantic": content_sem,
        })

        self.state["working_memory_load"] = round(wm_load, 4)
        self.state["delay_activity"] = round(new_delay, 4)
        self.state["top_down_bias"] = round(bias, 4)
        self.state["executive_engagement"] = round(new_eng, 4)
        self.state["planning_signal"] = round(plan, 4)
        self.state["dlpfc_state"] = state
        self.state["recent_states"] = recent
        self.state["maintained_items"] = items
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('planning_signal', 0.0)))
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd

        # extension: track state history if state field exists
        rs = list(self.state.get("recent_states", []))
        cur_state = self.state.get('dlpfc_state', "quiet") if 'dlpfc_state' else "quiet"
        rs.append(cur_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "working_memory_load": round(wm_load, 4),
            "delay_activity": round(new_delay, 4),
            "top_down_bias": round(bias, 4),
            "executive_engagement": round(new_eng, 4),
            "planning_signal": round(plan, 4),
            "dlpfc_state": state,
            "maintained_items": items,
        }

    # ----- introspection ---------------------------------------------------

    def _engagement_fraction(self) -> float:
        """Fraction of recent ticks in non-quiet state."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        return sum(1 for s in recent if s != "quiet") / len(recent)

    def _summary(self) -> dict:
        return {
            "engagement": self.state.get("executive_engagement", 0.0),
            "wm_load": self.state.get("working_memory_load", 0.0),
            "delay": self.state.get("delay_activity", 0.0),
            "items": self.state.get("maintained_items", 0),
            "state": self.state.get("dlpfc_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Fraction of consecutive ticks holding the same state."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i - 1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        """Most-frequent recent state."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('dlpfc_state', "quiet") if 'dlpfc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        """Running mean of primary drive over recent window."""
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('planning_signal', 0.0)) if 'planning_signal' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        """Std-dev proxy of primary drive — tonic-vs-phasic balance."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        """Sustained ceiling — runaway feedback flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        """Sustained collapse — afferent failure flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('planning_signal', 0.0) if 'planning_signal' else 0.0,
            "state": self.state.get('dlpfc_state', "quiet") if 'dlpfc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

