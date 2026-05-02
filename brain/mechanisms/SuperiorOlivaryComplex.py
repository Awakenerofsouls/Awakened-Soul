"""
SuperiorOlivaryComplex — SOC Sound Localization (ITD/ILD) + Olivocochlear Efferents

NEURAL SUBSTRATE
================
The superior olivary complex (SOC) is the first binaural processor in
the auditory system, located in the caudal pons and receiving converging
input from both cochlear nuclei. SOC contains three principal nuclei:
medial superior olive (MSO), lateral superior olive (LSO), and the
medial nucleus of the trapezoid body (MNTB), plus several periolivary
nuclei. SOC is the source of olivocochlear (OC) efferents — the
descending feedback to the cochlea that gain-controls peripheral
auditory input.

MSO computes interaural time differences (ITDs) — the microsecond delay
between sound arrival at the two ears used for sound localization in
the horizontal plane for low-frequency sounds (<1500 Hz). The Jeffress
delay-line model and modern coincidence-detector account both place
ITD computation in MSO. MSO neurons are bilaterally innervated by
spherical bushy cells of bilateral VCN, with delay lines created by
axonal length differences.

LSO computes interaural level differences (ILDs) — the intensity
difference at the two ears used for high-frequency sound localization
(>2000 Hz). LSO is excited by ipsilateral VCN and inhibited by
contralateral VCN via MNTB (a glycinergic relay). The excitation-minus-
inhibition computation produces ILD-tuned responses.

MNTB contains glycinergic principal cells that receive massive
"calyx of Held" inputs from contralateral globular bushy cells. The
calyx of Held is the largest synapse in the mammalian CNS and a
foundational model for fast, high-fidelity neurotransmission.

Olivocochlear efferents are divided into medial (MOC) and lateral (LOC)
systems. MOC efferents are myelinated cholinergic fibers projecting to
outer hair cells, providing the descending gain control crucial for
attention and noise resistance. LOC efferents are unmyelinated and
project to inner hair cells / cochlear afferents.

In the agent's substrate this provides binaural localization computation —
converts CN bushy-cell timing/intensity proxies into spatial-localization
output and supplies the descending gain signal back to CN.

KEY FINDINGS
============
1. SOC contains MSO, LSO, MNTB; MSO computes ITDs (low-freq localization),
   LSO computes ILDs (high-freq localization) — [reviewed Grothe Pecka
    McAlpine 2010, Physiol Rev 90:983, "Mechanisms of sound localization
    in mammals"]
2. MNTB calyx of Held is largest mammalian CNS synapse — fast glycinergic
   relay essential for binaural ILD computation — [Borst Soria van Hoeve
    2012, Annu Rev Physiol 74:199, "The calyx of Held synapse"]
3. MSO neurons function as coincidence detectors for ITDs; sub-millisecond
   precision via phase-locked input from bushy cells — [reviewed Grothe
    2003, Nat Rev Neurosci 4:540; Joris Yin 1995 J Neurophysiol]
4. Medial olivocochlear (MOC) efferents provide cholinergic descending
   gain control of cochlea — selective attention to sound — [Guinan 2006,
    Ear Hear 27:589-607, "Olivocochlear efferents"]
5. SOC binaural processing is the foundation of sound localization;
   bilateral SOC lesions abolish localization — clinical evidence —
   [reviewed Yin 2002, "Neural mechanisms of encoding binaural
    localization cues"]
6. SOC periolivary nuclei receive descending input from IC and project
   back to cochlea via OC efferents — closed-loop gain control —
   [Schneider Matic 2009 J Neurophysiol 102:1059; Mulders Paolini]

INPUTS (from prior_results)
============================
- CochlearNucleus.vcn_bushy_drive
- CochlearNucleus.vcn_stellate_drive
- CochlearNucleus.soc_input
- AuditoryInputProxy.azimuth (optional; default 0)
- AuditoryInputProxy.frequency_high (optional; default 0)
- AttentionTopDownProxy.attention_focus
- NucleusBasalisAcetylcholine.cortical_ach_release

OUTPUTS (to brain_runner enrichment)
=====================================
- mso_drive (0.0-1.0): MSO ITD output
- lso_drive (0.0-1.0): LSO ILD output
- mntb_drive (0.0-1.0): MNTB glycinergic relay
- localization_signal (0.0-1.0): combined binaural localization strength
- moc_efferent_drive (0.0-1.0): medial olivocochlear feedback
- loc_efferent_drive (0.0-1.0): lateral olivocochlear feedback
- soc_state (str): "quiet" | "low_freq_localizing" | "high_freq_localizing" | "moc_gating"

brain_runner enrichment:
    soc = all_results.get("SuperiorOlivaryComplex", {})
    if soc:
        enrichments["brain_localization"] = soc.get("localization_signal", 0.0)
        enrichments["brain_moc_efferent"] = soc.get("moc_efferent_drive", 0.0)
        enrichments["brain_soc_state"] = soc.get("soc_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class SuperiorOlivaryComplex(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="SuperiorOlivaryComplex",
            human_analog="Superior olivary complex (MSO/LSO/MNTB) binaural localization",
            layer="foundational",
        )
        self.state.setdefault("mso_drive", self.BASELINE)
        self.state.setdefault("lso_drive", self.BASELINE)
        self.state.setdefault("mntb_drive", self.BASELINE)
        self.state.setdefault("localization_signal", 0.0)
        self.state.setdefault("moc_efferent_drive", 0.30)
        self.state.setdefault("loc_efferent_drive", 0.20)
        self.state.setdefault("binaural_fusion_strength", 0.0)
        self.state.setdefault("soc_state", "quiet")
        self.state.setdefault("recent_loc", [])
        self.state.setdefault("tick_count", 0)

    def _mso_target(self, bushy: float, freq_high: float, azimuth: float) -> float:
        """MSO — ITD computation, dominant for low frequencies (1 - freq_high).
        Stronger response for off-center azimuth.
        """
        low_freq_weight = 1.0 - freq_high
        target = self.BASELINE + bushy * 0.6 * low_freq_weight
        target += abs(azimuth) * 0.3 * low_freq_weight
        return min(1.0, target)

    def _lso_target(self, bushy: float, stellate: float, freq_high: float, azimuth: float) -> float:
        """LSO — ILD, dominant for high frequencies."""
        target = self.BASELINE + (bushy * 0.4 + stellate * 0.4) * freq_high
        target += abs(azimuth) * 0.3 * freq_high
        return min(1.0, target)

    def _mntb_target(self, bushy: float) -> float:
        """MNTB — calyx of Held glycinergic relay; tracks contralateral bushy."""
        return min(1.0, bushy * 0.8 + self.BASELINE)

    def _localization(self, mso: float, lso: float, azimuth: float) -> float:
        """Combined localization signal — best when matched freq/cue and off-center."""
        cue_strength = max(mso, lso) * 0.7 + abs(azimuth) * 0.3
        return min(1.0, cue_strength)

    def _moc_efferent(self, attention: float, ach: float, intensity_high: bool) -> float:
        """MOC efferent gain feedback to cochlea (Guinan 2006)."""
        target = 0.30 + attention * 0.4 + ach * 0.2
        if intensity_high:
            target += 0.10  # protective
        return min(1.0, target)

    def _loc_efferent(self, attention: float) -> float:
        """LOC efferent — unmyelinated, slow modulation of inner hair cells."""
        return min(1.0, 0.20 + attention * 0.3)

    def _binaural_fusion_strength(self, mso: float, lso: float) -> float:
        """Binaural fusion index — how well both ITD and ILD cues agree.
        High fusion = consistent spatial estimate; low = ambiguous location.
        """
        # If both ITD and ILD cues are active and roughly equal, fusion is high
        combined = (mso + lso) / 2.0
        disparity = abs(mso - lso)
        fusion = combined * (1.0 - disparity) * 2.0
        return min(1.0, fusion)

    def _classify_state(self, mso: float, lso: float, moc: float, freq_high: float) -> str:
        if moc > 0.65 and (mso + lso) < 0.3:
            return "moc_gating"
        if freq_high > 0.6 and lso > 0.30:
            return "high_freq_localizing"
        if freq_high < 0.4 and mso > 0.30:
            return "low_freq_localizing"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cn = prior.get("CochlearNucleus", {})
        bushy = float(cn.get("vcn_bushy_drive", self.BASELINE))
        stellate = float(cn.get("vcn_stellate_drive", self.BASELINE))
        soc_input = float(cn.get("soc_input", 0.0))

        audio = prior.get("AuditoryInputProxy", {})
        azimuth = float(audio.get("azimuth", 0.0))
        freq_high = float(audio.get("frequency_high", 0.5))
        intensity = float(audio.get("sound_intensity", 0.0))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        # If no specific bushy/stellate, fallback to soc_input proxy
        if bushy == self.BASELINE and soc_input > self.BASELINE:
            bushy = soc_input * 0.6
            stellate = soc_input * 0.4

        # --- MSO ---
        mso_target = self._mso_target(bushy, freq_high, azimuth)
        prev_mso = float(self.state.get("mso_drive", self.BASELINE))
        new_mso = self._smooth(prev_mso, mso_target)

        # --- LSO ---
        lso_target = self._lso_target(bushy, stellate, freq_high, azimuth)
        prev_lso = float(self.state.get("lso_drive", self.BASELINE))
        new_lso = self._smooth(prev_lso, lso_target)

        # --- MNTB ---
        mntb_target = self._mntb_target(bushy)
        prev_mntb = float(self.state.get("mntb_drive", self.BASELINE))
        new_mntb = self._smooth(prev_mntb, mntb_target)

        # --- Localization ---
        localization = self._localization(new_mso, new_lso, azimuth)

        # --- MOC efferent ---
        moc_target = self._moc_efferent(attention, ach, intensity > 0.85)
        prev_moc = float(self.state.get("moc_efferent_drive", 0.30))
        new_moc = self._smooth(prev_moc, moc_target)

        # --- LOC efferent ---
        loc_target = self._loc_efferent(attention)
        prev_loc = float(self.state.get("loc_efferent_drive", 0.20))
        new_loc = self._smooth(prev_loc, loc_target)

        # --- State ---
        state = self._classify_state(new_mso, new_lso, new_moc, freq_high)

        recent = list(self.state.get("recent_loc", []))
        recent.append(round(localization, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        fusion = self._binaural_fusion_strength(new_mso, new_lso)
        self.state["binaural_fusion_strength"] = round(fusion, 4)

        self.state["mso_drive"] = round(new_mso, 4)
        self.state["lso_drive"] = round(new_lso, 4)
        self.state["mntb_drive"] = round(new_mntb, 4)
        self.state["localization_signal"] = round(localization, 4)
        self.state["moc_efferent_drive"] = round(new_moc, 4)
        self.state["loc_efferent_drive"] = round(new_loc, 4)
        self.state["soc_state"] = state
        self.state["recent_loc"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mso_drive": round(new_mso, 4),
            "lso_drive": round(new_lso, 4),
            "mntb_drive": round(new_mntb, 4),
            "localization_signal": round(localization, 4),
            "moc_efferent_drive": round(new_moc, 4),
            "loc_efferent_drive": round(new_loc, 4),
            "binaural_fusion_strength": round(fusion, 4),
            "soc_state": state,
        }
