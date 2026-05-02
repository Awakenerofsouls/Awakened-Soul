"""
PeriaqueductalDefenseRouter — PAG Columnar Defense Reaction Router

NEURAL SUBSTRATE
================
The periaqueductal gray (PAG) of the midbrain is organized into longitudinal
columns surrounding the cerebral aqueduct: dorsomedial (dmPAG), dorsolateral
(dlPAG), lateral (lPAG), and ventrolateral (vlPAG). These columns are
functionally specialized for distinct components of defensive behavior, and
together implement the brain's central defense reaction selector.

Active coping (escapable threat):
 • dlPAG and lPAG drive flight/fight responses, including escape attempts,
   sympathetic activation, and stress-induced analgesia. Electrical or
   optogenetic activation of dlPAG/lPAG produces flight, jumping, and the
   classical "fight-or-flight" cardiovascular profile (tachycardia,
   hypertension, sympathoexcitation).

Passive coping (inescapable threat):
 • vlPAG drives freezing — immobility, bradycardia, opioid-mediated
   analgesia, and hyporesponsivity. vlPAG lesion abolishes conditioned
   freezing in fear paradigms. vlPAG also contributes to sleep regulation
   and pain modulation through its connections to RVM.

dmPAG (newer literature):
 • Recent work (Tovote, Esposito, Botta et al., 2016 Nature) further
   refined the columnar model — defensive behavior emerges from dynamic
   coordination across columns rather than strict region-to-action mapping,
   but the active-vs-passive coping axis (dl/l-PAG vs vlPAG) remains the
   canonical organizing principle.

PAG receives convergent input from amygdala (CeA primarily to vlPAG;
medial amygdala to dlPAG), hypothalamus (DMH to dlPAG/lPAG for active
coping), and cortical regions (mPFC for top-down control). It outputs
through descending projections to RVM (pain modulation), nucleus retroambiguus
(vocalization), and brainstem cardiovascular nuclei (autonomic component
of defense).

KEY FINDINGS
============
1. PAG is organized into longitudinal functional columns: dmPAG, dlPAG,
   lPAG, vlPAG with distinct afferent/efferent patterns —
   [Bandler Carrive 1988; reviewed in StatPearls Periaqueductal Gray
    NBK554391]
2. Distinct PAG regions mediate acquisition vs expression of conditioned
   defensive responses (vlPAG necessary for freezing) —
   [Vianna et al. 1998, J Neurosci 18(9):3426]
3. dlPAG/lPAG drives active coping (flight/fight); vlPAG drives passive
   coping (freezing) — comparison of dlPAG vs vlPAG stimulation —
   [Vianna Brandao 2003, PubMed 11742247, Behav Brain Res]
4. Sparse genetically-defined PAG neurons refine the canonical columnar
   role — defense behavior emerges from dynamic across-column coordination
   — [McNally Johansen et al. 2022, PMC9224993, eLife]
5. Prefrontal-PAG circuit can override passive coping endocrine response,
   shifting toward active coping — [Wallace Bhattacharya 2022,
    PNAS doi:10.1073/pnas.2210783119]

INPUTS (from prior_results)
============================
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- VitalCoreRegulator.survival_threat_level
- VitalCoreRegulator.sympathetic_tone
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- StressActivationAxis.stress_active
- DescendingPainGate.stress_induced_analgesia (vlPAG-RVM coupling)
- AttachmentLongingGenerator.separation_distress (CeA-PAG drive)

OUTPUTS (to brain_runner enrichment)
=====================================
- defense_mode (str): "none" | "fight" | "flight" | "freeze" | "tonic_immobility"
- dlPAG_drive (0.0-1.0): active coping column
- lPAG_drive (0.0-1.0): active coping column
- vlPAG_drive (0.0-1.0): passive coping column
- escapability_estimate (0.0-1.0): perceived escapability of threat
- coping_strategy (str): "active" | "passive" | "neutral"
- prefrontal_override_active (bool): mPFC top-down active coping recruitment

brain_runner enrichment block:
    pdr = all_results.get("PeriaqueductalDefenseRouter", {})
    if pdr:
        enrichments["brain_defense_mode"] = pdr.get("defense_mode", "none")
        enrichments["brain_dlpag_drive"] = pdr.get("dlPAG_drive", 0.0)
        enrichments["brain_vlpag_drive"] = pdr.get("vlPAG_drive", 0.0)
        enrichments["brain_escapability"] = pdr.get("escapability_estimate", 0.5)
        enrichments["brain_coping_strategy"] = pdr.get("coping_strategy", "neutral")
"""

