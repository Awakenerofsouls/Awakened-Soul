"""
InterpeduncularNucleus — IPN / Aversion-Reward Valence Hub

NEURAL SUBSTRATE
================
Unpaired midline nucleus in the ventral midbrain between the cerebral
peduncles. Multiple subnuclei: rostral, central, lateral, dorsal. The IPN
is the principal target of the medial habenula via fasciculus retroflexus,
receiving cholinergic + glutamatergic + substance-P + GABA from MHb.

Outputs:
- Median raphe (5HT modulation)
- Dorsal tegmental nucleus
- Raphe pallidus (autonomic + thermoregulation)
- Periaqueductal gray (defense)
- Lateral septum (limbic feedback)

GABAergic output dominant. Functions as the aversion-axis amplifier:
modulates serotonin tone during aversive states, gates anxiety expression,
contributes to nicotine withdrawal aversion. α5β4 nicotinic receptors
on IPN neurons mediate nicotine threshold.

KEY FINDINGS
============
1. IPN GABAergic→raphe pathway gates serotonin during aversion;
   chemogenetic IPN activation suppresses dorsal raphe firing —
   [Quina 2017, Brain Struct Funct 222:1851, doi:10.1007/s00429-016-1311-0]
2. MHb→IPN ACh stimulation drives anxiety-like behavior; α5 KO blocks —
   [Hsu 2013, Nat Neurosci 16:1623, PMC3812308]
3. IPN α5β4 nicotinic receptors mediate nicotine sensitivity threshold —
   [Frahm 2011, Neuron 70:522, doi:10.1016/j.neuron.2011.04.013]
4. IPN α5 KO alters aversion-reward valence shift in nicotine taking —
   [Fowler 2011, Nature 471:597, doi:10.1038/nature09797]
5. IPN lesions disrupt REM rhythmicity via dorsal tegmental nucleus
   pathway — [Clark 2013, J Neurosci 33:6253, PMID 23575820]

INPUTS
======
- MedialHabenula.ipn_drive_command, .mhb_cholinergic_drive,
  .mhb_substance_p_drive, .mhb_glutamate_drive

OUTPUTS
=======
- ipn_drive (0-1)
- raphe_5ht_modulation (-1 to 1, signed: + facilitate, - suppress)
- dorsal_tegmental_signal (0-1) — REM-rhythmicity coupling
- aversion_amplification (0-1)
- ipn_state (str): "aversion_gain" | "rem_modulation" |
  "withdrawal_amplifier" | "quiet"

brain_runner enrichment:
    ipn = all_results.get("InterpeduncularNucleus", {})
    if ipn:
        enrichments["brain_ipn_drive"] = ipn.get("ipn_drive", 0.0)
        enrichments["brain_raphe_5ht_mod"] = ipn.get("raphe_5ht_modulation", 0.0)
        enrichments["brain_aversion_amp"] = ipn.get("aversion_amplification", 0.0)
        enrichments["brain_ipn_state"] = ipn.get("ipn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class InterpeduncularNucleus(BrainMechanism):
    """IPN — aversion-axis amplifier; receives MHb, modulates raphe."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AVERSION_THRESHOLD = 0.40
    REM_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="InterpeduncularNucleus",
            human_analog="Interpeduncular nucleus (aversion-axis amplifier)",
            layer="foundational",
        )
        self.state.setdefault("ipn_drive", self.BASELINE)
        self.state.setdefault("raphe_5ht_modulation", 0.0)
        self.state.setdefault("dorsal_tegmental_signal", 0.0)
        self.state.setdefault("aversion_amplification", 0.0)
        self.state.setdefault("ipn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # IPN drive — proportional to MHb command (Hsu 2013, Quina 2017)
    # ------------------------------------------------------------------
    def _ipn_drive(self, mhb_cmd: float, chol: float, subp: float, glu: float) -> float:
        """IPN firing scales with combined MHb input."""
        target = self.BASELINE + mhb_cmd * 0.50
        target += chol * 0.15 + subp * 0.15 + glu * 0.10
        return min(1.0, target)

    # ------------------------------------------------------------------
    # Raphe 5HT modulation — ACh suppresses, substance-P facilitates (Quina 2017)
    # ------------------------------------------------------------------
    def _raphe_modulation(self, chol: float, subp: float) -> float:
        """Signed signal: negative = 5HT suppression, positive = facilitation.

        Cholinergic-dominant IPN tone suppresses raphe (aversion → reduced
        5HT). Substance-P-dominant tone slightly facilitates.
        """
        signal = subp * 0.40 - chol * 0.55
        return max(-1.0, min(1.0, signal))

    # ------------------------------------------------------------------
    # Dorsal tegmental signal — REM rhythmicity coupling (Clark 2013)
    # ------------------------------------------------------------------
    def _dorsal_tegmental(self, ipn_drive: float, glu: float) -> float:
        """IPN → dorsal tegmental nucleus → REM circuit.

        Glutamatergic IPN component drives dorsal tegmental.
        """
        return min(1.0, ipn_drive * 0.5 + glu * 0.4)

    # ------------------------------------------------------------------
    # Aversion amplification (Hsu 2013, Fowler 2011)
    # ------------------------------------------------------------------
    def _aversion_amplification(self, chol: float, subp: float,
                                  ipn_drive: float) -> float:
        """Aversion amplification — combination of ACh + substance-P
        IPN drive. Both pathways converge on aversion expression."""
        return min(1.0, chol * 0.4 + subp * 0.4 + ipn_drive * 0.2)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, ipn_drive: float, chol: float, subp: float,
                          dorsal_teg: float) -> str:
        """Classify IPN operating mode."""
        if ipn_drive < 0.15:
            return "quiet"
        # MHb-cholinergic-dominant input → withdrawal amplifier
        if chol > 0.40 and chol > subp * 1.3:
            return "withdrawal_amplifier"
        # Substance-P-dominant → aversion gain
        if subp > self.AVERSION_THRESHOLD:
            return "aversion_gain"
        # Glutamatergic-dominant → REM modulation
        if dorsal_teg > self.REM_THRESHOLD:
            return "rem_modulation"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _ipn_subnucleus_split(self, ipn_drive: float, chol: float,
                                subp: float, glu: float) -> dict:
        """Split aggregate IPN drive into rostral / central / lateral
        subnucleus activations. Rostral receives MHb-substance-P;
        central receives MHb-cholinergic; lateral receives MHb-glutamate.
        """
        rostral = min(1.0, ipn_drive * 0.4 + subp * 0.6)
        central = min(1.0, ipn_drive * 0.4 + chol * 0.6)
        lateral = min(1.0, ipn_drive * 0.4 + glu * 0.6)
        return {"rostral": rostral, "central": central, "lateral": lateral}

    def _aversion_history_smooth(self, recent: list, current: float) -> float:
        """Smoothed aversion-amplification window (last 30 ticks).
        Detects building aversion vs transient spikes — chronic state
        marker for IPN→raphe sustained suppression.
        """
        if not recent:
            return current
        window = recent[-30:]
        if not window:
            return current
        avg = sum(s == "aversion_gain" for s in window) / len(window)
        return min(1.0, current * 0.6 + avg * 0.4)

    def _ipn_serotonin_lock(self, raphe_mod: float, recent: list) -> float:
        """Sustained ACh-dominant IPN tone produces serotonin-suppression
        lock that takes ticks to release. Returns suppression magnitude.
        """
        if raphe_mod >= 0.0:
            return 0.0
        recent_window = [s for s in recent[-20:] if s == "withdrawal_amplifier"]
        lock_factor = len(recent_window) / 20.0
        return min(1.0, abs(raphe_mod) * (0.5 + lock_factor * 0.5))

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "ipn_drive": self.state.get("ipn_drive", 0.0),
            "raphe_mod": self.state.get("raphe_5ht_modulation", 0.0),
            "aversion_amp": self.state.get("aversion_amplification", 0.0),
            "state": self.state.get("ipn_state", "quiet"),
        }
    def _rostral_central_lateral_split(self, ipn_drive: float,
                                          chol: float, subp: float,
                                          glu: float) -> dict:
        """IPN subnucleus split — output by subdivision (Quina 2017).
        Rostral IPN  → median raphe
        Central IPN  → dorsal raphe + dorsal tegmental
        Lateral IPN  → REM circuits + ventral tegmental
        """
        return {
            "rostral_to_median_raphe": min(1.0, ipn_drive * 0.4 + subp * 0.5),
            "central_to_dorsal_raphe": min(1.0, ipn_drive * 0.4 + chol * 0.5),
            "lateral_to_rem": min(1.0, ipn_drive * 0.4 + glu * 0.5),
        }

    def _is_chronic_aversion(self, recent_states: list,
                                window: int = 40) -> bool:
        """Chronic-aversion detection — sustained aversion_gain or
        withdrawal_amplifier across the recent window."""
        if not recent_states:
            return False
        w = recent_states[-window:]
        if not w:
            return False
        chronic_states = sum(
            1 for s in w
            if s in ("aversion_gain", "withdrawal_amplifier")
        )
        return chronic_states / len(w) > 0.6

    def _alpha5_nicotinic_threshold(self, chol: float, glu: float) -> float:
        """α5β4 nicotinic receptor threshold modulation (Frahm 2011).
        IPN α5 expression sets nicotine sensitivity threshold.
        """
        if chol < 0.20 and glu < 0.15:
            return 0.0
        return min(1.0, chol * 0.65 + glu * 0.35)


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mhb_data = prior.get("MedialHabenula", {})
        mhb_cmd = float(mhb_data.get("ipn_drive_command", 0.0))
        chol = float(mhb_data.get("mhb_cholinergic_drive", 0.0))
        subp = float(mhb_data.get("mhb_substance_p_drive", 0.0))
        glu = float(mhb_data.get("mhb_glutamate_drive", 0.0))

        # --- Drive ---
        ipn_target = self._ipn_drive(mhb_cmd, chol, subp, glu)
        prev_drive = float(self.state.get("ipn_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, ipn_target)

        # --- Raphe modulation ---
        raphe_mod = self._raphe_modulation(chol, subp)

        # --- Dorsal tegmental signal ---
        dorsal_teg = self._dorsal_tegmental(new_drive, glu)

        # --- Aversion amplification ---
        aversion_amp = self._aversion_amplification(chol, subp, new_drive)

        state = self._classify_state(new_drive, chol, subp, dorsal_teg)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ipn_drive"] = round(new_drive, 4)
        self.state["raphe_5ht_modulation"] = round(raphe_mod, 4)
        self.state["dorsal_tegmental_signal"] = round(dorsal_teg, 4)
        self.state["aversion_amplification"] = round(aversion_amp, 4)
        self.state["ipn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ipn_drive": round(new_drive, 4),
            "raphe_5ht_modulation": round(raphe_mod, 4),
            "dorsal_tegmental_signal": round(dorsal_teg, 4),
            "aversion_amplification": round(aversion_amp, 4),
            "ipn_state": state,
        }
