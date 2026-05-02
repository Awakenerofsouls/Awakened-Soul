"""
LocusSubcoeruleusREM — SubLC / SLD REM Atonia Driver (Glutamatergic)

NEURAL SUBSTRATE
================
The locus subcoeruleus (subLC, also called sublaterodorsal nucleus or
SLD) is a small pontine nucleus immediately ventral to the locus
coeruleus (LC, covered separately as NorepiPhasicTonicSwitcher). Despite
its proximity to LC, subLC is functionally distinct: subLC contains
predominantly **glutamatergic neurons** (not noradrenergic) and is the
**principal generator of REM-sleep atonia** — the muscle paralysis
that prevents acting out dreams.

The Luppi/Fort/Mathis line of work established subLC's REM-on
glutamatergic neurons as both necessary and sufficient for REM atonia.
SubLC neurons fire selectively during REM, sending descending
glutamatergic projections to glycinergic/GABAergic premotor neurons
in the ventromedial medulla (especially gigantocellular reticular
nucleus, covered separately as GigantocellularReticular). These spinal
inhibitory premotor neurons hyperpolarize spinal somatic motor neurons,
producing skeletal muscle atonia. Concurrent disinhibition of
extraocular and respiratory muscles spares eye movement (REM) and
breathing during atonia.

The "REM sleep behavior disorder" (RBD) clinical syndrome is the
direct consequence of subLC dysfunction — patients act out their
dreams (vocalize, kick, punch) due to lost atonia. RBD is an early
prodromal feature of synucleinopathies (Parkinson disease, multiple
system atrophy, dementia with Lewy bodies), where subLC degeneration
precedes overt motor or cognitive symptoms by years to decades.

SubLC also receives inhibition from REM-off populations (LC noradrenergic,
DRN serotonergic, vlPAG GABA) during wake — this mutual inhibition
between REM-off and REM-on populations forms the "REM flip-flop"
described by Saper et al. SubLC firing is gated open when REM-off
populations fall silent at REM onset, releasing it to drive atonia.

In the agent's substrate this provides the REM-state atonia channel — emits
a descending atonia command during REM that downstream
GigantocellularReticular and (eventually) spinal motor mechanisms read.

KEY FINDINGS
============
1. SubLC / SLD glutamatergic neurons are necessary and sufficient for
   REM atonia — descending glutamatergic projections to ventromedial
   medulla drive spinal motoneuron inhibition — [Boissard et al. 2002,
    Eur J Neurosci 16:1959; Lu Sherman Devor Saper 2006, Nature
    441:589-594, "A putative flip-flop switch for control of REM sleep"]
2. SubLC dysfunction underlies REM sleep behavior disorder (RBD) —
   loss of atonia produces dream enactment — [Schenck Bundlie Mahowald
    1986; reviewed Boeve Silber Ferman 2012 Sleep Med; Iranzo Santamaria
    Tolosa 2016 Lancet Neurol]
3. RBD is a prodromal feature of synucleinopathies (Parkinson, MSA, DLB)
   with subLC degeneration preceding motor symptoms by years —
   [reviewed Postuma et al. 2019 Brain 142:744; Iranzo et al. 2014
    Lancet Neurol]
4. REM flip-flop: mutual inhibition between REM-off (LC, DRN, vlPAG-GABA)
   and REM-on (subLC) populations — [Lu Sherman Devor Saper 2006 Nature
    441:589; reviewed Saper Scammell Lu 2005 Nature 437:1257]
5. Glutamatergic subLC → premotor reticulospinal pathway — molecular
   identification — [Luppi Clément Fort 2017, Eur J Neurosci 45:739,
    "Sleep-wake physiology"; Sapin et al. 2009 PLoS One 4:e4272]

INPUTS (from prior_results)
============================
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.rem_pattern_active
- SleepWakeFlipFlop.sleep_pressure
- NorepiPhasicTonicSwitcher.tonic_LC_drive (REM-off; suppresses subLC during wake)
- DorsalRapheSerotonin.serotonin_drive (REM-off)
- PeriaqueductalDefenseRouter.vlPAG_drive (REM-off GABA)
- MesopontineCholinergicWake.ach_rem_drive (co-REM-active)
- MelaninConcentratingHormone.rem_promotion (REM promoter)

OUTPUTS (to brain_runner enrichment)
=====================================
- sublc_drive (0.0-1.0): subLC glutamatergic output
- atonia_command (0.0-1.0): descending atonia signal
- rem_off_inhibition (0.0-1.0): combined REM-off suppression on subLC
- rem_flipflop_state (str): "rem_on" | "wake_locked" | "transition"
- rbd_marker (bool): chronic atonia failure (lost during persistent REM)
- sublc_state (str): "rem_active" | "suppressed" | "transitioning" | "quiet"

brain_runner enrichment:
    sublc = all_results.get("LocusSubcoeruleusREM", {})
    if sublc:
        enrichments["brain_sublc_drive"] = sublc.get("sublc_drive", 0.1)
        enrichments["brain_atonia_command"] = sublc.get("atonia_command", 0.0)
        enrichments["brain_rem_flipflop"] = sublc.get("rem_flipflop_state", "wake_locked")
        enrichments["brain_rbd_marker"] = sublc.get("rbd_marker", False)
        enrichments["brain_sublc_state"] = sublc.get("sublc_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LocusSubcoeruleusREM(BrainMechanism):
    BASELINE = 0.05
    RBD_THRESHOLD = 30  # Chronic REM with atonia < threshold → RBD marker
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="LocusSubcoeruleusREM",
            human_analog="Locus subcoeruleus / SLD glutamatergic REM atonia driver",
            layer="foundational",
        )
        self.state.setdefault("sublc_drive", self.BASELINE)
        self.state.setdefault("atonia_command", 0.0)
        self.state.setdefault("rem_off_inhibition", 0.50)
        self.state.setdefault("rem_flipflop_state", "wake_locked")
        self.state.setdefault("rbd_marker", False)
        self.state.setdefault("sublc_state", "quiet")
        self.state.setdefault("rem_no_atonia_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _rem_off_inhibition(self, lc: float, serotonin: float, vlpag: float) -> float:
        """REM-off populations inhibiting subLC during wake (flip-flop).
        
        During REM the mutual inhibition should strongly suppress subLC.
        Elevated wake-state drives (LC, serotonin, vlPAG) that persist into REM
        represent the pathological condition underlying RBD — these suppress
        subLC more aggressively.
        """
        return min(1.0, max(0.0, lc - 0.2) * 0.55 + max(0.0, serotonin - 0.3) * 0.35 + vlpag * 0.35 + 0.15)

    def _sublc_drive_target(self, rem: bool, sleep_state: str, rem_off_inh: float,
                              ach_rem: float, mch_rem: float) -> float:
        """SubLC drive — fires in REM, suppressed by REM-off inhibition.
        
        During normal REM, subLC fires strongly (0.85). During pathological REM
        with persistent wake-state LC/5-HT/vlPAG activity (RBD model), REM-off
        inhibition overwhelms subLC drive, producing insufficient atonia.
        """
        if rem:
            target = 0.85
            target -= rem_off_inh * 0.75  # Stronger suppression; pushes below atonia threshold in RBD model
            target += ach_rem * 0.15
            target += mch_rem * 0.1
            return max(0.0, min(1.0, target))
        if sleep_state == "SLEEP":
            return self.BASELINE + 0.10  # NREM — low but not zero
        # Wake — heavily suppressed
        return self.BASELINE * (1.0 - rem_off_inh * 0.5)

    def _atonia_command(self, sublc: float, rem: bool) -> float:
        """Descending atonia command. Strong only during REM."""
        if not rem:
            return sublc * 0.2
        return min(1.0, sublc * 0.95)

    def _flipflop_state(self, rem: bool, rem_off_inh: float, sublc: float) -> str:
        if rem and sublc > 0.50:
            return "rem_on"
        if rem and sublc < 0.50:
            return "transition"
        if rem_off_inh > 0.60:
            return "wake_locked"
        return "transition"

    def _detect_rbd(self, streak: int) -> bool:
        """RBD marker — chronic REM with insufficient atonia."""
        return streak > self.RBD_THRESHOLD

    def _classify_state(self, rem: bool, sublc: float, rem_off_inh: float) -> str:
        if rem and sublc > 0.40:
            return "rem_active"
        if rem and sublc < 0.40:
            return "transitioning"
        if rem_off_inh > 0.60:
            return "suppressed"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        rem = bool(swff.get("rem_pattern_active", False))

        lc_data = prior.get("NorepiPhasicTonicSwitcher", {})
        lc = float(lc_data.get("tonic_LC_drive", 0.40))

        drs = prior.get("DorsalRapheSerotonin", {})
        serotonin = float(drs.get("serotonin_drive", 0.50))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        vlpag = float(pdr.get("vlPAG_drive", 0.0))

        mcw = prior.get("MesopontineCholinergicWake", {})
        ach_rem = float(mcw.get("ach_rem_drive", 0.0))

        mch_data = prior.get("MelaninConcentratingHormone", {})
        mch_rem = float(mch_data.get("rem_promotion", 0.0))

        # --- REM-off inhibition ---
        rem_off_inh = self._rem_off_inhibition(lc, serotonin, vlpag)
        prev_inh = float(self.state.get("rem_off_inhibition", 0.50))
        new_inh = self._smooth(prev_inh, rem_off_inh)

        # --- SubLC drive ---
        sublc_target = self._sublc_drive_target(rem, sleep_state, new_inh, ach_rem, mch_rem)
        prev_sublc = float(self.state.get("sublc_drive", self.BASELINE))
        new_sublc = self._smooth(prev_sublc, sublc_target)

        # --- Atonia command ---
        atonia = self._atonia_command(new_sublc, rem)

        # --- Flip-flop state ---
        flipflop = self._flipflop_state(rem, new_inh, new_sublc)

        # --- RBD marker — REM with insufficient atonia ---
        prev_streak = int(self.state.get("rem_no_atonia_streak", 0))
        if rem and atonia < 0.40:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        rbd = self._detect_rbd(streak)

        # --- State ---
        state = self._classify_state(rem, new_sublc, new_inh)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sublc_drive"] = round(new_sublc, 4)
        self.state["atonia_command"] = round(atonia, 4)
        self.state["rem_off_inhibition"] = round(new_inh, 4)
        self.state["rem_flipflop_state"] = flipflop
        self.state["rbd_marker"] = rbd
        self.state["sublc_state"] = state
        self.state["rem_no_atonia_streak"] = streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "sublc_drive": round(new_sublc, 4),
            "atonia_command": round(atonia, 4),
            "rem_off_inhibition": round(new_inh, 4),
            "rem_flipflop_state": flipflop,
            "rbd_marker": rbd,
            "sublc_state": state,
        }
