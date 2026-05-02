"""
VentrolateralPrefrontalCortex — VLPFC / Inhibition, Language, Semantic Selection

NEURAL SUBSTRATE
================
The ventrolateral prefrontal cortex (VLPFC) occupies the ventral surface
of the lateral frontal lobe, encompassing the inferior frontal gyrus
(IFG) — pars opercularis (BA 44), pars triangularis (BA 45), and pars
orbitalis (BA 47). On the left it includes Broca's area (BA 44/45),
critical for syntactic unification and articulatory planning
(Hagoort 2013). The right inferior frontal cortex (rIFC) plays a
dominant role in motor response inhibition (Aron, Robbins, & Poldrack
2014).

Functionally VLPFC implements controlled retrieval and selection from
semantic memory — biasing competition among activated representations
when context demands a non-dominant response (Thompson-Schill et al.
1997; Badre & Wagner 2002, 2005).

KEY FINDINGS
============
1. Right inferior frontal cortex (rIFC) is causally required for
   stopping motor responses and for braking action; updated theory
   distinguishes total stop and partial pause modes —
   [Aron A 2014, Trends Cogn Sci 18:177, doi:10.1016/j.tics.2013.12.003]
2. Left VLPFC supports dissociable controlled-retrieval and selection
   mechanisms over semantic representations, with anterior VLPFC for
   retrieval and mid-VLPFC for selection —
   [Badre D 2005, Neuron 47:907, doi:10.1016/j.neuron.2005.07.023]
3. Broca's area + adjacent BA 47/6 implements unification operations
   over lexical-syntactic building blocks within the MUC neurobiological
   model of language —
   [Hagoort P 2013, Front Psychol 4:416, doi:10.3389/fpsyg.2013.00416]
4. Left inferior PFC activity reflects selection among competing
   semantic alternatives rather than retrieval per se —
   [Thompson-Schill S 1997, Proc Natl Acad Sci USA 94:14792, doi:10.1073/pnas.94.26.14792]
5. Stop-signal task BOLD response in right IFG / pre-SMA is a robust
   marker of inhibitory control across studies and species —
   [Aron A 2004, Nat Neurosci 6:115, doi:10.1038/nn1003]

INPUTS
======
- prior_results["DorsolateralPrefrontalCortex"] — executive demand
- prior_results["BasalGangliaIndirect"] / STN — stopping circuit
- prior_results["TemporalPole"] — semantic candidates (anterior temporal)
- prior_results["AnteriorCingulate"] — conflict driving selection

OUTPUTS
=======
- inhibition_signal (0-1)            — right-lateralized stop signal
- semantic_selection (0-1)           — left-lateralized selection drive
- broca_unification (0-1)            — language unification load
- response_brake (0-1)               — output to motor system
- vlpfc_engagement (0-1)
- vlpfc_state (str): "stopping" | "selecting" | "speaking" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VentrolateralPrefrontalCortex(BrainMechanism):
    """VLPFC — response inhibition, semantic selection, language unification."""

    BASELINE = 0.06
    SMOOTH = 0.20
    ENGAGE_THRESHOLD = 0.20
    STOP_THRESHOLD = 0.45
    SELECT_THRESHOLD = 0.40
    LANG_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="VentrolateralPrefrontalCortex",
            human_analog="Ventrolateral prefrontal cortex (IFG / Broca)",
            layer="neocortical",
        )
        self.state.setdefault("inhibition_signal", 0.0)
        self.state.setdefault("semantic_selection", 0.0)
        self.state.setdefault("broca_unification", 0.0)
        self.state.setdefault("response_brake", 0.0)
        self.state.setdefault("vlpfc_engagement", self.BASELINE)
        self.state.setdefault("vlpfc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("stop_count", 0)
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _stop_signal(self, stop_cue: float, conflict: float, urgency: float) -> float:
        """Right-lateralized stopping (Aron 2014)."""
        if stop_cue < 0.05 and urgency < 0.10:
            return 0.0
        return min(1.0, stop_cue * 0.55 + urgency * 0.25 + conflict * 0.20)

    def _semantic_selection(self, candidates: float, conflict: float,
                             demand: float) -> float:
        """Left-VLPFC selection among competing alternatives
        (Thompson-Schill 1997; Badre 2005)."""
        # Selection scales with overlap of candidate activation: more
        # candidates above threshold means more competition.
        if candidates < 0.10:
            return 0.0
        competition = candidates * conflict  # multiplicative
        return min(1.0, competition * 1.3 + demand * 0.20)

    def _broca_unification(self, lang_input: float, demand: float) -> float:
        """Broca's area unification load (Hagoort 2013 MUC model)."""
        if lang_input < 0.05:
            return 0.0
        return min(1.0, lang_input * 0.65 + demand * 0.25)

    def _response_brake(self, stop: float, lang_brake: float) -> float:
        """Composite output brake to motor pathways."""
        return min(1.0, max(stop, lang_brake * 0.4))

    def _classify_state(self, eng: float, stop: float, sel: float,
                         lang: float) -> str:
        if eng < self.ENGAGE_THRESHOLD:
            return "quiet"
        # Priority: hard stop > selection > language production
        if stop > self.STOP_THRESHOLD:
            return "stopping"
        if sel > self.SELECT_THRESHOLD:
            return "selecting"
        if lang > self.LANG_THRESHOLD:
            return "speaking"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _engagement_target(self, stop: float, sel: float, lang: float) -> float:
        return min(1.0, self.BASELINE + stop * 0.45
                       + sel * 0.40 + lang * 0.35)

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Stopping inputs
        stop_data = prior.get("StopSignal", {})
        stop_cue = float(stop_data.get("stop_cue", 0.0))
        stn_data = prior.get("SubthalamicNucleus", {})
        if not stn_data:
            stn_data = prior.get("BasalGangliaIndirect", {})
        stn_drive = float(stn_data.get("stn_drive",
                              stn_data.get("indirect_drive", 0.0)))

        # Combine stop_cue and STN as "stop urgency" channel
        stop_input = max(stop_cue, stn_drive * 0.6)

        # Conflict / urgency
        acc_data = prior.get("AnteriorCingulate", {})
        if not acc_data:
            acc_data = prior.get("CingulateAnterior", {})
        conflict = float(acc_data.get("conflict_signal",
                              acc_data.get("acc_drive", 0.0)))
        urgency = float(prior.get("Urgency", {}).get("urgency", 0.0))

        # Executive demand from DLPFC
        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        demand = float(dlpfc_data.get("top_down_bias",
                            dlpfc_data.get("executive_engagement", 0.0)))

        # Semantic candidates from TP / temporal lobe
        tp_data = prior.get("TemporalPole", {})
        semantic_cands = float(tp_data.get("semantic_drive",
                                  tp_data.get("hub_activation", 0.0)))

        # Language input (auditory comprehension or speech production demand)
        lang_data = prior.get("Language", {})
        if not lang_data:
            lang_data = prior.get("WernickeArea", {})
        lang_input = float(lang_data.get("language_signal",
                              lang_data.get("comprehension", 0.0)))
        if lang_input == 0.0:
            # speech-production demand can drive Broca even without input
            lang_input = float(prior.get("SpeechProduction", {}).get(
                "production_demand", 0.0))

        stop = self._stop_signal(stop_input, conflict, urgency)
        sel = self._semantic_selection(semantic_cands, conflict, demand)
        lang = self._broca_unification(lang_input, demand)

        prev_eng = float(self.state.get("vlpfc_engagement", self.BASELINE))
        eng_target = self._engagement_target(stop, sel, lang)
        new_eng = self._smooth(prev_eng, eng_target)

        brake = self._response_brake(stop, lang)
        state = self._classify_state(new_eng, stop, sel, lang)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        stop_count = int(self.state.get("stop_count", 0))
        if state == "stopping":
            stop_count += 1

        self.state["inhibition_signal"] = round(stop, 4)
        self.state["semantic_selection"] = round(sel, 4)
        self.state["broca_unification"] = round(lang, 4)
        self.state["response_brake"] = round(brake, 4)
        self.state["vlpfc_engagement"] = round(new_eng, 4)
        self.state["vlpfc_state"] = state
        self.state["recent_states"] = recent
        self.state["stop_count"] = stop_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('inhibition_signal', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('vlpfc_state', "quiet") if 'vlpfc_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "inhibition_signal": round(stop, 4),
            "semantic_selection": round(sel, 4),
            "broca_unification": round(lang, 4),
            "response_brake": round(brake, 4),
            "vlpfc_engagement": round(new_eng, 4),
            "vlpfc_state": state,
        }

    # ----- introspection ----------------------------------------------------

    def _stop_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("stop_count", 0) / ticks

    def _summary(self) -> dict:
        return {
            "engagement": self.state.get("vlpfc_engagement", 0.0),
            "stop": self.state.get("inhibition_signal", 0.0),
            "select": self.state.get("semantic_selection", 0.0),
            "broca": self.state.get("broca_unification", 0.0),
            "state": self.state.get("vlpfc_state", "quiet"),
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
        if not recent:
            return self.state.get('vlpfc_state', "quiet") if 'vlpfc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('inhibition_signal', 0.0)) if 'inhibition_signal' else 0.0
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
            "drive": self.state.get('inhibition_signal', 0.0) if 'inhibition_signal' else 0.0,
            "state": self.state.get('vlpfc_state', "quiet") if 'vlpfc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

