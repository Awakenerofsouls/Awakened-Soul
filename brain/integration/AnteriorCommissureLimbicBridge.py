"""
AnteriorCommissureLimbicBridge — Bilateral Limbic + Olfactory Conduit

NEURAL SUBSTRATE
================
The anterior commissure (AC) is a small but ancient white-matter tract
crossing the midline anterior to the columns of the fornix, connecting
the two temporal lobes plus their associated limbic and olfactory
structures. Distinct from the corpus callosum (which connects neocortex
generally), the AC specifically bridges:

- Bilateral amygdala
- Bilateral olfactory bulbs and piriform cortices
- Bilateral anterior olfactory nucleus
- Inferior temporal, parahippocampal, and fusiform gyri
- Inferior occipital cortex

The AC carries decussating olfactory fibers — making it essential for
bilateral olfactory integration and the contralateral innervation of
the olfactory bulb. It also enables bilateral amygdala coordination
during emotional processing and inter-hemispheric piriform-piriform
exchange of odor representations.

Functional model: AC ensures that limbic processing is unified across
hemispheres for affective/olfactory content even when the corpus
callosum-mediated neocortical exchange is absent or weakened. In
split-brain patients, an intact AC preserves bilateral emotion +
olfactory integration despite full callosotomy.

Catani 2002 mapped the AC + uncinate + fornix as the medial limbic
fiber system using diffusion tractography. Risold & Swanson 1996
characterized the rodent AC connections in detail.

KEY FINDINGS
============
1. Anterior commissure interconnects bilateral amygdala + olfactory bulbs + piriform cortex; primary limbic interhemispheric tract — [Catani M 2002, Neuroimage 17:77, doi:10.1006/nimg.2002.1136]
2. Bilateral olfactory integration via anterior commissure decussating fibers; AON is principal contralateral source — [Yan Z 2008, J Neurosci 28:1683, PMID 18272689]
3. Anterior commissure preserved limbic interhemispheric communication in split-brain (callosotomy) patients — [Bogen JE 1979, Brain Res Bull 4:127, doi:10.1016/0361-9230(79)90049-1]
4. Olfactory amygdala connectivity: anterior commissure is principal route for bilateral amygdaloid coordination of emotional valence — [Wang G 2024, Imaging Neuroscience 2:1, doi:10.1162/imag_a_00571]
5. Risold & Swanson rodent connectional analysis confirms AC carries bilateral amygdala + AON + piriform fibers — [Risold PY 1996, Brain Res Rev 24:115, PMID 9385452]

INPUTS (from prior_results)
============================
- BasolateralAmygdala.bla_drive (bilateral amygdala merger)
- AnteriorOlfactoryNucleus.aon_drive (bilateral OB integration)
- PiriformLayer2.pir2_drive
- OlfactoryBulb.ob_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS (to brain_runner enrichment)
=====================================
- ac_drive (0-1)
- bilateral_amygdala_signal (0-1)
- bilateral_olfactory_signal (0-1)
- limbic_unification_signal (0-1)
- ac_state (str): "limbic_unified" | "olfactory_dominant" |
  "amygdala_dominant" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCommissureLimbicBridge(BrainMechanism):
    """Anterior commissure — bilateral limbic + olfactory conduit."""

    BASELINE = 0.10
    SMOOTH = 0.20
    UNIFICATION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="AnteriorCommissureLimbicBridgeVariant",
            human_analog="Anterior commissure (limbic interhemispheric)",
            layer="integration",
        )
        self.state.setdefault("ac_drive", self.BASELINE)
        self.state.setdefault("bilateral_amygdala_signal", 0.0)
        self.state.setdefault("bilateral_olfactory_signal", 0.0)
        self.state.setdefault("limbic_unification_signal", 0.0)
        self.state.setdefault("ac_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _bilateral_amygdala(self, bla: float, intensity: float) -> float:
        """Bilateral amygdala synchronization (Wang 2024)."""
        return min(1.0, bla * 0.7 + intensity * 0.3)

    def _bilateral_olfactory(self, aon: float, ob: float,
                                pir: float) -> float:
        """Bilateral olfactory integration (Yan 2008 — AON principal
        contralateral source)."""
        return min(1.0, aon * 0.45 + ob * 0.35 + pir * 0.20)

    def _limbic_unification(self, amyg: float, olf: float) -> float:
        """Combined limbic unification signal."""
        return min(1.0, amyg * 0.55 + olf * 0.45)

    def _drive_target(self, amyg: float, olf: float) -> float:
        """AC drive."""
        return min(1.0, self.BASELINE + amyg * 0.45 + olf * 0.45)

    def _classify_state(self, drive: float, amyg: float, olf: float,
                          unification: float) -> str:
        if drive < 0.20:
            return "quiet"
        if unification > self.UNIFICATION_THRESHOLD:
            return "limbic_unified"
        if olf > amyg + 0.15:
            return "olfactory_dominant"
        if amyg > olf + 0.15:
            return "amygdala_dominant"
        return "limbic_unified"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        aon_data = prior.get("AnteriorOlfactoryNucleus", {})
        aon = float(aon_data.get("aon_drive",
                          aon_data.get("bilateral_integration_signal", 0.0)))

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive", 0.0))

        pir_data = prior.get("PiriformLayer2", {})
        if not pir_data:
            pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir2_drive",
                          pir_data.get("pir_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        amyg = self._bilateral_amygdala(bla, intensity)
        olf = self._bilateral_olfactory(aon, ob, pir)
        unification = self._limbic_unification(amyg, olf)

        target = self._drive_target(amyg, olf)
        prev_drive = float(self.state.get("ac_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        state = self._classify_state(new_drive, amyg, olf, unification)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ac_drive"] = round(new_drive, 4)
        self.state["bilateral_amygdala_signal"] = round(amyg, 4)
        self.state["bilateral_olfactory_signal"] = round(olf, 4)
        self.state["limbic_unification_signal"] = round(unification, 4)
        self.state["ac_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ac_drive": round(new_drive, 4),
            "bilateral_amygdala_signal": round(amyg, 4),
            "bilateral_olfactory_signal": round(olf, 4),
            "limbic_unification_signal": round(unification, 4),
            "ac_state": state,
        }

    def _split_brain_compensation(self) -> float:
        """In split-brain patients, AC compensates for callosotomy
        (Bogen 1979). High AC engagement = compensation active."""
        return float(self.state.get("limbic_unification_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ac_drive", 0.0),
            "amyg": self.state.get("bilateral_amygdala_signal", 0.0),
            "olf": self.state.get("bilateral_olfactory_signal", 0.0),
            "unification": self.state.get("limbic_unification_signal", 0.0),
            "state": self.state.get("ac_state", "quiet"),
        }
