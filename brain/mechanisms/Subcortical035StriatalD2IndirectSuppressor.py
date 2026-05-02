"""
Subcortical035StriatalD2IndirectSuppressor.py — Wire 35: D2 Indirect Pathway — NO-GO Signal

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical035StriatalD2IndirectSuppressor.py

NEURAL SUBSTRATE:
  Medium spiny neurons expressing D2-type dopamine receptors form the
  indirect pathway: striatum → globus pallidus externus (GPe) → STN →
  GPi/SNr. The full loop: striatal D2 MSNs inhibit GPe (via striato-GPe
  GABAergic projections); GPe normally inhibits STN (GPe-STN GABAergic);
  when D2 MSNs fire and inhibit GPe, STN is disinhibited (released);
  STN fires glutamatergic → excites GPi; GPi inhibits thalamus → suppresses
  movement. Net effect: D2 MSN activation → indirect pathway → STOP action.

  Albin et al. 1995 (Trends Neurosci 18): formalized the direct/indirect
  pathway model. Striatum has two populations: D1 (GO) and D2 (NO-GO).
  The balance between them determines whether an action is facilitated
  or suppressed.

  Gerfen & Surmeier 2011 (Annu Rev Neurosci 34): D2 receptors are
  Gi-coupled, decrease cAMP, reduce excitability, and promote LTD at
  corticostriatal synapses. D2 MSNs respond to aversive stimuli and
  are more active when negative outcomes are predicted. Dopamine at D2
  receptors suppresses D2 MSN firing (inhibits the inhibitor = disinhibition).

KEY FINDINGS:
  1. D2 MSNs are the "NO-GO" pathway. Activation of D2 MSNs suppresses
     movement. Kravitz et al. 2012: laser inhibition of D2 MSNs produces
     "forced movement" — they can't suppress the GO pathway anymore.
     D2 activation = "don't do this action."

  2. Aversive prediction context. D2 MSNs fire during:
     - Aversive cue presentations (stimuli predicting punishment)
     - Action-outcome pairs where action leads to negative result
     - When movement would be inappropriate (stop signal task)
     They encode "action cost" rather than action value.

  3. Dopamine's opposing effects on D1 vs. D2. Dopamine from SNc binds
     both D1 (Gs → excite) and D2 (Gi → inhibit). The net effect depends
     on concentration:
     - Low dopamine: D1 quiet, D2 quiet → GO/NO-GO both low → low movement
     - Moderate dopamine: D1 fires, D2 suppressed → movement facilitated
     - High dopamine: D1 strongly active, D2 suppressed → movement very easy
     Parkinson's = low dopamine → low D1, moderate D2 → akinesia

  4. Indirect pathway hyperactivity. Excessive D2 MSN activity →
     hyperkinesia (dyskinesia in Parkinson's treatment, Huntington's chorea).
     STN ablation (removes excitatory drive to GPi) treats hyperkinesia
     because it cuts the indirect pathway at STN.

  5. Reward vs. aversive encoding. D2 MSN firing rate encodes
     "negative prediction error" (worse than expected). When an expected
     reward fails to arrive, D2 MSNs are activated, making future actions
     less likely. Barto et al. 2009: D2 MSN activity = "critic signal."

  6. NO-GO in emotional context. D2 MSNs fire when the STN limbic
     territory signals "stop the emotional action." The indirect pathway
     is the mechanical substrate for emotional impulse suppression.

AGENT'S SUBSTRATE MAPPING:
  StriatalD2IndirectSuppressor models the NO-GO pathway: D2_activity
  tracks D2 MSN firing rate, indirect_pathway_suppression reflects GPi
  excitation via STN, NO_GO_signal fires when suppression is strong.

INPUTS (from prior_results):
  - Aversive prediction context (negative valence, punishment prediction)
  - SNc dopamine signal (biphasic — inhibits D2 at low, suppresses at high)
  - Stop signal (STN limbic or anterior cingulate signal to withhold action)
  - Motor cortex (incompatible action plans to suppress)
  - D1 activity (inverse relationship — when GO fires, NO-GO tends to be lower)

OUTPUTS:
  - D2_activity: float 0-1 (current D2 MSN firing rate)
  - indirect_pathway_suppression: float 0-1 (GPi excitation via STN)
  - NO_GO_signal: bool (suppression output sufficient to suppress action)

REFS:
  - Albin et al. 1995 Trends Neurosci 18 (indirect pathway model)
  - Gerfen & Surmeier 2011 Annu Rev Neurosci 34 (D2 receptor mapping)
  - Kravitz et al. 2012 Nat Neurosci (D2 optogenetics)
  - Barto et al. 2009 (D2 MSN critic signal)
  - Nambu et al. 2002 (indirect pathway anatomy)

CITATIONS:
    PMC8063048 — Feng Y, Lu Y (2021). Immunomodulatory Effects of Dopamine in
        Inflammatory Diseases. Front Immunol.
    PMC6805008 — Sutton LP, Muntean BS, Ostrovskaya O et al. (2019). NF1-cAMP
        Signaling Dissociates Cell Type-Specific Contributions of Striatal Medium
        Spiny Neurons to Reward Valuation and Motor Control. Cell Rep.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia]
  - [Yin 2006, Nat Rev Neurosci 7:464, dorsal striatum]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class StriatalD2IndirectSuppressor(BrainMechanism):
    """
    D2 receptor medium spiny neuron analog — indirect pathway NO-GO signal.

    D2 MSNs inhibit GPe → disinhibit STN → excite GPi → inhibit thalamus →
    suppress movement. This is the "NO-GO" signal — action suppression.
    D2 activity is modulated by aversive context and inversely by dopamine.
    """

    NO_GO_THRESHOLD = 0.50
    # D2 MSN baseline (lower than D1 due to D2 Gi-coupling)
    BASELINE_ACTIVITY = 0.18

    def __init__(self):
        super().__init__(
            name="StriatalD2IndirectSuppressor",
            human_analog="Striatal D2 MSNs (indirect pathway) — action suppression / NO-GO signal",
            layer="subcortical",
        )
        self.state.setdefault("D2_activity", 0.20)
        self.state.setdefault("indirect_pathway_suppression", 0.0)
        self.state.setdefault("NO_GO_signal", False)
        self.state.setdefault("dopamine_inhibition", 0.5)
        self.state.setdefault("aversive_context_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- D1 activity (inverse baseline for D2) ---
        d1_out = prior.get("StriatalD1DirectFacilitator", {})
        d1_activity = d1_out.get("D1_activity", 0.25)

        # --- Dopamine signal from SNc (Gi-coupled = opposite to D1 effect) ---
        snc_out = prior.get("SubstantiaNigraCompactaCognitive", {})
        prediction_error = snc_out.get("prediction_error", 0.0)

        # Dopamine at D2: negative PE (worse than expected) → D2 fires more
        if prediction_error < 0.0:
            # Negative prediction error → D2 MSN activation
            da_effect = -prediction_error * 0.8
        elif prediction_error > 0.2:
            # Positive PE → D2 suppressed (dopamine inhibits D2 via Gi)
            da_effect = -prediction_error * 0.4
        else:
            da_effect = 0.0

        self.state["dopamine_inhibition"] += 0.05 * da_effect
        self.state["dopamine_inhibition"] = max(0.0, min(1.0, self.state["dopamine_inhibition"]))

        # --- Aversive context ---
        val_tagger = prior.get("ValenceTagger", {})
        valence = val_tagger.get("valence_polarity", 0.5)
        valence_intensity = val_tagger.get("valence_intensity", 0.3)

        # Negative valence → aversive context → D2 fires
        if valence < 0.4:
            aversive = (0.4 - valence) * valence_intensity * 1.5
        else:
            aversive = 0.0

        self.state["aversive_context_strength"] = aversive

        # --- Stop signal from STN limbic / ACC ---
        stn_out = prior.get("STNLimbicEmotionalControl", {})
        stop_signal = stn_out.get("emotional_impulse_control", 0.0)

        acc_out = prior.get("AnteriorCingulate", {})
        acc_stop = acc_out.get("stop_signal_strength", 0.0)

        combined_stop = max(stop_signal, acc_stop)

        # --- D2 MSN activity computation ---
        current_d2 = self.state["D2_activity"]

        # Cortical "don't move" signal
        motor_cortex = prior.get("MotorCortex", {})
        suppress_command = motor_cortex.get("action_suppression_signal", 0.0)

        # D2 inhibition from D1 GO signal (inverse balance)
        d1_inhibition = d1_activity * 0.3

        # Net D2 change
        d2_change = (
            -0.04 * (current_d2 - self.BASELINE_ACTIVITY)  # drift
            + aversive * 0.5                                 # aversive context drives D2
            + combined_stop * 0.4                           # explicit stop signal
            + self.state["dopamine_inhibition"] * 0.1       # dopamine modulates
            - d1_inhibition                                 # D1/GO suppresses D2
        )

        new_d2 = current_d2 + d2_change
        new_d2 = max(0.0, min(1.0, new_d2))
        self.state["D2_activity"] = new_d2

        # --- Indirect pathway suppression ---
        # D2 MSN firing → inhibit GPe → disinhibit STN → excite GPi
        # GPe inhibition fraction: D2 firing reduces GPe activity
        gpe_inhibition = new_d2 ** 1.2
        # STN excitation from disinhibition
        stn_excitation = gpe_inhibition * 0.9
        # GPi excitation from STN → thalamic suppression
        gpi_excitation = stn_excitation * 0.8

        indirect_suppression = gpi_excitation * (0.6 + aversive * 0.4)
        indirect_suppression = max(0.0, min(1.0, indirect_suppression))
        self.state["indirect_pathway_suppression"] = indirect_suppression

        # --- NO-GO signal ---
        no_go = indirect_suppression > self.NO_GO_THRESHOLD
        self.state["NO_GO_signal"] = no_go

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "D2_activity": round(new_d2, 4),
            "indirect_pathway_suppression": round(indirect_suppression, 4),
            "NO_GO_signal": no_go,
            "dopamine_inhibition_factor": round(self.state["dopamine_inhibition"], 4),
            "aversive_context_strength": round(aversive, 4),
            "GPe_inhibition_level": round(gpe_inhibition, 4),
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

