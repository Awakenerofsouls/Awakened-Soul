"""
MedullaryRapheMagnus — Nucleus Raphe Magnus (NRM) Descending Serotonin Modulator

NEURAL SUBSTRATE
================
The nucleus raphe magnus (NRM) sits in the rostroventromedial medulla and
contains the largest population of bulbospinal serotonergic (5-HT) neurons.
Its 5-HT projections descend through the dorsolateral funiculus to spinal
dorsal horn, where they form a key output of the descending pain modulation
system. Approximately 23% of NRM neurons are 5-HT immunoreactive — the
remainder include enkephalinergic and GABAergic populations.

Functionally, NRM contains the canonical RVM ON/OFF/NEUTRAL cell trichotomy:
ON cells (~25%) increase firing just before nocifensive reflex — pronociceptive,
facilitating spinal pain transmission;
OFF cells (~25%) decrease firing just before reflex — antinociceptive, gating
spinal pain transmission;
NEUTRAL cells (~50%) — most of which are 5-HT — show no nocifensive response
but tonically modulate dorsal-horn nociceptive transmission.

Serotonergic modulation of pain is bi-directional through multiple receptor
subtypes (5-HT1A, 5-HT2A, 5-HT3, 5-HT7), and ultimately produces context-
dependent inhibition or facilitation. Chronic stress shifts NRM toward
descending facilitation, contributing to centralized pain syndromes.

NRM also sends ascending projections to forebrain sites and modulates
attention, mood, and integration of pain affect with sensory-discriminative
pain. NRM is closely coupled with PAG (PAG → NRM → spinal cord cascade)
and with locus coeruleus.

In Nova's substrate this is the second-tier descending pain modulator (under
PAG/DescendingPainGate); generates the spinal-level signal that gates
nociceptive ascending traffic.

KEY FINDINGS
============
1. NRM contains bulbospinal serotonergic neurons that descend to spinal dorsal
   horn and tonically modulate nociceptive transmission — [Mason 2001;
    Bowker et al., reviewed in ScienceDirect "Nucleus Raphe Magnus" overview]
2. Approximately 23% of NRM neurons are 5-HT, predominantly NEUTRAL cells;
   ON and OFF cells are mostly non-serotonergic — [Gao Mason 2000, J Neurophysiol
    84:1719-1725, "Serotonergic Raphe Magnus Cells That Respond to Noxious
    Tail Heat Are Not on or off Cells"]
3. RVM/NRM ON/OFF/NEUTRAL cell trichotomy mediates bi-directional descending
   pain modulation — [reviewed Frontiers Pharmacol 2023, doi:10.3389/fphar.2023.1159753,
    "Bulbospinal nociceptive ON and OFF cells related neural circuits and
    transmitters"]
4. Optogenetic activation of brainstem serotonergic neurons induces persistent
   pain sensitization in some contexts — descending 5-HT can be facilitatory —
   [Cai et al. 2014, Mol Pain 10:70, doi:10.1186/1744-8069-10-70]
5. Molecular depletion of descending serotonin unmasks novel facilitatory
   role in development of persistent pain — [Wei et al. 2010, J Neurosci
    30:8624-8636, doi:10.1523/JNEUROSCI.5389-09.2010]

INPUTS (from prior_results)
============================
- DescendingPainGate.inhibitory_drive
- DescendingPainGate.facilitatory_drive
- DescendingPainGate.opioid_tone
- DescendingPainGate.chronic_facilitation
- PeriaqueductalDefenseRouter.vlPAG_drive
- DorsalRapheSerotonin.serotonin_drive
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- nrm_5ht_drive (0.0-1.0): NRM serotonergic output proxy
- on_cell_drive (0.0-1.0): pronociceptive cell drive
- off_cell_drive (0.0-1.0): antinociceptive cell drive
- net_descending_modulation (signed -1..+1): + = facilitation, - = inhibition
- spinal_5ht_release (0.0-1.0): spinal cord 5-HT release proxy
- centralized_pain_drift (bool): chronic facilitatory shift
- bidirectional_balance (str): "inhibitory" | "facilitatory" | "neutral"
- descending_facilitatory_shift (bool): chronic pain windup marker
- rvm_serotonin_ascending_mood (0.0-1.0): forebrain 5-HT projection for mood

brain_runner enrichment:
    nrm = all_results.get("MedullaryRapheMagnus", {})
    if nrm:
        enrichments["brain_nrm_5ht"] = nrm.get("nrm_5ht_drive", 0.5)
        enrichments["brain_on_cell"] = nrm.get("on_cell_drive", 0.0)
        enrichments["brain_off_cell"] = nrm.get("off_cell_drive", 0.0)
        enrichments["brain_descending_balance"] = nrm.get("bidirectional_balance", "neutral")
"""

