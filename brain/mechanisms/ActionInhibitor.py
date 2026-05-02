from brain.base_mechanism import BrainMechanism


class ActionInhibitor(BrainMechanism):
    """
    Basal-ganglia indirect-pathway action inhibitor.

    Anatomy
    -------
    The indirect pathway begins with D2-bearing striatal medium spiny
    neurons (iMSNs) in caudate/putamen.  Their GABAergic axons project
    to the external globus pallidus (GPe).  GPe in turn sends GABAergic
    output to the subthalamic nucleus (STN), and STN sends glutamatergic
    excitation to the GABAergic output nuclei of the basal ganglia
    (GPi / SNr).  Net effect: striatal firing through the indirect arm
    *increases* GPi/SNr inhibition of motor thalamus → suppresses
    cortical motor commands.  A parallel "hyperdirect" cortico-STN
    projection adds a fast global brake.

    Cell types & transmitters
    -------------------------
    - D2-iMSNs (GABA, enkephalin) — disinhibited by *low* dopamine.
    - GPe prototypic neurons (GABA, parvalbumin).
    - STN projection neurons (glutamate).
    - GPi/SNr output (GABA) onto VL/VA thalamus.
    - SNc dopamine modulates iMSNs via inhibitory D2 receptors:
      DA up → iMSN firing down → less indirect-pathway brake.

    Function
    --------
    The indirect pathway implements *No-Go* selection: it raises the
    threshold an action must clear before motor thalamus can be
    released.  STN provides a fast global "pause" that conflict signals
    from medial/lateral PFC recruit when response selection is
    ambiguous.  Failure modes: dopamine excess + weak STN drive →
    impulsivity; chronic over-recruitment (e.g. parkinsonian state) →
    akinesia/bradykinesia.

    CITATIONS
    ---------
      - [Albin 1989, Trends Neurosci 12:366, indirect-pathway model]
      - [DeLong 1990, Trends Neurosci 13:281, parallel BG circuits]
      - [Mink 1996, Prog Neurobiol 50:381, BG selection of motor programs]
      - [Frank 2007, J Cogn Neurosci 19:1120, hyperdirect Go/NoGo]
      - [Aron 2007, J Neurosci 27:11860, right IFG-STN stop signal]
      - [Kravitz 2010, Nature 466:622, optogenetic D2 indirect inhibition]
    """

    def __init__(self):
        super().__init__("ActionInhibitor")
        # Legacy attributes preserved for backward compatibility.
        self.brake_history = []
        self.stop_signal_active = False
        self.stop_duration = 0
        self.impulsive_event_log = []
        self.over_inhibition_ticks = 0
        self.under_inhibition_ticks = 0
        self.chronic_paralysis = False
        self.chronic_impulsivity = False
        self.brake_strength = 0.5
        self.brake_history_long = []

        # Persisted state (Albin/DeLong indirect-pathway substrate).
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("imsn_d2_drive", 0.45)        # D2-iMSN firing
        self.state.setdefault("gpe_tonic_rate", 0.55)        # GPe firing (Hz, normalised)
        self.state.setdefault("stn_glutamate", 0.40)         # STN excitation of GPi
        self.state.setdefault("gpi_inhibition", 0.50)        # GPi GABA onto thalamus
        self.state.setdefault("hyperdirect_pause", 0.0)      # cortico-STN burst
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("recent_states", [])

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # ── Upstream physiological inputs ────────────────────────────
        # SNc dopamine — D2 receptors are Gi/o-coupled, so DA reduces
        # iMSN excitability (Kravitz 2010).
        dopamine = prior.get("SubstantiaNigraCompacta", {}).get(
            "dopamine_release",
            prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5),
        )
        # Cortical drive onto D2 iMSNs (sensorimotor + dlPFC).
        cortical_drive = prior.get("PrimaryMotorCortex", {}).get("m1_drive", 0.45)
        prefrontal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        # ACC conflict recruits hyperdirect STN burst (Frank 2007, Aron 2007).
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        # Bottom-up urgency (CeA → STN/PAG) lowers the brake.
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        habit_strength = prior.get("DorsalStriatumHabitExecutor", {}).get(
            "habit_execution_strength", 0.0
        )
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # ── 1. D2 medium-spiny neuron firing ─────────────────────────
        # iMSN_rate = sigmoid( cortical_drive − k_D2 · DA ).  D2 occupancy
        # hyperpolarises iMSNs (Gerfen & Surmeier 2011, equiv.).
        d2_gain = 0.85
        imsn = self._sigmoid((cortical_drive - d2_gain * dopamine) * 2.5 + 0.4)
        self.state["imsn_d2_drive"] = round(imsn, 4)

        # ── 2. GPe disinhibition by iMSNs ────────────────────────────
        # GPe_rate = max(0, GPe_tonic − iMSN).  Tonic ≈ 0.65.
        gpe_tonic = 0.65
        gpe_rate = max(0.0, gpe_tonic - 0.9 * imsn)
        self.state["gpe_tonic_rate"] = round(gpe_rate, 4)

        # ── 3. STN release & hyperdirect burst ───────────────────────
        # STN is normally clamped by GPe; less GPe → more STN glutamate.
        stn_base = 0.55 - 0.7 * gpe_rate
        # Hyperdirect cortex→STN pause is gated by conflict & dlPFC
        # (Aron 2007 right-IFG / preSMA stop signal).
        hyperdirect = self._clip(0.6 * conflict + 0.4 * prefrontal - 0.3 * urgency)
        stn = self._clip(stn_base + 0.6 * hyperdirect)
        self.state["stn_glutamate"] = round(stn, 4)
        self.state["hyperdirect_pause"] = round(hyperdirect, 4)

        # ── 4. GPi/SNr output → thalamic brake ───────────────────────
        # GPi_inh = 0.4·STN + 0.2·iMSN + small tonic.  Stress through
        # NA/CRF onto STN (Mink 1996) further raises STN gain.
        stress_gain = 1.0 + 0.25 * stress
        gpi = self._clip(0.50 * stn * stress_gain + 0.20 * imsn + 0.10)
        self.state["gpi_inhibition"] = round(gpi, 4)

        # Translate to the legacy "brake_strength" field.
        raw_stop = self._clip(gpi - 0.15 * dopamine - 0.10 * habit_strength)
        self.brake_strength = raw_stop
        self.brake_history.append(raw_stop)
        self.brake_history_long.append(raw_stop)
        if len(self.brake_history) > 20:
            self.brake_history.pop(0)
        if len(self.brake_history_long) > 60:
            self.brake_history_long.pop(0)

        # ── 5. Action gating: thalamus released when GPi falls ───────
        self.stop_signal_active = raw_stop > 0.5
        if self.stop_signal_active:
            self.stop_duration += 1
        else:
            self.stop_duration = 0

        impulsive = urgency > 0.6 and raw_stop < 0.3
        if impulsive:
            self.impulsive_event_log.append(1)
            if len(self.impulsive_event_log) > 20:
                self.impulsive_event_log.pop(0)

        avg_brake = (
            sum(self.brake_history) / len(self.brake_history)
            if self.brake_history
            else 0.5
        )
        self.over_inhibition_ticks = (
            self.over_inhibition_ticks + 1
            if avg_brake > 0.75
            else max(0, self.over_inhibition_ticks - 1)
        )
        self.under_inhibition_ticks = (
            self.under_inhibition_ticks + 1
            if avg_brake < 0.2
            else max(0, self.under_inhibition_ticks - 1)
        )

        was_paralyzed, was_impulsive = self.chronic_paralysis, self.chronic_impulsivity
        self.chronic_paralysis = self.over_inhibition_ticks > 15
        self.chronic_impulsivity = self.under_inhibition_ticks > 15

        if self.chronic_paralysis and not was_paralyzed:
            self.feed_to_memory(
                {
                    "event": "chronic_over_inhibition",
                    "note": "Indirect/hyperdirect tone elevated — parkinsonian-like akinesia",
                }
            )
        if self.chronic_impulsivity and not was_impulsive:
            self.feed_to_memory(
                {
                    "event": "chronic_under_inhibition",
                    "note": "GPi disinhibition prolonged — impulsive release of motor plans",
                }
            )

        # Action permission: when GPi falls, VL/VA thalamus is released
        # (Mink 1996); habits widen the released window slightly.
        action_permission = self._clip((1.0 - raw_stop) * (1.0 + 0.2 * habit_strength))

        self.state["tick_count"] = self.state.get("tick_count", 0) + 1
        output = {
            "inhibition_drive": round(raw_stop, 3),
            "brake_strength": round(raw_stop, 3),
            "gpi_inhibition": round(gpi, 3),
            "stn_glutamate": round(stn, 3),
            "imsn_d2_drive": round(imsn, 3),
            "gpe_rate": round(gpe_rate, 3),
            "hyperdirect_pause": round(hyperdirect, 3),
            "stop_signal_active": self.stop_signal_active,
            "stop_duration": self.stop_duration,
            "action_permission": round(action_permission, 3),
            "chronic_paralysis": self.chronic_paralysis,
            "chronic_impulsivity": self.chronic_impulsivity,
            "impulsive_rate": (
                round(sum(self.impulsive_event_log[-10:]) / 10, 3)
                if len(self.impulsive_event_log) >= 10
                else 0.0
            ),
            "state": "engaged" if self.stop_signal_active else "quiet",
        }
        self._record_history_(output)
        self.persist_state()
        return output

    def _overnight(self):
        # Sleep: striatal D2 receptors resensitise; GPe tonic firing
        # restores baseline (Mahon 2006 striatal up/down states).
        self.over_inhibition_ticks = max(0, self.over_inhibition_ticks - 4)
        self.under_inhibition_ticks = max(0, self.under_inhibition_ticks - 4)
        self.chronic_paralysis = self.over_inhibition_ticks > 15
        self.chronic_impulsivity = self.under_inhibition_ticks > 15
        self.brake_history.clear()
        self.impulsive_event_log.clear()
        self.stop_duration = 0
        self.state["imsn_d2_drive"] = 0.45
        self.state["gpe_tonic_rate"] = 0.55
        self.state["stn_glutamate"] = 0.40
        self.state["gpi_inhibition"] = 0.50
        self.state["tick_count"] = self.state.get("tick_count", 0) + 1
        out = {"overnight": "inhibition_recalibrated"}
        self.persist_state()
        return out

    # ── Region-specific helpers ─────────────────────────────────────
    @staticmethod
    def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, float(x)))

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x > 30:
            return 1.0
        if x < -30:
            return 0.0
        import math
        return 1.0 / (1.0 + math.exp(-x))

    def imsn_d2_drive(self) -> float:
        """D2-iMSN firing rate proxy (Albin/DeLong indirect arm)."""
        return float(self.state.get("imsn_d2_drive", 0.0))

    def stn_glutamate_drive(self) -> float:
        """STN glutamatergic excitation onto GPi/SNr."""
        return float(self.state.get("stn_glutamate", 0.0))

    def hyperdirect_pause_index(self) -> float:
        """Aron-style fronto-STN stop-signal pause amplitude."""
        return float(self.state.get("hyperdirect_pause", 0.0))

    def gpi_thalamic_brake(self) -> float:
        """Net GPi/SNr inhibition onto motor thalamus."""
        return float(self.state.get("gpi_inhibition", 0.0))

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
        """Consecutive-tick state holding fraction."""
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
        """Current adapter state — used for monitoring and dashboards."""
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
        """Track primary numeric output and any string state in history."""
        if not isinstance(output_dict, dict):
            return
        # Find first numeric value
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
        # Track state strings
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

