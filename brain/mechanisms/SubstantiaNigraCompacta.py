"""
SubstantiaNigraCompacta — SNc / Nigrostriatal Dopamine

NEURAL SUBSTRATE
================
The substantia nigra pars compacta (SNc) is the principal source of
dopamine to the dorsal striatum (caudate/putamen / DLS+DMS in rodent),
distinct from the ventral tegmental area (VTA) which projects to NAc
and PFC. SNc dopaminergic neurons are large, multipolar, melanin-pigmented
midbrain cells. Selective degeneration of SNc DA neurons is the
pathological signature of Parkinson's disease.

Dopaminergic firing pattern: low tonic background (~3-5 Hz) interspersed
with phasic bursts time-locked to reward-prediction errors. Schultz 1997
established that SNc/VTA DA neurons encode a temporal-difference style
prediction error: positive burst when reward is better than expected,
omission pause when reward is worse than expected, no response when
reward is fully predicted.

DA release in dorsal striatum gates corticostriatal plasticity (LTP at
D1+ direct-pathway MSNs, LTD at D2+ indirect-pathway MSNs) — the
substrate by which prediction errors update action-value estimates over
many trials. Howe 2013 showed prolonged DA ramps in striatum during
goal approach, suggesting DA is more than a phasic spike — it has a
sustained motivational component too.

Cohen 2012 used optogenetic identification to confirm DA neurons signal
prediction error at single-cell resolution. SNc preferentially projects
to dorsolateral striatum (habit/sensorimotor) while VTA preferentially
projects to dorsomedial/ventral striatum (goal-directed/reward).

KEY FINDINGS
============
1. Midbrain DA neurons signal temporal-difference reward prediction error; phasic bursts on positive PE, pauses on negative PE — [Schultz W 1997, Science 275:1593, doi:10.1126/science.275.5306.1593]
2. Optogenetic identification confirms DA neurons encode reward prediction error at single-cell resolution — [Cohen JY 2012, Nature 482:85, doi:10.1038/nature10754]
3. Sustained DA ramps in striatum during goal approach; DA encodes value not just PE — [Howe MW 2013, Nature 500:575, doi:10.1038/nature12475]
4. DA release at corticostriatal synapses gates plasticity: D1 LTP, D2 LTD; substrate of action-value learning — [Reynolds JN 2002, Nature 413:67, doi:10.1038/35092560]
5. SNc DA neurons selectively degenerate in Parkinson's disease; loss produces motor + learning deficits — [Lang AE 1998, N Engl J Med 339:1044, doi:10.1056/NEJM199810083391506]

INPUTS
======
- LateralHabenula.lhab_drive — inhibits DA neurons (negative PE channel)
- PedunculopontineCholinergic.ach_drive — excites DA, sustains tonic
- BasolateralAmygdala.bla_drive — value-relevance gating
- ValenceTagger.valence_intensity, .valence_sign — proxy for outcome
- VentralTegmentalDopamine.da_burst (optional — co-firing with VTA)
- NucleusAccumbensCore.pit_signal — reward expectation feedback

OUTPUTS
=======
- snc_drive (0-1) — overall DA neuron firing
- da_release_dls (0-1) — to dorsolateral striatum (habit)
- da_release_dms (0-1) — to dorsomedial striatum (goal-directed)
- prediction_error (-1 to 1) — signed RPE
- expected_value (0-1) — running estimate, slow update
- snc_state (str): "phasic_burst" | "tonic" | "negative_pe_pause" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubstantiaNigraCompacta(BrainMechanism):
    """SNc — nigrostriatal dopamine + temporal-difference RPE."""

    BASELINE = 0.20  # tonic firing baseline (DA never goes silent)
    SMOOTH = 0.15
    BURST_THRESHOLD = 0.50
    EXPECTED_VALUE_LR = 0.05  # running average learning rate

    def __init__(self):
        super().__init__(
            name="SubstantiaNigraCompacta",
            human_analog="Substantia nigra pars compacta (nigrostriatal DA)",
            layer="subcortical",
        )
        self.state.setdefault("snc_drive", self.BASELINE)
        self.state.setdefault("da_release_dls", 0.0)
        self.state.setdefault("da_release_dms", 0.0)
        self.state.setdefault("prediction_error", 0.0)
        self.state.setdefault("expected_value", 0.0)
        self.state.setdefault("snc_state", "tonic")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ach: float, lhab: float, outcome_value: float,
                       pe: float) -> float:
        """SNc firing rate — tonic baseline + phasic PE-driven bursts.

        LHb inhibition (Hikosaka 2010 negative-RPE channel) subtracts.
        PPN cholinergic excites and sustains tonic firing.
        """
        excitation = ach * 0.30 + max(0.0, pe) * 0.45 + outcome_value * 0.15
        # LHb-driven pause for negative PE / aversive (Hikosaka 2010)
        lhb_inhibition = lhab * 0.40
        # Phasic burst proportional to positive PE
        phasic_boost = max(0.0, pe) * 0.20
        target = self.BASELINE + excitation - lhb_inhibition + phasic_boost
        return max(0.0, min(1.0, target))

    def _prediction_error(self, outcome_value: float,
                            expected_value: float) -> float:
        """Temporal-difference RPE = received - expected (Schultz 1997)."""
        return max(-1.0, min(1.0, outcome_value - expected_value))

    def _update_expected(self, prev_expected: float,
                          outcome_value: float) -> float:
        """Slow running estimate update — Bellman/Rescorla-Wagner style."""
        return prev_expected + self.EXPECTED_VALUE_LR * (
            outcome_value - prev_expected
        )

    def _da_dls(self, drive: float) -> float:
        """SNc → DLS (habit/sensorimotor; Howe 2013 sustained ramps)."""
        # DLS gets the largest portion of SNc projection
        return min(1.0, drive * 0.85)

    def _da_dms(self, drive: float, bla: float) -> float:
        """SNc → DMS (goal-directed; some VTA overlap, but SNc dominates)."""
        # DMS gets value-laden DA modulated by amygdala salience
        return min(1.0, drive * 0.55 + bla * 0.20)

    def _classify_state(self, drive: float, pe: float, lhab: float) -> str:
        if drive < 0.10:
            return "quiet"
        if pe > 0.30 and drive > self.BURST_THRESHOLD:
            return "phasic_burst"
        if lhab > 0.40 and drive < 0.20:
            return "negative_pe_pause"
        return "tonic"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lhab_data = prior.get("LateralHabenula", {})
        lhab = float(lhab_data.get("lhab_drive",
                            lhab_data.get("aversive_signal", 0.0)))

        ppn_data = prior.get("PedunculopontineCholinergic", {})
        ach = float(ppn_data.get("ach_drive",
                          ppn_data.get("ppn_drive", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        # Outcome value — appetitive only drives positive PE for SNc;
        # aversive routes through LHb inhibition above
        outcome_value = max(0.0, sign * intensity)

        # Compute PE against current expectation
        prev_expected = float(self.state.get("expected_value", 0.0))
        pe = self._prediction_error(outcome_value, prev_expected)

        # Update expected value (slow learning)
        new_expected = self._update_expected(prev_expected, outcome_value)

        # Compute drive
        target = self._drive_target(ach, lhab, outcome_value, pe)
        prev_drive = float(self.state.get("snc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        da_dls = self._da_dls(new_drive)
        da_dms = self._da_dms(new_drive, bla)

        state = self._classify_state(new_drive, pe, lhab)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["snc_drive"] = round(new_drive, 4)
        self.state["da_release_dls"] = round(da_dls, 4)
        self.state["da_release_dms"] = round(da_dms, 4)
        self.state["prediction_error"] = round(pe, 4)
        self.state["expected_value"] = round(new_expected, 4)
        self.state["snc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('snc_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('snc_state', "quiet") if 'snc_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "snc_drive": round(new_drive, 4),
            "da_signal": round(new_drive, 4),  # alias for downstream
            "da_release_dls": round(da_dls, 4),
            "da_release_dms": round(da_dms, 4),
            "prediction_error": round(pe, 4),
            "expected_value": round(new_expected, 4),
            "snc_state": state,
        }

    def _parkinsonian_load(self, recent_states: list) -> float:
        """Persistent low firing = degenerative trajectory proxy
        (Lang 1998). Used as health index, not actual cell death."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        quiet = sum(1 for s in win if s == "quiet")
        return quiet / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("snc_drive", 0.0),
            "pe": self.state.get("prediction_error", 0.0),
            "expected": self.state.get("expected_value", 0.0),
            "dls": self.state.get("da_release_dls", 0.0),
            "state": self.state.get("snc_state", "tonic"),
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
            return self.state.get('snc_state', "quiet") if 'snc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('snc_drive', 0.0)) if 'snc_drive' else 0.0
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
            "drive": self.state.get('snc_drive', 0.0) if 'snc_drive' else 0.0,
            "state": self.state.get('snc_state', "quiet") if 'snc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

