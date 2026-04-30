"""
InferiorColliculusAuditory — IC Auditory Midbrain / PPI Relay / Threat-Sound Detector

NEURAL SUBSTRATE
================
The inferior colliculus (IC) is the principal auditory midbrain — a near-
obligatory relay for ascending lemniscal auditory input on the path from
brainstem auditory nuclei (cochlear nucleus, superior olivary complex,
nuclei of the lateral lemniscus) to medial geniculate nucleus (MGN) of
the auditory thalamus, and onward to auditory cortex. The IC is divided
into central nucleus (ICc, the lemniscal core), dorsal cortex (DC, also
called ICd), and lateral cortex (LC/external nucleus, ICl). ICc is
strongly tonotopic with isofrequency laminae; DC and LC are non-lemniscal,
multimodal, and integrate cortical descending input.

The IC is critical for sound localization (computing interaural cues
delivered from SOC) and for spectral integration. Beyond pure auditory
relay, IC is an obligate node for **prepulse inhibition (PPI)** of the
acoustic startle reflex — Fendt et al. (2001) mapped the brainstem
circuit as IC → superior colliculus → pedunculopontine/laterodorsal
tegmentum → caudal pontine reticular nucleus (PnC), where the prepulse
signal converges with startle-driving giant neurons of PnC to attenuate
the startle response. Lesions of IC, especially ICc, abolish acoustic
PPI; PPI is a translational marker of sensorimotor gating studied in
schizophrenia and PTSD models.

IC also sits within auditory threat-detection — auditory cortex, IC, and
amygdala form a bidirectional circuit in which IC receives top-down
modulation from auditory cortex (DC) and projects to amygdala via MGN
("low road" of LeDoux for fear conditioning) and via direct collateral
projections in some species. Threat-typed sounds (high-frequency
distress calls, rapid frequency modulation) preferentially activate
shell IC subnuclei.

In {{AGENT_NAME}}'s substrate this provides the auditory midbrain integrator —
converts auditory input proxies (intensity, prepulse-detection,
threat-typed flags) into a relay output to MGN-equivalent and a
PPI-signal that gates startle.

KEY FINDINGS
============
1. Acoustic prepulses for PPI are relayed through the inferior colliculus —
   IC is part of brainstem PPI circuit including SC, PPTg/LDTg, SNR, PnC —
   [Fendt Li Yeomans 2001, Psychopharmacology 156:216-224, "Brain stem
    circuits mediating prepulse inhibition of the startle reflex"
    PMID 11549224]
2. IC lesions impair acoustic PPI; LN/DC lesions elevate startle and
   alter PPI intensity functions — [Leitner Cohen 1985, Behav Neural Biol;
    Li Frost 1996/2000, Hear Res — IC plasticity and PPI; Leitner
    Powers 1990 PMID 2285482]
3. IC contains tonotopic central nucleus (ICc, lemniscal) and non-
   lemniscal dorsal/lateral cortices that integrate descending auditory
   cortical input — [reviewed Winer Schreiner 2005, "The Inferior
    Colliculus" Springer]
4. Inhibitory (GABAergic) projections from IC to PnC are critical for
   PPI — pharmacological disinhibition of IC abolishes PPI — [Yeomans
    Frankland 1995, Brain Res Rev; Carlson Willott 1996]
5. IC participates in fear-conditioning auditory pathway (MGN → amygdala
   "low road") — IC plasticity tracks aversive auditory associative
   learning — [Weinberger 2007 Hear Res; reviewed LeDoux 2000 Annu Rev]

INPUTS (from prior_results)
============================
- AuditoryInputProxy.sound_intensity (optional; default 0)
- AuditoryInputProxy.prepulse_active (optional; default False)
- AuditoryInputProxy.threat_sound_flag (optional; default False)
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- MultisensoryStartleMapper.startle_amplitude
- ArousalRegulator.tonic_level
- NucleusBasalisAcetylcholine.cortical_ach_release

OUTPUTS (to brain_runner enrichment)
=====================================
- ic_central_drive (0.0-1.0): ICc lemniscal output
- ic_shell_drive (0.0-1.0): DC/LC non-lemniscal output
- mgn_relay (0.0-1.0): IC → MGN auditory thalamic relay
- ppi_signal (0.0-1.0): prepulse-inhibition signal to PnC
- threat_sound_relay (0.0-1.0): IC→amygdala low-road
- ic_state (str): "tonic" | "ppi_engaged" | "threat_relay" | "quiet"

brain_runner enrichment:
    ic = all_results.get("InferiorColliculusAuditory", {})
    if ic:
        enrichments["brain_ic_central"] = ic.get("ic_central_drive", 0.2)
        enrichments["brain_mgn_relay"] = ic.get("mgn_relay", 0.0)
        enrichments["brain_ppi_signal"] = ic.get("ppi_signal", 0.0)
        enrichments["brain_threat_sound_relay"] = ic.get("threat_sound_relay", 0.0)
        enrichments["brain_ic_state"] = ic.get("ic_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class InferiorColliculusAuditory(BrainMechanism):
    BASELINE_DRIVE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="InferiorColliculusAuditory",
            human_analog="Inferior colliculus auditory midbrain / PPI relay",
            layer="foundational",
        )
        self.state.setdefault("ic_central_drive", self.BASELINE_DRIVE)
        self.state.setdefault("ic_shell_drive", 0.15)
        self.state.setdefault("mgn_relay", 0.0)
        self.state.setdefault("ppi_signal", 0.0)
        self.state.setdefault("threat_sound_relay", 0.0)
        self.state.setdefault("azimuth_integration", 0.0)
        self.state.setdefault("ic_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ic_central_target(self, intensity: float, arousal: float) -> float:
        """ICc lemniscal — scales with sound intensity and arousal gain."""
        target = self.BASELINE_DRIVE + intensity * 0.6
        target += max(0.0, arousal - 0.5) * 0.2
        return min(1.0, target)

    def _ic_shell_target(self, intensity: float, threat_sound: bool, ach: float,
                         valence: float) -> float:
        """DC/LC shell — multimodal/descending. Engaged on threat-flagged sounds
        and ACh-driven attention.
        """
        target = 0.15 + intensity * 0.3
        if threat_sound:
            target += valence * 0.4
        target += ach * 0.2
        return min(1.0, target)

    def _mgn_relay(self, central: float, shell: float) -> float:
        """IC → MGN auditory thalamic relay."""
        return min(1.0, central * 0.7 + shell * 0.3)

    def _ppi_signal(self, prepulse: bool, central: float, intensity: float) -> float:
        """Prepulse inhibition signal to PnC (Fendt 2001).
        Active when a weak prepulse precedes a startle-eliciting sound.
        """
        if not prepulse:
            return 0.0
        # Effective PPI requires moderate intensity prepulse and intact ICc
        return min(1.0, central * 0.6 + intensity * 0.4)

    def _threat_sound_relay(self, threat_sound: bool, threat: bool, valence: float,
                             shell: float) -> float:
        """IC→MGN→amygdala low-road for threat-typed auditory input."""
        if not (threat_sound or threat):
            return 0.0
        return min(1.0, valence * 0.5 + shell * 0.5)

    def _azimuth_integration(self, central: float, shell: float,
                              soc_input: float) -> float:
        """IC receives azimuth/ITD-related input from SOC — integrates
        sound-source azimuth estimate into spatial orientation signal.
        """
        # ICc fires more to contralateral sounds (high ITD values)
        # SOC provides explicit azimuth; IC pools SOC + own auditory input
        combined = central * 0.4 + shell * 0.2 + soc_input * 0.4
        return min(1.0, combined)

    def _classify_state(self, ppi: float, threat_relay: float, central: float) -> str:
        if ppi > 0.30:
            return "ppi_engaged"
        if threat_relay > 0.35:
            return "threat_relay"
        if central > 0.35:
            return "tonic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        audio = prior.get("AuditoryInputProxy", {})
        intensity = float(audio.get("sound_intensity", 0.0))
        prepulse = bool(audio.get("prepulse_active", False))
        threat_sound = bool(audio.get("threat_sound_flag", False))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        startle_data = prior.get("MultisensoryStartleMapper", {})
        startle = float(startle_data.get("startle_amplitude", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        # If startle is firing and no explicit intensity proxy, use startle as proxy
        if intensity == 0.0 and startle > 0.30:
            intensity = startle

        # --- ICc ---
        central_target = self._ic_central_target(intensity, tonic)
        prev_central = float(self.state.get("ic_central_drive", self.BASELINE_DRIVE))
        new_central = self._smooth(prev_central, central_target)

        # --- IC shell ---
        shell_target = self._ic_shell_target(intensity, threat_sound, ach, valence_intensity)
        prev_shell = float(self.state.get("ic_shell_drive", 0.15))
        new_shell = self._smooth(prev_shell, shell_target)

        # --- MGN relay ---
        mgn = self._mgn_relay(new_central, new_shell)

        # --- PPI signal ---
        ppi = self._ppi_signal(prepulse, new_central, intensity)

        # --- Threat sound relay ---
        threat_relay = self._threat_sound_relay(threat_sound, threat,
                                                  valence_intensity, new_shell)

        # --- Azimuth integration ---
        soc_data = prior.get("SuperiorOlivaryComplex", {})
        soc_input = float(soc_data.get("localization_signal", 0.0))
        azimuth_int = self._azimuth_integration(new_central, new_shell, soc_input)

        # --- State ---
        state = self._classify_state(ppi, threat_relay, new_central)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ic_central_drive"] = round(new_central, 4)
        self.state["ic_shell_drive"] = round(new_shell, 4)
        self.state["mgn_relay"] = round(mgn, 4)
        self.state["ppi_signal"] = round(ppi, 4)
        self.state["threat_sound_relay"] = round(threat_relay, 4)
        self.state["azimuth_integration"] = round(azimuth_int, 4)
        self.state["ic_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ic_central_drive": round(new_central, 4),
            "ic_shell_drive": round(new_shell, 4),
            "mgn_relay": round(mgn, 4),
            "ppi_signal": round(ppi, 4),
            "threat_sound_relay": round(threat_relay, 4),
            "azimuth_integration": round(azimuth_int, 4),
            "ic_state": state,
        }
