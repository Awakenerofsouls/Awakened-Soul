"""
CorpusCallosumFullBridge — Interhemispheric Integration Bus

NEURAL SUBSTRATE
================
The corpus callosum (CC) is the largest white-matter tract in the
mammalian brain, containing ~200-250 million axons connecting homologous
regions of the two cerebral hemispheres. Its principal function is
synchronizing and coordinating computation between the structurally
specialized left and right hemispheres — left hemisphere lateralized
for language and analytical processing, right for spatial/face/holistic
processing.

Anatomical organization (rostral to caudal):
- Rostrum + genu — connect prefrontal cortex (executive, working memory)
- Body — connect motor + premotor, somatosensory cortex
- Splenium — connect parietal, temporal, occipital (visual, face, scene)

Gazzaniga's 45+ years of split-brain research (callosotomy patients
treated for refractory epilepsy) established that interhemispheric
integration is not just relay but functional binding: each hemisphere
operates independently when CC is sectioned, with the left interpreter
fabricating explanations for right-hemisphere actions, and visual
integration breaking down when stimuli are routed to one hemisphere
but not the other.

Functional model: callosal fibers carry homotopic excitation +
inhibition between paired cortical areas, producing either functional
unification (common-frame perception, motor coordination) or
competitive lateralization (one hemisphere wins for a given task).

KEY FINDINGS
============
1. Forty-five years of split-brain research established corpus callosum as primary substrate of interhemispheric integration; left interpreter, right specialization — [Gazzaniga MS 2005, Nat Rev Neurosci 6:653, doi:10.1038/nrn1723]
2. Cerebral specialization + interhemispheric communication via callosum enables higher-order integrated cognition — [Gazzaniga MS 2000, Brain 123:1293, doi:10.1093/brain/123.7.1293]
3. Posterior callosal fibers sufficient for full interhemispheric integration; small posterior fraction preserves binding — [Berlucchi G 2014, Brain 137:50, doi:10.1093/brain/awt278]
4. Split-brain patients show preserved unified consciousness despite anatomical disconnection; subcortical pathways contribute — [Pinto Y 2017, Brain 140:1231, doi:10.1093/brain/awx050]
5. Fifty years of split-brain insights: callosum essential for integrated perception, motor coordination, language-spatial integration — [Wolman D 2012, Nature 483:260, doi:10.1038/483260a]

INPUTS (from prior_results)
============================
- DorsolateralPrefrontalCortex.dlpfc_drive (left+right pooled in single agent)
- PrimaryVisualCortex.v1_drive
- PrimaryMotorCortex.m1_drive
- PrimarySomatosensoryCortex.s1_drive
- PrimaryAuditoryCortex.a1_drive
- WernickeArea / TemporalLanguageArea (if available — proxy for L lateralization)
- ParahippocampalPlaceArea.ppa_drive (R-lateralized)

OUTPUTS (to brain_runner enrichment)
=====================================
- callosum_drive (0-1)
- interhemispheric_synchrony (0-1)
- frontal_integration_signal (0-1) — genu/rostrum bandwidth
- visual_integration_signal (0-1) — splenium bandwidth
- motor_coordination_signal (0-1) — body bandwidth
- lateralization_balance (0-1) — left vs right dominance contrast
- callosum_state (str): "integrated" | "lateralized_left" |
  "lateralized_right" | "decoupled" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CorpusCallosumFullBridge(BrainMechanism):
    """Corpus callosum — interhemispheric integration bus."""

    BASELINE = 0.10
    SMOOTH = 0.20
    INTEGRATION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="CorpusCallosumFullBridgeVariant",
            human_analog="Corpus callosum (interhemispheric bridge)",
            layer="integration",
        )
        self.state.setdefault("callosum_drive", self.BASELINE)
        self.state.setdefault("interhemispheric_synchrony", 0.0)
        self.state.setdefault("frontal_integration_signal", 0.0)
        self.state.setdefault("visual_integration_signal", 0.0)
        self.state.setdefault("motor_coordination_signal", 0.0)
        self.state.setdefault("lateralization_balance", 0.5)
        self.state.setdefault("callosum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _frontal_band(self, dlpfc: float, vlpfc: float) -> float:
        """Genu/rostrum bandwidth — frontal cortex pair (Gazzaniga 2000).
        Both available frontal signals contribute."""
        return min(1.0, max(dlpfc, vlpfc) * 0.6 + (dlpfc + vlpfc) * 0.20)

    def _visual_band(self, v1: float, ppa: float) -> float:
        """Splenium bandwidth — V1 pair + scene/face areas
        (Berlucchi 2014 posterior fibers sufficient)."""
        return min(1.0, v1 * 0.6 + ppa * 0.4)

    def _motor_band(self, m1: float, s1: float) -> float:
        """Body bandwidth — motor + somatosensory pair."""
        return min(1.0, m1 * 0.55 + s1 * 0.45)

    def _drive_target(self, frontal: float, visual: float,
                       motor: float, auditory: float) -> float:
        """Aggregate callosum drive — sum of bandwidth across regions."""
        return min(1.0, self.BASELINE + frontal * 0.30 + visual * 0.25
                      + motor * 0.25 + auditory * 0.10)

    def _synchrony(self, signals: list) -> float:
        """Interhemispheric synchrony — proxy via signal coherence
        across regions (homologous areas should fire together)."""
        active = [s for s in signals if s > 0.20]
        if len(active) < 2:
            return 0.0
        mean_a = sum(active) / len(active)
        var = sum((s - mean_a) ** 2 for s in active) / len(active)
        # Higher mean + lower variance = better synchrony
        return max(0.0, min(1.0, mean_a * (1.0 - min(1.0, var * 4.0))))

    def _lateralization(self, language_proxy: float,
                          spatial_proxy: float) -> float:
        """Left-right lateralization balance.
        0.0 = strong left lateralization (language dominant)
        1.0 = strong right lateralization (spatial dominant)
        0.5 = balanced/integrated.

        Pinto 2017: even after callosotomy, unified consciousness persists
        — so this is competitive bias, not absolute split.
        """
        total = language_proxy + spatial_proxy
        if total < 0.10:
            return 0.5  # neutral when both quiet
        right_share = spatial_proxy / total
        return max(0.0, min(1.0, right_share))

    def _classify_state(self, drive: float, synchrony: float,
                          lat: float) -> str:
        if drive < 0.20:
            return "quiet"
        # Severe lateralization (one hemisphere dominant + low sync)
        if synchrony < 0.20:
            if lat < 0.30:
                return "lateralized_left"
            if lat > 0.70:
                return "lateralized_right"
            return "decoupled"
        if synchrony > self.INTEGRATION_THRESHOLD:
            return "integrated"
        if lat < 0.30:
            return "lateralized_left"
        if lat > 0.70:
            return "lateralized_right"
        return "integrated"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive", 0.0))

        vlpfc_data = prior.get("VentrolateralPrefrontalCortex", {})
        vlpfc = float(vlpfc_data.get("vlpfc_drive", 0.0))

        v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive", 0.0))

        m1_data = prior.get("PrimaryMotorCortex", {})
        m1 = float(m1_data.get("m1_drive", 0.0))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive", 0.0))

        a1_data = prior.get("PrimaryAuditoryCortex", {})
        a1 = float(a1_data.get("a1_drive", 0.0))

        ppa_data = prior.get("ParahippocampalPlaceArea", {})
        ppa = float(ppa_data.get("ppa_drive", 0.0))

        # Language proxy: VLPFC (Broca-side) — left-lateralized in humans
        language_proxy = vlpfc
        # Spatial proxy: PPA + IPS — right-lateralized
        ips_data = prior.get("IntraparietalSulcus", {})
        ips = float(ips_data.get("ips_drive", 0.0))
        spatial_proxy = max(ppa, ips)

        frontal = self._frontal_band(dlpfc, vlpfc)
        visual = self._visual_band(v1, ppa)
        motor = self._motor_band(m1, s1)

        target = self._drive_target(frontal, visual, motor, a1)
        prev_drive = float(self.state.get("callosum_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        signals = [dlpfc, vlpfc, v1, m1, s1, a1, ppa]
        synchrony = self._synchrony(signals)
        lat = self._lateralization(language_proxy, spatial_proxy)

        state = self._classify_state(new_drive, synchrony, lat)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["callosum_drive"] = round(new_drive, 4)
        self.state["interhemispheric_synchrony"] = round(synchrony, 4)
        self.state["frontal_integration_signal"] = round(frontal, 4)
        self.state["visual_integration_signal"] = round(visual, 4)
        self.state["motor_coordination_signal"] = round(motor, 4)
        self.state["lateralization_balance"] = round(lat, 4)
        self.state["callosum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "callosum_drive": round(new_drive, 4),
            "interhemispheric_synchrony": round(synchrony, 4),
            "frontal_integration_signal": round(frontal, 4),
            "visual_integration_signal": round(visual, 4),
            "motor_coordination_signal": round(motor, 4),
            "lateralization_balance": round(lat, 4),
            "callosum_state": state,
        }

    def _split_brain_proxy(self, recent_states: list) -> float:
        """Sustained 'decoupled' = split-brain-like signature
        (Gazzaniga 2005)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        d = sum(1 for s in win if s == "decoupled")
        return d / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("callosum_drive", 0.0),
            "synchrony": self.state.get("interhemispheric_synchrony", 0.0),
            "lateralization": self.state.get("lateralization_balance", 0.5),
            "state": self.state.get("callosum_state", "quiet"),
        }
