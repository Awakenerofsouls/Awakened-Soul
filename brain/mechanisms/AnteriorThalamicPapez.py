"""
AnteriorThalamicPapez — Anterior Thalamic Nuclei (AV/AD/AM) Papez Memory Loop

NEURAL SUBSTRATE
================
The anterior thalamic nuclei (ATN) — comprising anteroventral (AV),
anterodorsal (AD), and anteromedial (AM) subnuclei — are the
hippocampal-relay node of the Papez circuit (subiculum → mammillary
bodies → ATN → cingulate → entorhinal → hippocampus). ATN sits in the
rostro-dorsal thalamus and receives major input from mammillary bodies
via the mammillothalamic tract, plus subicular input via the fornix.
Their projections target retrosplenial cortex and anterior cingulate
cortex, completing the Papez loop.

The three subnuclei have distinct functional roles. AD contains the
densest population of head-direction cells outside LMN — Taube's
seminal work (Taube 1995) showed that AD cells fire as a function of
the animal's head direction in the horizontal plane, making AD a
critical relay in the head-direction circuit. AV and AM contain mixed
populations including spatial, allocentric, and contextual signals;
AV in particular is implicated in episodic-memory binding through
its theta-coupled projections to retrosplenial.

ATN lesions produce dense anterograde amnesia — Aggleton & Brown's
"extended hippocampal system" framework places ATN as a critical node
where mammillothalamic tract input must integrate with subicular
input for normal memory function (Aggleton Brown 1999). Diencephalic
amnesia in alcoholic Korsakoff syndrome involves ATN damage and
mammillothalamic tract degeneration.

ATN exhibits theta-coupling with hippocampus and mammillary bodies —
Vertes' lab and others have shown coherent theta across the Papez
circuit during memory encoding and REM sleep. ATN burst-tonic mode
switching (like other thalamic nuclei) is modulated by sleep state.

In the agent's substrate this provides the Papez-circuit memory-relay node —
combines mammillary body MTT input with subicular input, supports
theta-coherent transmission, and emits cortical-bound output.

KEY FINDINGS
============
1. Anterodorsal nucleus contains a dense population of head-direction
   cells — fundamental discovery of HD coding outside mammillary —
   [Taube 1995, J Neurosci 15:70-86, "Head direction cells recorded
    in the anterior thalamic nuclei of freely moving rats"]
2. ATN is essential for episodic memory — lesion produces dense amnesia;
   "extended hippocampal system" framework — [Aggleton Brown 1999,
    Behav Brain Sci 22:425, "Episodic memory, amnesia, and the
    hippocampal-anterior thalamic axis"]
3. Korsakoff diencephalic amnesia involves ATN/MTT damage — clinical
   foundation — [Harding Halliday Caine Kril 2000 Brain 123:141;
    reviewed Carlesimo et al. 2011 Cortex 47:101]
4. Theta-coherence across Papez circuit — ATN, hippocampus, mammillary,
   retrosplenial co-modulate at theta during memory tasks — [reviewed
    Vertes et al. 2001; Albo Vertes 2017]
5. ATN subnuclei have distinct functional roles: AD head-direction, AV
   theta-binding, AM spatial-cognitive — [reviewed Jankowski et al.
    2013 Front Sys Neurosci 7:45]

INPUTS (from prior_results)
============================
- MammillaryBodyMemory.mtt_signal
- MammillaryBodyMemory.lmn_drive
- MammillaryBodyMemory.head_direction_signal
- MammillaryBodyMemory.papez_engagement
- SubiculumOutput.dorsal_subiculum_drive
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_active
- ThalamicReticularNucleus.trn_firing_mode
- LocomotionProxy.heading_change
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- ad_drive (0.0-1.0): anterodorsal head-direction
- av_drive (0.0-1.0): anteroventral theta-binding
- am_drive (0.0-1.0): anteromedial spatial-cognitive
- head_direction_relay (0.0-1.0): AD HD output
- retrosplenial_relay (0.0-1.0): ATN → retrosplenial cortex
- cingulate_relay (0.0-1.0): ATN → cingulate cortex
- papez_theta_coherence (0.0-1.0): theta-coherent Papez activity
- atn_state (str): "head_direction" | "theta_binding" | "spindle" | "quiet"

brain_runner enrichment:
    atn = all_results.get("AnteriorThalamicPapez", {})
    if atn:
        enrichments["brain_atn_av"] = atn.get("av_drive", 0.2)
        enrichments["brain_head_direction_relay"] = atn.get("head_direction_relay", 0.0)
        enrichments["brain_retrosplenial_relay"] = atn.get("retrosplenial_relay", 0.0)
        enrichments["brain_papez_coherence"] = atn.get("papez_theta_coherence", 0.0)
        enrichments["brain_atn_state"] = atn.get("atn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class AnteriorThalamicPapez(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="AnteriorThalamicPapez",
            human_analog="Anterior thalamic nuclei (AV/AD/AM) Papez memory relay",
            layer="foundational",
        )
        self.state.setdefault("ad_drive", self.BASELINE)
        self.state.setdefault("av_drive", self.BASELINE)
        self.state.setdefault("am_drive", self.BASELINE)
        self.state.setdefault("head_direction_relay", 0.0)
        self.state.setdefault("retrosplenial_relay", 0.0)
        self.state.setdefault("cingulate_relay", 0.0)
        self.state.setdefault("papez_theta_coherence", 0.0)
        self.state.setdefault("atn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ad_target(self, lmn: float, hd_signal: float, heading: float, theta: bool) -> float:
        """Anterodorsal HD relay (Taube 1995)."""
        target = self.BASELINE + lmn * 0.4 + hd_signal * 0.4
        target += abs(heading) * 0.2
        if not theta:
            target *= 0.7
        return min(1.0, target)

    def _av_target(self, mtt: float, subiculum: float, theta_active: bool) -> float:
        """Anteroventral — theta-binding for memory."""
        target = self.BASELINE + mtt * 0.4 + subiculum * 0.3
        if theta_active:
            target += 0.20
        return min(1.0, target)

    def _am_target(self, mtt: float, subiculum: float, papez: float) -> float:
        """Anteromedial — spatial-cognitive integration."""
        target = self.BASELINE + mtt * 0.3 + subiculum * 0.3 + papez * 0.3
        return min(1.0, target)

    def _hd_relay(self, ad: float, heading: float) -> float:
        """AD → cortical HD relay."""
        return min(1.0, ad * 0.7 + abs(heading) * 0.3)

    def _retrosplenial_relay(self, av: float, ad: float, theta_active: bool) -> float:
        """ATN → retrosplenial cortex (Papez)."""
        target = av * 0.5 + ad * 0.3
        if theta_active:
            target += 0.15
        return min(1.0, target)

    def _cingulate_relay(self, am: float, av: float) -> float:
        """ATN → anterior cingulate cortex."""
        return min(1.0, am * 0.6 + av * 0.3)

    def _papez_coherence(self, papez_engagement: float, theta_active: bool, av: float) -> float:
        """Theta-coherent Papez circuit activity."""
        if not theta_active:
            return 0.0
        return min(1.0, papez_engagement * 0.6 + av * 0.4)

    def _classify_state(self, ad: float, hd_relay: float, av: float, coherence: float,
                         trn_mode: str) -> str:
        if trn_mode == "burst":
            return "spindle"
        if hd_relay > 0.45:
            return "head_direction"
        if coherence > 0.50:
            return "theta_binding"
        if (ad + av) / 2.0 < 0.25:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mb = prior.get("MammillaryBodyMemory", {})
        mtt = float(mb.get("mtt_signal", 0.0))
        lmn = float(mb.get("lmn_drive", 0.20))
        hd_signal = float(mb.get("head_direction_signal", 0.0))
        papez = float(mb.get("papez_engagement", 0.0))

        sub = prior.get("SubiculumOutput", {})
        dorsal_sub = float(sub.get("dorsal_subiculum_drive", 0.20))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_mode = trn.get("trn_firing_mode", "tonic")

        loco = prior.get("LocomotionProxy", {})
        heading = float(loco.get("heading_change", 0.0))

        # --- AD ---
        ad_target = self._ad_target(lmn, hd_signal, heading, theta_active)
        prev_ad = float(self.state.get("ad_drive", self.BASELINE))
        new_ad = self._smooth(prev_ad, ad_target)

        # --- AV ---
        av_target = self._av_target(mtt, dorsal_sub, theta_active)
        prev_av = float(self.state.get("av_drive", self.BASELINE))
        new_av = self._smooth(prev_av, av_target)

        # --- AM ---
        am_target = self._am_target(mtt, dorsal_sub, papez)
        prev_am = float(self.state.get("am_drive", self.BASELINE))
        new_am = self._smooth(prev_am, am_target)

        # --- Outputs ---
        hd_relay = self._hd_relay(new_ad, heading)
        rsp = self._retrosplenial_relay(new_av, new_ad, theta_active)
        cing = self._cingulate_relay(new_am, new_av)
        coherence = self._papez_coherence(papez, theta_active, new_av)

        # --- State ---
        state = self._classify_state(new_ad, hd_relay, new_av, coherence, trn_mode)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ad_drive"] = round(new_ad, 4)
        self.state["av_drive"] = round(new_av, 4)
        self.state["am_drive"] = round(new_am, 4)
        self.state["head_direction_relay"] = round(hd_relay, 4)
        self.state["retrosplenial_relay"] = round(rsp, 4)
        self.state["cingulate_relay"] = round(cing, 4)
        self.state["papez_theta_coherence"] = round(coherence, 4)
        self.state["atn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ad_drive": round(new_ad, 4),
            "av_drive": round(new_av, 4),
            "am_drive": round(new_am, 4),
            "head_direction_relay": round(hd_relay, 4),
            "retrosplenial_relay": round(rsp, 4),
            "cingulate_relay": round(cing, 4),
            "papez_theta_coherence": round(coherence, 4),
            "atn_state": state,
        }