from brain.base_mechanism import BrainMechanism


class PeriaqueductalDefenseRouter(BrainMechanism):
    """
    PAG columnar defense router.

    Routes integrated threat signals into one of four defense modes — none,
    fight, flight, freeze, or tonic immobility — based on threat magnitude,
    perceived escapability, and arousal state. Models columnar specialization
    per Bandler-Carrive and refines per McNally-Johansen 2022 eLife dynamic
    cross-column coordination.
    """

    THREAT_THRESHOLD = 0.40
    ACTIVE_COPING_AROUSAL_MIN = 0.50
    PASSIVE_COPING_AROUSAL_MAX = 0.45
    HIGH_THREAT_ESCAPABLE = 0.55
    EXTREME_THREAT = 0.85

    DLPAG_BASELINE = 0.0
    VLPAG_BASELINE = 0.05  # mild baseline tone for pain modulation / sleep regulation
    LPAG_BASELINE = 0.0

    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="PeriaqueductalDefenseRouter",
            human_analog="Periaqueductal gray columnar defense router",
            layer="foundational",
        )
        self.state.setdefault("defense_mode", "none")
        self.state.setdefault("dlPAG_drive", self.DLPAG_BASELINE)
        self.state.setdefault("lPAG_drive", self.LPAG_BASELINE)
        self.state.setdefault("vlPAG_drive", self.VLPAG_BASELINE)
        self.state.setdefault("escapability_estimate", 0.6)
        self.state.setdefault("coping_strategy", "neutral")
        self.state.setdefault("prefrontal_override_active", False)
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("freeze_duration_ticks", 0)
        self.state.setdefault("tick_count", 0)

    def _estimate_escapability(self, threat: float, arousal: float, sympathetic: float) -> float:
        """Higher arousal + higher sympathetic_tone = more escapable estimate.
        Very high threat with low arousal = inescapable.
        """
        if arousal < 0.30 and threat > 0.6:
            return 0.10
        if arousal > 0.70 and sympathetic > 0.65:
            return 0.85
        # default monotonic
        return max(0.05, min(0.95, 0.40 + (arousal - 0.5) * 0.6 + (sympathetic - 0.5) * 0.3))

    def _select_mode(self, threat: float, escapability: float, arousal: float, valence_intensity: float) -> str:
        """Select defense mode based on threat magnitude × escapability × arousal."""
        if threat < self.THREAT_THRESHOLD:
            return "none"
        # Tonic immobility: extreme threat + collapse-low arousal
        if threat > self.EXTREME_THREAT and arousal < 0.25:
            return "tonic_immobility"
        # Active coping: high arousal + escapable
        if arousal >= self.ACTIVE_COPING_AROUSAL_MIN and escapability > self.HIGH_THREAT_ESCAPABLE:
            # Fight if intense valence + extremely high threat; otherwise flight
            if valence_intensity > 0.75 and threat > 0.70:
                return "fight"
            return "flight"
        # Passive coping: low arousal or low escapability
        if arousal <= self.PASSIVE_COPING_AROUSAL_MAX or escapability < 0.40:
            return "freeze"
        # Mid-state ambiguous — default flight if threat is real
        return "flight"

    def _column_drives_for_mode(self, mode: str, threat: float):
        """Map mode to column drives matching Bandler-Carrive functional anatomy."""
        if mode == "fight":
            return (0.95, 0.85, self.VLPAG_BASELINE)  # dlPAG, lPAG, vlPAG
        if mode == "flight":
            return (0.80, 0.95, self.VLPAG_BASELINE)
        if mode == "freeze":
            return (self.DLPAG_BASELINE, 0.10, 0.85)
        if mode == "tonic_immobility":
            return (self.DLPAG_BASELINE, self.LPAG_BASELINE, 0.95)
        return (self.DLPAG_BASELINE, self.LPAG_BASELINE, self.VLPAG_BASELINE)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        dpg = prior.get("DescendingPainGate", {})
        sia_active = bool(dpg.get("stress_induced_analgesia", False))

        attach = prior.get("AttachmentLongingGenerator", {})
        sep_distress = float(attach.get("separation_distress", 0.0))

        # --- Compose total threat magnitude ---
        threat_magnitude = max(
            survival_threat,
            valence_intensity if threat_signal else 0.0,
        )
        # Separation distress can drive PAG defense response (CeA→PAG)
        if sep_distress > 0.5:
            threat_magnitude = max(threat_magnitude, sep_distress * 0.7)

        # --- Estimate escapability (combines arousal + sympathetic + stress) ---
        escapability = self._estimate_escapability(threat_magnitude, tonic, symp_tone)

        # --- mPFC prefrontal override: stress-active without flight = prefrontal override possible ---
        prefrontal_override = (
            stress_active
            and threat_magnitude > 0.5
            and tonic > 0.65
            and not threat_signal
        )
        if prefrontal_override:
            # Override pushes the system toward active coping (Wallace 2022)
            escapability = min(0.95, escapability + 0.20)

        # --- Mode selection ---
        mode = self._select_mode(threat_magnitude, escapability, tonic, valence_intensity)

        # --- Column drive targets ---
        dl_target, l_target, vl_target = self._column_drives_for_mode(mode, threat_magnitude)

        # If SIA active, vlPAG is engaged for opioid analgesia even outside freeze
        if sia_active:
            vl_target = max(vl_target, 0.5)

        prev_dl = float(self.state.get("dlPAG_drive", self.DLPAG_BASELINE))
        prev_l = float(self.state.get("lPAG_drive", self.LPAG_BASELINE))
        prev_vl = float(self.state.get("vlPAG_drive", self.VLPAG_BASELINE))
        new_dl = self._smooth(prev_dl, dl_target)
        new_l = self._smooth(prev_l, l_target)
        new_vl = self._smooth(prev_vl, vl_target)

        # --- Coping strategy classification ---
        if mode in ("fight", "flight"):
            coping = "active"
        elif mode in ("freeze", "tonic_immobility"):
            coping = "passive"
        else:
            coping = "neutral"

        # --- Freeze duration tracking ---
        prev_freeze = int(self.state.get("freeze_duration_ticks", 0))
        if mode in ("freeze", "tonic_immobility"):
            freeze_duration = prev_freeze + 1
        else:
            freeze_duration = 0

        recent = list(self.state.get("recent_modes", []))
        recent.append(mode)
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Persist ---
        self.state["defense_mode"] = mode
        self.state["dlPAG_drive"] = round(new_dl, 4)
        self.state["lPAG_drive"] = round(new_l, 4)
        self.state["vlPAG_drive"] = round(new_vl, 4)
        self.state["escapability_estimate"] = round(escapability, 4)
        self.state["coping_strategy"] = coping
        self.state["prefrontal_override_active"] = prefrontal_override
        self.state["freeze_duration_ticks"] = freeze_duration
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "defense_mode": mode,
            "dlPAG_drive": round(new_dl, 4),
            "lPAG_drive": round(new_l, 4),
            "vlPAG_drive": round(new_vl, 4),
            "escapability_estimate": round(escapability, 4),
            "coping_strategy": coping,
            "prefrontal_override_active": prefrontal_override,
            "freeze_duration_ticks": freeze_duration,
        }
