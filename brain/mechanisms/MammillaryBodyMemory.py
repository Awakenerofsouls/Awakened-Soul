"""
MammillaryBodyMemory — Mammillary Bodies / Papez Circuit Episodic Memory Hub

NEURAL SUBSTRATE
================
The mammillary bodies (MB) are paired round nuclei at the ventral
posterior hypothalamus, anatomically prominent at the base of the brain.
They consist of medial mammillary nucleus (MMN, the larger and more
medial division) and lateral mammillary nucleus (LMN, smaller and more
lateral). The medial mammillary nucleus is the principal node — its
neurons project via the mammillothalamic tract (MTT, Vicq d'Azyr's
bundle) to the anterior thalamic nuclei (AT), which project to cingulate
cortex; together MB → AT → cingulate → entorhinal/hippocampal circuit
forms the Papez circuit, a foundational anatomical loop for episodic
memory.

The MB receives major input from the postcommissural fornix carrying
hippocampal subiculum output, plus inputs from septum, mPFC, and
brainstem reticular nuclei (especially Gudden's tegmental nuclei).
The MB is required for spatial memory and recollective episodic
memory — Vann & Aggleton's body of work has established MB as a
non-trivial memory hub distinct from "just a relay." Lesions of MB
produce dense anterograde amnesia in humans (e.g., Wernicke-Korsakoff
syndrome from thiamine deficiency).

LMN neurons fire as "head direction cells" — encoding allocentric
heading; this signal propagates through anterodorsal thalamus to
postsubiculum and entorhinal cortex (Taube et al.). Selective LMN
lesion abolishes hippocampal/entorhinal head direction signals.

Recent work has clarified that MB lesions impair episodic-like memory
consolidation independently of hippocampal damage (Vann 2010; Dillingham
& Vann 2019), and MB participates in theta synchronization across the
Papez circuit, supporting memory binding.

In the agent's substrate this provides the mammillary node of the Papez
circuit — a slow integrator of subiculum-equivalent input and a relay
for head-direction (when motion proxies are available), feeding into
anterior-thalamic / cingulate equivalent mechanisms downstream.

KEY FINDINGS
============
1. Mammillary bodies are required for spatial and episodic memory;
   not a simple relay but a dedicated memory node — [Vann Aggleton 2004,
    Nat Rev Neurosci 5:35-44, "The mammillary bodies: two memory
    systems in one?"]
2. Lateral mammillary nucleus encodes head direction; LMN lesion
   abolishes downstream head-direction signals — [Stackman Taube 1998,
    J Neurosci 18:9020-9039; Yoder Taube 2014; Bassett Tullman Taube
    2007 J Neurosci]
3. Mammillary body lesions produce anterograde amnesia in human
   Wernicke-Korsakoff syndrome — clinical foundation — [reviewed
    Harding Halliday Caine Kril 2000 Brain 123:141; Sullivan
    Pfefferbaum 2009]
4. MB to anterior thalamus mammillothalamic tract is critical for
   recollection — selective MTT lesion impairs recollection more
   than familiarity — [Vann et al. 2009, J Neurosci 29:6203-6210;
    Dillingham Vann 2019 Neurobiol Learn Mem 161:69]
5. Mammillary body theta synchronization with hippocampus and anterior
   thalamus supports memory binding — [Kirk Mackay 2003 J Neurosci
    23:1267; reviewed Dillingham Frizzati Nelson Vann 2015]

INPUTS (from prior_results)
============================
- HippocampalContextProxy.subiculum_output (optional; default 0)
- HippocampalContextProxy.context_id (optional; default 0)
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_amplitude
- MedialSeptumTheta.theta_active
- ArousalRegulator.tonic_level
- LocomotionProxy.locomotion_speed
- LocomotionProxy.heading_change (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- mmn_drive (0.0-1.0): medial mammillary nucleus output
- lmn_drive (0.0-1.0): lateral mammillary nucleus output
- mtt_signal (0.0-1.0): mammillothalamic tract → anterior thalamus
- head_direction_signal (0.0-1.0): LMN head-direction proxy
- papez_engagement (0.0-1.0): theta-coupled Papez activity
- memory_consolidation_active (bool)
- mb_state (str): "quiet" | "encoding" | "head_direction" | "consolidation"

brain_runner enrichment:
    mb = all_results.get("MammillaryBodyMemory", {})
    if mb:
        enrichments["brain_mmn_drive"] = mb.get("mmn_drive", 0.2)
        enrichments["brain_mtt_signal"] = mb.get("mtt_signal", 0.0)
        enrichments["brain_head_direction"] = mb.get("head_direction_signal", 0.0)
        enrichments["brain_papez_engagement"] = mb.get("papez_engagement", 0.0)
        enrichments["brain_mb_state"] = mb.get("mb_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodyMemory(BrainMechanism):
    BASELINE_MMN = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="MammillaryBodyMemory",
            human_analog="Mammillary bodies (medial + lateral) Papez circuit memory node",
            layer="foundational",
        )
        self.state.setdefault("mmn_drive", self.BASELINE_MMN)
        self.state.setdefault("lmn_drive", 0.20)
        self.state.setdefault("mtt_signal", 0.0)
        self.state.setdefault("head_direction_signal", 0.0)
        self.state.setdefault("papez_engagement", 0.0)
        self.state.setdefault("memory_consolidation_active", False)
        self.state.setdefault("mb_state", "quiet")
        self.state.setdefault("recent_papez", [])
        self.state.setdefault("tick_count", 0)

    def _mmn_target(self, subiculum: float, theta: float, theta_active: bool,
                     arousal: float) -> float:
        """Medial mammillary — driven by hippocampal subiculum input through fornix."""
        target = self.BASELINE_MMN + subiculum * 0.5
        if theta_active:
            target += theta * 0.2
        target += max(0.0, arousal - 0.5) * 0.2
        return min(1.0, target)

    def _lmn_target(self, locomotion: float, heading_change: float, arousal: float) -> float:
        """Lateral mammillary — head-direction; engaged with locomotion."""
        target = 0.10 + locomotion * 0.4 + abs(heading_change) * 0.5
        target += max(0.0, arousal - 0.4) * 0.2
        return min(1.0, target)

    def _mtt_signal(self, mmn: float, lmn: float) -> float:
        """Mammillothalamic tract → anterior thalamus — combined MMN+LMN."""
        return min(1.0, mmn * 0.7 + lmn * 0.3)

    def _head_direction(self, lmn: float, locomotion: float, heading: float) -> float:
        """Head-direction signal."""
        return min(1.0, lmn * 0.7 + locomotion * 0.2 + abs(heading) * 0.3)

    def _papez_engagement(self, mtt: float, theta_amp: float, theta_active: bool) -> float:
        """Theta-coupled Papez circuit engagement (Kirk MacKay 2003)."""
        if not theta_active:
            return mtt * 0.3
        return min(1.0, mtt * 0.6 + theta_amp * 0.4)

    def _consolidation(self, papez: float, sleep_state: str) -> bool:
        """Memory consolidation gate — engaged during sleep with Papez activity."""
        if sleep_state == "SLEEP" and papez > 0.40:
            return True
        return False

    def _classify_state(self, mmn: float, lmn: float, papez: float, consolidation: bool) -> str:
        if consolidation:
            return "consolidation"
        if lmn > 0.40 and lmn > mmn:
            return "head_direction"
        if mmn > 0.40:
            return "encoding"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hipp = prior.get("HippocampalContextProxy", {})
        subiculum = float(hipp.get("subiculum_output", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_phase = float(ms.get("theta_phase", 0.0))
        theta_amp = float(ms.get("theta_amplitude", 0.0))
        theta_active = bool(ms.get("theta_active", False))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        heading = float(loco.get("heading_change", 0.0))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- MMN ---
        mmn_target = self._mmn_target(subiculum, theta_amp, theta_active, tonic)
        prev_mmn = float(self.state.get("mmn_drive", self.BASELINE_MMN))
        new_mmn = self._smooth(prev_mmn, mmn_target)

        # --- LMN ---
        lmn_target = self._lmn_target(locomotion, heading, tonic)
        prev_lmn = float(self.state.get("lmn_drive", 0.20))
        new_lmn = self._smooth(prev_lmn, lmn_target)

        # --- MTT signal ---
        mtt = self._mtt_signal(new_mmn, new_lmn)

        # --- Head direction ---
        hd = self._head_direction(new_lmn, locomotion, heading)

        # --- Papez engagement ---
        papez = self._papez_engagement(mtt, theta_amp, theta_active)
        prev_papez = float(self.state.get("papez_engagement", 0.0))
        new_papez = self._smooth(prev_papez, papez)

        # --- Consolidation ---
        consolidation = self._consolidation(new_papez, sleep_state)

        # --- State ---
        state = self._classify_state(new_mmn, new_lmn, new_papez, consolidation)

        recent = list(self.state.get("recent_papez", []))
        recent.append(round(new_papez, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mmn_drive"] = round(new_mmn, 4)
        self.state["lmn_drive"] = round(new_lmn, 4)
        self.state["mtt_signal"] = round(mtt, 4)
        self.state["head_direction_signal"] = round(hd, 4)
        self.state["papez_engagement"] = round(new_papez, 4)
        self.state["memory_consolidation_active"] = consolidation
        self.state["mb_state"] = state
        self.state["spatial_memory_active"] = (state == "MemoryActive")
        self.state["hd_signal_strength"] = round(hd, 4)
        self.state["papez_engagement"] = round(new_papez, 4)
        self.state["recent_papez"] = recent
        self.state["papez_ema"] = round(new_papez * 0.2 + float(self.state.get("papez_ema", new_papez)) * 0.8, 4)
        self.state["hd_confidence"] = round(min(1.0, abs(hd - 0.5) * 2), 4)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mmn_drive": round(new_mmn, 4),
            "lmn_drive": round(new_lmn, 4),
            "mtt_signal": round(mtt, 4),
            "head_direction_signal": round(hd, 4),
            "papez_engagement": round(new_papez, 4),
            "memory_consolidation_active": consolidation,
            "mb_state": state,
            "spatial_memory_active": (state == "MemoryActive"),
            "hd_signal_strength": round(hd, 4),
            "papez_ema": round(new_papez * 0.2 + float(self.state.get("papez_ema", new_papez)) * 0.8, 4),
        }