from brain.base_mechanism import BrainMechanism


class MedullaryRapheMagnus(BrainMechanism):
    BASELINE_5HT = 0.40
    CENTRALIZED_THRESHOLD_TICKS = 60
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="MedullaryRapheMagnus",
            human_analog="Nucleus raphe magnus descending 5-HT modulator",
            layer="foundational",
        )
        self.state.setdefault("nrm_5ht_drive", self.BASELINE_5HT)
        self.state.setdefault("on_cell_drive", 0.20)
        self.state.setdefault("off_cell_drive", 0.20)
        self.state.setdefault("net_descending_modulation", 0.0)
        self.state.setdefault("spinal_5ht_release", self.BASELINE_5HT)
        self.state.setdefault("centralized_pain_drift", False)
        self.state.setdefault("bidirectional_balance", "neutral")
        self.state.setdefault("descending_facilitatory_shift", False)
        self.state.setdefault("rvm_serotonin_ascending_mood", 0.40)
        self.state.setdefault("facilitatory_streak", 0)
        self.state.setdefault("recent_5ht", [])
        self.state.setdefault("tick_count", 0)

    def _on_cell_target(self, facilitation: float, chronic_fac: bool) -> float:
        """ON cells: pronociceptive, recruited under facilitation conditions."""
        target = facilitation * 0.7
        if chronic_fac:
            target += 0.20
        return min(1.0, target)

    def _off_cell_target(self, inhibition: float, opioid_tone: float, vlpag_drive: float) -> float:
        """OFF cells: antinociceptive, recruited under SIA / opioid-engaged states / vlPAG drive."""
        return min(1.0, inhibition * 0.6 + opioid_tone * 0.4 + vlpag_drive * 0.3)

    def _nrm_5ht_target(self, raphe_drive: float, vlpag: float, on_drive: float, off_drive: float) -> float:
        """NRM 5-HT firing target — convergent input from DRN, vlPAG, and local
        ON/OFF interneurons. NEUTRAL cells (most 5-HT) tonic regardless of ON/OFF.
        """
        target = self.BASELINE_5HT
        target += (raphe_drive - 0.5) * 0.3
        target += vlpag * 0.20
        # Mild contribution from ON/OFF (NEUTRAL 5-HT not gated by them)
        target += (on_drive - off_drive) * 0.05
        return max(0.0, min(1.0, target))

    def _net_modulation(self, on_drive: float, off_drive: float) -> float:
        """Net descending modulation: + = facilitation, - = inhibition."""
        return max(-1.0, min(1.0, on_drive - off_drive))

    def _classify_balance(self, net_mod: float) -> str:
        if net_mod > 0.20:
            return "facilitatory"
        if net_mod < -0.20:
            return "inhibitory"
        return "neutral"

    def _spinal_release(self, nrm_5ht: float, balance: str) -> float:
        """Spinal cord 5-HT release at dorsal horn terminals.
        Same molecular release but receptor context determines effect.
        """
        return min(1.0, nrm_5ht * 1.05)

    def _ascending_mood_effect(self, nrm_5ht: float, net_mod: float) -> float:
        """NRM 5-HT ascending projections to forebrain modulate mood.
        High facilitatory state reduces forebrain 5-HT (pain competes with mood).
        """
        if net_mod > 0.3:
            return max(0.1, 0.45 - (net_mod - 0.3) * 0.4)
        return min(1.0, 0.40 + nrm_5ht * 0.5)

    def _detect_centralized_drift(self, streak: int) -> bool:
        return streak > self.CENTRALIZED_THRESHOLD_TICKS

    def _detect_facilitatory_shift(self, streak: int) -> bool:
        return streak > 40

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dpg = prior.get("DescendingPainGate", {})
        inhibitory = float(dpg.get("inhibitory_drive", 0.5))
        facilitatory = float(dpg.get("facilitatory_drive", 0.5))
        opioid_tone = float(dpg.get("opioid_tone", 0.0))
        chronic_fac = bool(dpg.get("chronic_facilitation", False))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        vlpag = float(pdr.get("vlPAG_drive", 0.0))

        drs = prior.get("DorsalRapheSerotonin", {})
        raphe_drive = float(drs.get("serotonin_drive", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- ON/OFF cell drives ---
        on_target = self._on_cell_target(facilitatory, chronic_fac)
        off_target = self._off_cell_target(inhibitory, opioid_tone, vlpag)

        prev_on = float(self.state.get("on_cell_drive", 0.20))
        prev_off = float(self.state.get("off_cell_drive", 0.20))
        new_on = self._smooth(prev_on, on_target)
        new_off = self._smooth(prev_off, off_target)

        # --- NRM 5-HT target ---
        nrm_target = self._nrm_5ht_target(raphe_drive, vlpag, new_on, new_off)
        prev_nrm = float(self.state.get("nrm_5ht_drive", self.BASELINE_5HT))
        new_nrm = self._smooth(prev_nrm, nrm_target)

        # --- Net descending modulation ---
        net_mod = self._net_modulation(new_on, new_off)

        # --- Bidirectional balance classification ---
        balance = self._classify_balance(net_mod)

        # --- Spinal release ---
        spinal = self._spinal_release(new_nrm, balance)

        # --- Centralized pain drift detection ---
        prev_streak = int(self.state.get("facilitatory_streak", 0))
        if balance == "facilitatory":
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        centralized = self._detect_centralized_drift(streak)
        descending_shift = self._detect_facilitatory_shift(streak)

        # --- Ascending 5-HT to forebrain (mood modulation) ---
        ascending_mood = self._ascending_mood_effect(new_nrm, net_mod)

        recent = list(self.state.get("recent_5ht", []))
        recent.append(round(new_nrm, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nrm_5ht_drive"] = round(new_nrm, 4)
        self.state["on_cell_drive"] = round(new_on, 4)
        self.state["off_cell_drive"] = round(new_off, 4)
        self.state["net_descending_modulation"] = round(net_mod, 4)
        self.state["spinal_5ht_release"] = round(spinal, 4)
        self.state["centralized_pain_drift"] = centralized
        self.state["bidirectional_balance"] = balance
        self.state["descending_facilitatory_shift"] = descending_shift
        self.state["rvm_serotonin_ascending_mood"] = round(ascending_mood, 4)
        self.state["facilitatory_streak"] = streak
        self.state["recent_5ht"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nrm_5ht_drive": round(new_nrm, 4),
            "on_cell_drive": round(new_on, 4),
            "off_cell_drive": round(new_off, 4),
            "net_descending_modulation": round(net_mod, 4),
            "spinal_5ht_release": round(spinal, 4),
            "centralized_pain_drift": centralized,
            "bidirectional_balance": balance,
            "descending_facilitatory_shift": descending_shift,
            "rvm_serotonin_ascending_mood": round(ascending_mood, 4),
        }
