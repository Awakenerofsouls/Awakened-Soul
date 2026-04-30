"""
FrontalEyeFields — FEF (Brodmann Area 8 / Walker's Area 45)

NEURAL SUBSTRATE
================
The frontal eye fields lie in the rostral bank of the arcuate sulcus in
macaque (area 8a/FEF), and on the precentral gyrus near the
intersection with the superior frontal sulcus in human. FEF is a
premotor area for saccadic eye movements and a key node of the
dorsal-frontal attention network.

Connectivity:
  - Visual input: from V4, MT, MST, LIP, IT (top-down attention loop).
  - Output: superior colliculus (saccade generator), brainstem
    saccadic burst nuclei, thalamus (MD, VL), striatum.
  - Direct cortico-cortical projections to V4 / V2 (Moore & Armstrong
    2003): FEF microstimulation enhances V4 visual responses below
    saccade threshold — the cortical substrate of endogenous spatial
    attention.

Functional cell types (Bruce & Goldberg 1985):
  - Visual cells: respond to retinotopic visual stimuli, no movement
    field activation.
  - Movement cells: discharge before saccades, no visual response.
  - Visuomovement cells: combination of both.
  - Fixation cells: tonic activity during steady fixation.
  Saccade vector code: each FEF neuron has a movement field encoding a
  preferred saccade direction/amplitude.

FEF and LIP together form the priority/saliency-map circuit for
visuospatial attention; FEF biases sensory cortex top-down (Schall
2002 review of saccade neurophysiology), while LIP supplies bottom-up
saliency. Visual selection in FEF can be dissociated from saccade
production (Thompson & Schall 1997).

KEY FINDINGS
============
1. Three classes of FEF neurons discharging before saccades — visual
   (40%), movement (20%), and visuomovement (40%); each encodes a
   saccade vector —
   [Bruce CJ 1985, J Neurophysiol 53:603, doi:10.1152/jn.1985.53.3.603]
2. Subthreshold microstimulation of FEF enhances V4 visual responses
   at retinotopically corresponding sites — causal link from FEF to
   covert attention —
   [Moore T 2003, Nature 421:370, doi:10.1038/nature01341]
3. Review of FEF physiology: visual selection, saccade preparation,
   target selection occur in distinct neuronal populations —
   [Schall JD 2002, Philos Trans R Soc B 357:1073, doi:10.1098/rstb.2002.1098]
4. FEF visual neurons signal target selection ~100-150 ms before
   saccade, dissociable from movement preparation —
   [Thompson KG 1997, J Neurophysiol 77:1046, doi:10.1152/jn.1997.77.2.1046]
5. Bilateral FEF and parietal cortex form the dorsal frontoparietal
   attention network in human fMRI; activation by endogenous
   covert attention —
   [Ekstrom LB 2008, Science 321:414, doi:10.1126/science.1158776]

INPUTS
======
- LateralIntraparietalArea.priority_signal (parietal saliency)
- VisualAreaV4.v4_drive (object/feature evidence)
- MiddleTemporalArea.lip_input_signal (motion evidence)
- DLPFC / cognitive-control top-down (optional)

OUTPUTS
=======
- fef_drive (0-1)
- saccade_vector_signal (0-1) — pooled movement-cell output
- attention_map (0-1) — top-down endogenous attention to V4/V2
- target_selection (0-1) — visual selection (Thompson 1997)
- sc_input_signal (0-1) — FEF → superior colliculus
- v4_modulation (0-1) — FEF → V4 attention beam (Moore 2003)
- fef_state (str): "saccade_prep" | "covert_attend" | "fixation"
                   | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class FrontalEyeFields(BrainMechanism):
    """FEF — saccade planning, top-down attention map."""

    BASELINE = 0.08
    SMOOTH = 0.22
    SACCADE_THRESHOLD = 0.55
    COVERT_THRESHOLD = 0.30
    FIXATION_THRESHOLD = 0.20
    QUIET_THRESHOLD = 0.13

    def __init__(self):
        super().__init__(
            name="FrontalEyeFields",
            human_analog="FEF (Brodmann area 8a)",
            layer="neocortical",
        )
        self.state.setdefault("fef_drive", self.BASELINE)
        self.state.setdefault("saccade_vector_signal", 0.0)
        self.state.setdefault("attention_map", 0.0)
        self.state.setdefault("target_selection", 0.0)
        self.state.setdefault("sc_input_signal", 0.0)
        self.state.setdefault("v4_modulation", 0.0)
        self.state.setdefault("fef_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("saccade_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, lip: float, v4: float, mt: float,
                       cog: float) -> float:
        """Pooled FEF drive (Schall 2002)."""
        target = (self.BASELINE
                  + lip * 0.35
                  + v4 * 0.25
                  + mt * 0.20
                  + cog * 0.15)
        return min(1.0, target)

    def _saccade_vector(self, drive: float, lip: float) -> float:
        """Movement-cell pool — saccade vector code (Bruce 1985)."""
        # Movement cells discharge before saccade onset; LIP target
        # selection feeds vector representation.
        if drive < 0.25:
            return 0.0
        return min(1.0, drive * 0.55 + lip * 0.40)

    def _attention_map(self, drive: float, v4: float,
                        target_sel: float) -> float:
        """Endogenous covert attention map (Moore 2003, Ekstrom 2008)."""
        # Top-down attention map — feeds V4/V2 modulation. Even when
        # drive is sub-saccade, FEF can support covert attention.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, drive * 0.50 + v4 * 0.25 + target_sel * 0.25)

    def _target_selection(self, drive: float, v4: float,
                            mt: float) -> float:
        """Visual selection signal (Thompson 1997)."""
        # Visual neurons select target ~100-150 ms before any saccade.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, v4 * 0.45 + mt * 0.30 + drive * 0.25)

    def _sc_input(self, vector: float, drive: float) -> float:
        """FEF → SC saccade output (Schall 2002 oculomotor circuit)."""
        return min(1.0, vector * 0.65 + drive * 0.30)

    def _v4_modulation(self, attention: float, target_sel: float) -> float:
        """FEF → V4 attentional gating (Moore 2003)."""
        # Microstimulation of FEF below saccade threshold enhances V4 —
        # this is the cortical substrate of covert spatial attention.
        return min(1.0, attention * 0.60 + target_sel * 0.35)

    def _classify_state(self, drive: float, vector: float,
                         attention: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if vector > self.SACCADE_THRESHOLD:
            return "saccade_prep"
        if attention > self.COVERT_THRESHOLD and vector < self.COVERT_THRESHOLD:
            return "covert_attend"
        if drive < self.FIXATION_THRESHOLD:
            return "fixation"
        return "engaged"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lip_data = prior.get("LateralIntraparietalArea", {})
        if not lip_data:
            lip_data = prior.get("LIP", {})
        lip = float(lip_data.get("priority_signal",
                          lip_data.get("saliency_signal",
                            lip_data.get("lip_drive", 0.0))))

        v4_data = prior.get("VisualAreaV4", {})
        if not v4_data:
            v4_data = prior.get("V4", {})
        v4 = float(v4_data.get("v4_drive", 0.0))

        mt_data = prior.get("MiddleTemporalArea", {})
        if not mt_data:
            mt_data = prior.get("MT", {})
        mt = float(mt_data.get("lip_input_signal",
                          mt_data.get("mt_drive", 0.0)))

        cog_data = prior.get("DLPFC", {})
        if not cog_data:
            cog_data = prior.get("DorsolateralPFC", {})
        cog = float(cog_data.get("control_signal",
                          cog_data.get("dlpfc_drive", 0.0)))

        target = self._drive_target(lip, v4, mt, cog)
        prev_drive = float(self.state.get("fef_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        target_sel = self._target_selection(new_drive, v4, mt)
        attention = self._attention_map(new_drive, v4, target_sel)
        vector = self._saccade_vector(new_drive, lip)
        sc_in = self._sc_input(vector, new_drive)
        v4_mod = self._v4_modulation(attention, target_sel)
        state = self._classify_state(new_drive, vector, attention)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        sacc_count = int(self.state.get("saccade_count", 0))
        if state == "saccade_prep":
            sacc_count += 1

        self.state["fef_drive"] = round(new_drive, 4)
        self.state["saccade_vector_signal"] = round(vector, 4)
        self.state["attention_map"] = round(attention, 4)
        self.state["target_selection"] = round(target_sel, 4)
        self.state["sc_input_signal"] = round(sc_in, 4)
        self.state["v4_modulation"] = round(v4_mod, 4)
        self.state["fef_state"] = state
        self.state["recent_states"] = recent
        self.state["saccade_count"] = sacc_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "fef_drive": round(new_drive, 4),
            "saccade_vector_signal": round(vector, 4),
            "attention_map": round(attention, 4),
            "target_selection": round(target_sel, 4),
            "sc_input_signal": round(sc_in, 4),
            "v4_modulation": round(v4_mod, 4),
            "fef_state": state,
        }

    def _saccade_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("saccade_count", 0) / ticks

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("fef_drive", 0.0),
            "vector": self.state.get("saccade_vector_signal", 0.0),
            "attention": self.state.get("attention_map", 0.0),
            "state": self.state.get("fef_state", "quiet"),
        }
