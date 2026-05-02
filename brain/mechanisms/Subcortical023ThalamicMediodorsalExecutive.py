"""
Subcortical023ThalamicMediodorsalExecutive.py — Wire 23: ThalamicMDExecutive

Mediodorsal (MD) thalamic nucleus — PFC executive function relay.

Neural analog: MD is the thalamic station of the prefrontal cortex. It is
a higher-order relay that receives from layer 5 of PFC and projects back to
layer 4 of PFC, forming the cortico-thalamo-cortical loop that supports
working memory, executive control, and decision-making. MD dysfunction
produces profound deficits in PFC-dependent cognition.

ANATOMY (Collins 2018; Parnaudeau 2013):
  - MD subdivisions: medial (limbic, connected to ACC), central (cognitive,
    connected to DLPFC), lateral (connected to lateral PFC)
  - Inputs: PFC layer 5 (all subdivisions), ventral tegmental area (VTA)
    dopaminergic afferents, basal forebrain, raphe nuclei
  - Outputs: widespread to prefrontal cortex (DLPFC, ACC, OFC, LPFC),
    entorhinal cortex
  - MD-PFC loop: the most prominent thalamo-cortical excitatory loop;
    damage to either MD or PFC disrupts this loop completely

COLLINS 2018 — MD IN COGNITIVE CONTROL:
  "Mediodorsal thalamus is essential for prefrontal cortical dynamics
  and cognitive flexibility." Collins et al. showed that:
  1. MD supports PFC persistent firing (maintenance of working memory)
  2. MD synchronizes PFC gamma oscillations during cognitive load
  3. MD disruption causes cognitive inflexibility (cannot update rules)
  4. MD-PFC coupling increases during working memory tasks

PARNAUDEAU 2013 — MD IN FLEXIBILITY:
  Parnaudeau et al. showed that MD inactivation specifically disrupts:
  - Rule learning and set-shifting (not skill learning)
  - Behavioral flexibility when reward contingencies change
  - This implicates MD in "updating" rather than "maintaining"
  - MD is the thalamic trigger for PFC rule-updating

DOPAMINERGIC MODULATION:
  VTA → MD dopaminergic afferents modulate MD-PFC communication.
  This is analogous to SNc → striatum (basal ganglia) but for the
  cognitive loop. MD dopamine enhances signal-to-noise in the MD-PFC loop.

KEY FUNCTIONS:
  1. executive_relay_strength: strength of MD → PFC relay signal
  2. PFC_coordination_signal: MD-mediated coordination across PFC regions
  3. MD_weight: thalamic influence on PFC cortical dynamics

REFS:
- Collins 2018 Nat Neurosci 21:1418-1428 — MD in cognitive control/flexibility
- Parnaudeau et al. 2013 J Neurosci 33:15734-15746 — MD inactivation studies
- Parnaudeau et al. 2015 Front Syst Neurosci — MD cognitive functions review
- Watanabe & Funahashi 2012 Neurosci Biobehav Rev — MD-PFC monkey studies
- Groenewegen 1988 J Comp Neurol — MD anatomy in rat
- Halassa & Sherman 2019 — higher-order relay classification of MD

CITATIONS:
    PMC11881366 — Mochizuki Y, Joji-Nishino A, Emoto K et al. (2025). Distinct Neural
        Responses of Ventromedial Prefrontal Cortex-Projecting Nucleus Reuniens Neurons
        During Aversive Memory Extinction. eNeuro.
    PMC1951790 — Hugues S, Garcia R (2007). Reorganization of Learning-Associated
        Prefrontal Synaptic Plasticity. Eur J Neurosci.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicMediodorsalExecutive(BrainMechanism):
    """
    MD mediodorsal thalamus — prefrontal executive function relay.

    MD is the thalamic hub of PFC executive function. It maintains the
    cortico-thalamo-cortical loop that enables working memory persistence,
    rule representation, and behavioral flexibility. MD receives from PFC
    layer 5 and projects back to PFC layer 4 — the cognitive thalamo-
    cortical loop.

    Inputs: PFC layer 5 efference, VTA dopaminergic modulation,
    rule update signals from ACC, arousal from CM.
    """

    RELAY_GAIN = 0.85
    DOPAMINE_MODULATION = 0.30
    PFC_COORDINATION_GAIN = 0.70
    RULE_UPDATE_BOOST = 0.60
    DECAY_RATE = 0.06

    def __init__(self):
        super().__init__(
            name="ThalamicMediodorsalExecutive",
            human_analog="Mediodorsal (MD) thalamus — PFC executive relay",
            layer="subcortical",
        )
        self.state.setdefault("executive_relay_strength", 0.0)
        self.state.setdefault("PFC_coordination_signal", 0.0)
        self.state.setdefault("MD_weight", 0.0)
        self.state.setdefault("last_rule_update_strength", 0.0)
        self.state.setdefault("dopamine_level", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: PFC layer 5 efference copy (what PFC is processing)
        pfc_efference = prior.get("PrefrontalExecutive", {})
        pfc_signal = pfc_efference.get("executive_relay_strength", 0.0)

        # Source 2: VTA/SNc dopaminergic modulation
        dopamine_signal = prior.get("SubstantiaNigraCompactaCognitive", {})
        dopamine_level = max(0.0, dopamine_signal.get("prediction_error", 0.5))
        # PE > 0 means better than expected = dopaminergic boost
        if dopamine_level > 0.0:
            dopamine_level = min(1.0, dopamine_level + 0.3)

        # Source 3: Rule update signals from ACC (anterior cingulate)
        acc_signal = prior.get("AnteriorCingulateRegulator", {})
        rule_update_strength = acc_signal.get("conflict_signal_strength", 0.0)

        # Source 4: CM arousal (matrix thalamus provides background arousal)
        cm_arousal = prior.get("ThalamicCentromedianIntralaminar", {})
        cm_level = cm_arousal.get("arousal_modulation", 0.0)

        # Source 5: Cognitive prediction error (signals need for rule update)
        cognitive_pe = prior.get("PredictionErrorDrift", {})
        cognitive_surprise = cognitive_pe.get("surprise_magnitude", 0.0)

        # Executive relay: PFC signal amplified by MD
        raw_relay = (
            pfc_signal * self.RELAY_GAIN
            + cm_level * 0.15
            + dopamine_level * self.DOPAMINE_MODULATION * 0.20
        )

        # Rule update boost: when cognitive PE is high, MD amplifies rule update
        if cognitive_surprise > 0.3 or rule_update_strength > 0.3:
            raw_relay += self.RULE_UPDATE_BOOST * max(cognitive_surprise, rule_update_strength)

        executive_relay = max(0.0, min(1.0, raw_relay))

        # PFC coordination signal: MD synchronizes multiple PFC regions
        # High coordination = multiple PFC regions being driven by MD
        coordination = max(
            0.0,
            min(1.0, executive_relay * self.PFC_COORDINATION_GAIN + cm_level * 0.2)
        )

        # MD weight: thalamic influence on PFC cortical dynamics
        # MD fires proportional to its PFC coordination role
        md_weight = max(0.0, min(1.0, executive_relay * 0.8 + dopamine_level * 0.2))

        # Decay on low input
        if pfc_signal < 0.05:
            executive_relay = max(0.0, executive_relay - self.DECAY_RATE)
            coordination = max(0.0, coordination - self.DECAY_RATE)
            md_weight = max(0.0, md_weight - self.DECAY_RATE)

        self.state["executive_relay_strength"] = round(executive_relay, 4)
        self.state["PFC_coordination_signal"] = round(coordination, 4)
        self.state["MD_weight"] = round(md_weight, 4)
        self.state["last_rule_update_strength"] = round(rule_update_strength, 4)
        self.state["dopamine_level"] = round(dopamine_level, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "executive_relay_strength": round(executive_relay, 4),
            "PFC_coordination_signal": round(coordination, 4),
            "MD_weight": round(md_weight, 4),
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

