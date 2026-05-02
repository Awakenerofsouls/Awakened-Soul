"""
MedialGeniculateNucleus — MGN Auditory Thalamus (Ventral / Dorsal / Medial)

NEURAL SUBSTRATE
================
The medial geniculate nucleus (MGN) is the auditory thalamus, sitting
on the dorsal surface of the thalamus and serving as the obligatory
relay between the inferior colliculus (IC) and primary auditory cortex
(A1). MGN is divided into three principal subdivisions:

Ventral MGN (MGv) — the "lemniscal" core, tonotopically organized,
relays sharply tuned auditory input from ICc to A1. MGv is the canonical
"first-order" thalamic relay for hearing.

Dorsal MGN (MGd) — non-lemniscal, broadly tuned, integrates input from
DC of IC and from auditory cortex via cortico-thalamic feedback. MGd
projects to higher auditory cortical areas and to amygdala.

Medial MGN (MGm) — also called magnocellular MGN, multimodal (auditory,
somatosensory, vestibular), and the principal MGN subdivision of the
"low road" of LeDoux to amygdala. MGm carries fast, broadly tuned
auditory information that directly engages the lateral amygdala for
auditory fear conditioning, bypassing cortical processing. MGm
plasticity tracks fear-conditioning learning.

MGN is gated by the thalamic reticular nucleus (TRN) auditory sector
and modulated by descending corticothalamic feedback from auditory
cortex layer 6. MGN also contains burst-firing dynamics that switch
between tonic (wake) and burst (NREM) modes, like other thalamic
relays.

In the agent's substrate this provides the auditory thalamic relay — converts
IC ascending signals into MGv lemniscal output to "auditory cortex
proxy," MGm signals direct-to-amygdala (low road), and MGd signals
to higher-order auditory pathways. Gated by TRN auditory sector.

KEY FINDINGS
============
1. MGN has three subdivisions: MGv (lemniscal tonotopic), MGd (non-
   lemniscal), MGm (multimodal, magnocellular) with distinct projection
   targets — [reviewed Winer Schreiner 2011, "The Auditory Cortex";
    Lee Sherman 2010 PNAS 107:9550]
2. MGm carries auditory "low road" to lateral amygdala for fear
   conditioning — bypasses auditory cortex — [LeDoux et al. 1990,
    J Neurosci 10:1062-1069, "The lateral amygdaloid nucleus: sensory
    interface of the amygdala in fear conditioning"; reviewed LeDoux
    2000 Annu Rev Neurosci 23:155]
3. MGm plasticity tracks auditory fear conditioning learning —
   conditioned tone responses potentiate in MGm — [reviewed Weinberger
    2007 Hear Res; Edeline Weinberger 1992 J Neurosci]
4. MGN exhibits burst/tonic mode switching modulated by sleep state
   and TRN inhibition — [reviewed Sherman 2001 Trends Neurosci 24:122,
    "Tonic and burst firing"]
5. Corticothalamic feedback from A1 layer 6 modulates MGN gain and
   selectivity — top-down auditory attention substrate — [Murphy
    Sillito 1987 Nature 329:727; Briggs Usrey 2008]
6. A1 layer 6 corticothalamic feedback sharpens MGN frequency
   tuning and synchrony via thalamic reticular nucleus gating —
   [Sillito Jones 2002 Neuroscience 62:1; Zhang et al. 2013 Nat
    Neurosci 16:1316, "Corticofugal feedback refines auditory
    circuitry"]

INPUTS (from prior_results)
============================
- InferiorColliculusAuditory.ic_central_drive
- InferiorColliculusAuditory.ic_shell_drive
- InferiorColliculusAuditory.mgn_relay
- InferiorColliculusAuditory.threat_sound_relay
- ThalamicReticularNucleus.sensory_sector_gate
- ThalamicReticularNucleus.trn_firing_mode
- AttentionTopDownProxy.attention_focus
- ValenceTagger.threat_signal

OUTPUTS (to brain_runner enrichment)
=====================================
- mgv_drive (0.0-1.0): ventral MGN lemniscal output to A1
- mgd_drive (0.0-1.0): dorsal MGN non-lemniscal output
- mgm_drive (0.0-1.0): medial MGN multimodal output (low road)
- mgm_amygdala_relay (0.0-1.0): MGm → lateral amygdala fear pathway
- a1_relay (0.0-1.0): MGv → A1 cortical relay
- firing_mode (str): "tonic" | "burst" | "off"
- mgn_state (str): "tonic_relay" | "low_road_engaged" | "spindle" | "quiet"

brain_runner enrichment:
    mgn = all_results.get("MedialGeniculateNucleus", {})
    if mgn:
        enrichments["brain_mgv"] = mgn.get("mgv_drive", 0.1)
        enrichments["brain_mgm_amygdala"] = mgn.get("mgm_amygdala_relay", 0.0)
        enrichments["brain_a1_relay"] = mgn.get("a1_relay", 0.0)
        enrichments["brain_mgn_state"] = mgn.get("mgn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedialGeniculateNucleus(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="MedialGeniculateNucleus",
            human_analog="Medial geniculate nucleus auditory thalamus (MGv/MGd/MGm)",
            layer="foundational",
        )
        self.state.setdefault("mgv_drive", self.BASELINE)
        self.state.setdefault("mgd_drive", self.BASELINE)
        self.state.setdefault("mgm_drive", self.BASELINE)
        self.state.setdefault("mgm_amygdala_relay", 0.0)
        self.state.setdefault("a1_relay", 0.0)
        self.state.setdefault("firing_mode", "tonic")
        self.state.setdefault("mgn_state", "quiet")
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("tick_count", 0)

    def _mgv_target(self, ic_central: float, trn_gate: float, attention: float) -> float:
        """MGv lemniscal — driven by ICc, gated by TRN."""
        target = self.BASELINE + ic_central * 0.7 * (1.0 - trn_gate * 0.5)
        target += attention * 0.2
        return min(1.0, target)

    def _mgd_target(self, ic_shell: float, attention: float, threat: bool) -> float:
        """MGd non-lemniscal — engaged by IC shell / cortical descending."""
        target = self.BASELINE + ic_shell * 0.6
        target += attention * 0.2
        if threat:
            target += 0.10
        return min(1.0, target)

    def _mgm_target(self, ic_central: float, ic_shell: float,
                    threat_sound_relay: float, threat: bool) -> float:
        """MGm magnocellular multimodal — broadly tuned, fast — emphasis on
        threat-typed input for low-road.
        """
        target = self.BASELINE + (ic_central + ic_shell) * 0.3
        target += threat_sound_relay * 0.5
        if threat:
            target += 0.15
        return min(1.0, target)

    def _firing_mode(self, trn_mode: str) -> str:
        """MGN burst/tonic mode mirrors TRN firing pattern."""
        if trn_mode == "burst":
            return "burst"
        if trn_mode == "off":
            return "off"
        return "tonic"

    def _mgm_amygdala_relay(self, mgm: float, threat: bool) -> float:
        """MGm → lateral amygdala fear pathway (LeDoux low road)."""
        if not threat:
            return mgm * 0.4
        return min(1.0, mgm * 0.95)

    def _a1_relay(self, mgv: float, firing_mode: str) -> float:
        """MGv → A1 cortical relay; suppressed in burst/off mode."""
        if firing_mode == "off":
            return 0.0
        if firing_mode == "burst":
            return mgv * 0.5
        return min(1.0, mgv * 0.95)

    def _classify_state(self, mode: str, mgm_relay: float, mgv: float) -> str:
        if mode == "burst":
            return "spindle"
        if mode == "off":
            return "quiet"
        if mgm_relay > 0.40:
            return "low_road_engaged"
        if mgv > 0.30:
            return "tonic_relay"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ic = prior.get("InferiorColliculusAuditory", {})
        ic_central = float(ic.get("ic_central_drive", self.BASELINE))
        ic_shell = float(ic.get("ic_shell_drive", 0.15))
        threat_relay = float(ic.get("threat_sound_relay", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_gate = float(trn.get("sensory_sector_gate", 0.30))
        trn_mode = trn.get("trn_firing_mode", "tonic")

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        # --- MGv ---
        mgv_target = self._mgv_target(ic_central, trn_gate, attention)
        prev_mgv = float(self.state.get("mgv_drive", self.BASELINE))
        new_mgv = self._smooth(prev_mgv, mgv_target)

        # --- MGd ---
        mgd_target = self._mgd_target(ic_shell, attention, threat)
        prev_mgd = float(self.state.get("mgd_drive", self.BASELINE))
        new_mgd = self._smooth(prev_mgd, mgd_target)

        # --- MGm ---
        mgm_target = self._mgm_target(ic_central, ic_shell, threat_relay, threat)
        prev_mgm = float(self.state.get("mgm_drive", self.BASELINE))
        new_mgm = self._smooth(prev_mgm, mgm_target)

        # --- Firing mode ---
        mode = self._firing_mode(trn_mode)

        # --- Outputs ---
        mgm_amyg = self._mgm_amygdala_relay(new_mgm, threat)
        a1 = self._a1_relay(new_mgv, mode)

        # --- State ---
        state = self._classify_state(mode, mgm_amyg, new_mgv)

        recent = list(self.state.get("recent_modes", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mgv_drive"] = round(new_mgv, 4)
        self.state["mgd_drive"] = round(new_mgd, 4)
        self.state["mgm_drive"] = round(new_mgm, 4)
        self.state["mgm_amygdala_relay"] = round(mgm_amyg, 4)
        self.state["a1_relay"] = round(a1, 4)
        self.state["firing_mode"] = mode
        self.state["mgn_state"] = state
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mgv_drive": round(new_mgv, 4),
            "mgd_drive": round(new_mgd, 4),
            "mgm_drive": round(new_mgm, 4),
            "mgm_amygdala_relay": round(mgm_amyg, 4),
            "a1_relay": round(a1, 4),
            "firing_mode": mode,
            "mgn_state": state,
        }
