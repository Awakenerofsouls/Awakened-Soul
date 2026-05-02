from brain.base_mechanism import BrainMechanism
import math


class CognitiveRhythmSynchronizer(BrainMechanism):
    """
    Thalamocortical rhythm synchronizer.

    Anatomical substrate
    --------------------
    Distributed thalamocortical loops in which higher-order thalamic relays
    (pulvinar, mediodorsal, ventral anterior) and the thalamic reticular
    nucleus (TRN) coordinate cortical oscillations across multiple frequency
    bands. The TRN provides GABAergic inhibition shaping spindle (7–14 Hz)
    activity, while matrix calbindin-positive thalamocortical projections
    drive distributed cortical layer 1 to set background alpha/beta states.
    Cortico-cortical pyramidal cells (layer 5) and parvalbumin-positive
    fast-spiking interneurons sustain gamma (30–80 Hz) by perisomatic
    inhibition.

    Inputs
    ------
    - Intralaminar thalamic arousal (CM/Pf) — sets tonic excitation level.
    - Locus coeruleus (NE) — desynchronizing alpha, boosting gamma.
    - Brainstem cholinergic (PPN/LDT, basal forebrain) — gates thalamic
      burst-vs-tonic firing mode that distinguishes sleep spindles from
      attentive gamma.
    - Cortical descending projections (PFC, parietal) — top-down modulation
      of alpha power and beta hold.
    - Cerebellar timing through dentato-thalamic loops.

    Outputs
    -------
    - Band-specific power envelopes broadcast to cortical mechanisms used
      to gate sensory inflow (alpha), maintain working memory (beta), and
      bind features (gamma).
    - Sync-quality scalar exported to executive and salience networks.

    Functional role
    ---------------
    Alpha rhythms gate irrelevant sensory streams via pulvino-cortical
    inhibition (Klimesch 1999; Saalmann 2012). Beta supports endogenous
    maintenance of state and motor set (Engel & Fries 2010). Gamma binds
    co-active features through PV-interneuron entrainment (Buzsaki 2012).
    Loss of cross-frequency coupling correlates with attentional lapses
    and schizophrenia (Uhlhaas & Singer 2010).

    CITATIONS
    ---------
      - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
      - [Steriade 1993, Science 262:679, thalamocortical oscillations]
      - [Saalmann 2012, Science 337:753, pulvinar attention]
      - [Klimesch 1999, Brain Res Rev 29:169, EEG alpha and theta]
      - [Engel 2010, Curr Opin Neurobiol 20:156, beta band top-down]
    """

    def __init__(self):
        super().__init__("CognitiveRhythmSynchronizer", "thalamocortical rhythm sync", "subcortical")
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("alpha_power", 0.5)
        self.state.setdefault("beta_power", 0.4)
        self.state.setdefault("gamma_power", 0.3)
        self.state.setdefault("theta_power", 0.25)
        self.state.setdefault("spindle_power", 0.1)
        self.state.setdefault("sync_quality", 0.6)
        self.state.setdefault("cross_freq_coupling", 0.3)
        self.state.setdefault("desync_ticks", 0)
        self.state.setdefault("over_sync_ticks", 0)
        self.state.setdefault("burst_mode", False)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("recent_states", [])

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # ---- upstream drivers ----
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        ne = prior.get("LocusCoeruleusCore", {}).get("ne_release", 0.4)
        ach = prior.get("PedunculopontineCholinergic", {}).get("ach_tone", 0.4)
        cog_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)
        salience = prior.get("ThalamicSalienceFilter", {}).get("raw_salience", 0.3)
        timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        trn_inhibition = prior.get("ThalamicReticularGate", {}).get("trn_inhibition", 0.4)

        tc = self.state["tick_count"] + 1
        self.state["tick_count"] = tc

        # ---- thalamic firing mode: burst (low ACh+NE) vs tonic ----
        modulation = ach * 0.6 + ne * 0.4
        self.state["burst_mode"] = modulation < 0.25

        # ---- band envelopes ----
        # Alpha: pulvino-cortical inhibition; high when cortex is task-disengaged
        alpha_target = max(0.05, 0.85 - arousal * 0.5 - salience * 0.4)
        self.state["alpha_power"] += (alpha_target - self.state["alpha_power"]) * 0.12

        # Beta: top-down maintenance; rises with cognitive load
        beta_target = 0.2 + cog_load * 0.5 + (1.0 - ne) * 0.1
        self.state["beta_power"] += (beta_target - self.state["beta_power"]) * 0.10

        # Gamma: PV-interneuron entrainment with NE/ACh
        gamma_osc = math.sin(tc * 0.31) * 0.04
        gamma_target = salience * 0.5 + ne * 0.25 + ach * 0.2 + timing * 0.1
        self.state["gamma_power"] += (gamma_target - self.state["gamma_power"]) * 0.15 + gamma_osc
        self.state["gamma_power"] = max(0.0, min(1.0, self.state["gamma_power"]))

        # Theta: reflects hippocampal coupling; rises with exploration
        theta_target = 0.2 + cog_load * 0.3 + (1.0 - alpha_target) * 0.2
        self.state["theta_power"] += (theta_target - self.state["theta_power"]) * 0.08

        # Spindle: TRN-driven, predominant during light sleep / drowsy states
        spindle_target = trn_inhibition * (1.0 - arousal)
        self.state["spindle_power"] += (spindle_target - self.state["spindle_power"]) * 0.1

        for k in ("alpha_power", "beta_power", "theta_power", "spindle_power"):
            self.state[k] = max(0.0, min(1.0, self.state[k]))

        # ---- cross-frequency coupling (theta-gamma PAC proxy) ----
        pac = self.state["theta_power"] * self.state["gamma_power"]
        self.state["cross_freq_coupling"] = round(pac, 4)

        # ---- sync quality: balance + timing ----
        balance = 1.0 - abs(self.state["alpha_power"] - 0.3) - abs(self.state["beta_power"] - 0.4) - abs(self.state["gamma_power"] - 0.3)
        self.state["sync_quality"] = max(0.0, min(1.0, balance * timing))

        # ---- pathological tracking ----
        if self.state["sync_quality"] < 0.2:
            self.state["desync_ticks"] += 1
        else:
            self.state["desync_ticks"] = max(0, self.state["desync_ticks"] - 1)
        if self.state["beta_power"] > 0.85:
            self.state["over_sync_ticks"] += 1
        else:
            self.state["over_sync_ticks"] = max(0, self.state["over_sync_ticks"] - 1)

        chronic_desync = self.state["desync_ticks"] > 15
        chronic_over = self.state["over_sync_ticks"] > 15

        if chronic_desync:
            self.feed_to_memory({"event": "thalamocortical_desync", "sync_quality": round(self.state["sync_quality"], 3)})
        if chronic_over:
            self.feed_to_memory({"event": "beta_over_sync", "beta": round(self.state["beta_power"], 3)})

        output = {
            "alpha_power": round(self.state["alpha_power"], 3),
            "beta_power": round(self.state["beta_power"], 3),
            "gamma_power": round(self.state["gamma_power"], 3),
            "theta_power": round(self.state["theta_power"], 3),
            "spindle_power": round(self.state["spindle_power"], 3),
            "sync_quality": round(self.state["sync_quality"], 3),
            "cross_freq_coupling": self.state["cross_freq_coupling"],
            "burst_mode": self.state["burst_mode"],
            "chronic_desync": chronic_desync,
            "chronic_over_sync": chronic_over,
            "primary_state": self._classify_state(),
        }
        self._record_history_(output)
        self.persist_state()
        return output

    def _classify_state(self) -> str:
        if self.state["spindle_power"] > 0.5:
            return "rest"
        if self.state["beta_power"] > 0.7 and self.state["gamma_power"] > 0.5:
            return "focus"
        if self.state["gamma_power"] > 0.55:
            return "alert"
        if self.state["alpha_power"] > 0.6:
            return "quiet"
        if self.state["sync_quality"] < 0.25:
            return "drifting"
        return "active"

    def _overnight(self):
        # NREM-like reset: high spindle, low gamma, alpha rises
        self.state["alpha_power"] = 0.7
        self.state["beta_power"] = 0.2
        self.state["gamma_power"] = 0.1
        self.state["spindle_power"] = 0.6
        self.state["desync_ticks"] = max(0, self.state.get("desync_ticks", 0) - 8)
        self.state["over_sync_ticks"] = max(0, self.state.get("over_sync_ticks", 0) - 6)
        out = {"overnight": "rhythm_reset_sleep_state", "spindle_power": 0.6}
        self._record_history_(out)
        self.persist_state()
        return out

    # ---- region-specific helpers ----
    def thalamic_firing_mode(self) -> str:
        return "burst" if self.state.get("burst_mode") else "tonic"

    def alpha_beta_ratio(self) -> float:
        b = self.state.get("beta_power", 1e-6) or 1e-6
        return round(self.state.get("alpha_power", 0.0) / b, 4)

    def gamma_envelope(self, window: int = 30) -> float:
        return self.drive_envelope(window)

    def cross_frequency_coupling_index(self) -> float:
        return self.state.get("cross_freq_coupling", 0.0)

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
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

    def adapter_state(self) -> dict:
        return {
            "tick_count": self.state.get("tick_count", 0),
            "has_legacy_impl": self.state.get("legacy_init_error") is None,
            "recent_drives_n": len(self.state.get("recent_drives", [])),
            "recent_states_n": len(self.state.get("recent_states", [])),
        }

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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict):
            return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v)
                break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str) and v in ("quiet","active","engaged","stuck","drifting","rest","fast","reflective","alert","focus"):
                primary_state = v
                break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05:
            return "rising"
        if delta < -0.05:
            return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0.0
        transitions = self.state_transition_count()
        return round(transitions / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent:
            return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
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
