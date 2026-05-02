"""
ParahippocampalPlaceArea — PPA (Posterior Parahippocampal Cortex)

NEURAL SUBSTRATE
================
The parahippocampal place area (PPA) is a category-selective region in
posterior parahippocampal cortex / collateral sulcus, just lateral and
ventral to the hippocampus on the inferior temporal lobe. Discovered
by Epstein & Kanwisher (1998) using fMRI, it responds robustly to
images of scenes and places (rooms, landscapes, buildings, navigable
spaces) but only weakly to single objects and not at all to faces —
the converse selectivity to the FFA.

Connectivity:
  - Visual input: from posterior IT (TEO/PIT), V4 dorsal, lateral
    occipital cortex.
  - Hippocampal/entorhinal: bidirectional with parahippocampal cortex
    (postrhinal homolog) and entorhinal cortex — the canonical
    "where" pathway into MTL.
  - Retrosplenial cortex (RSC) — close functional partner for spatial
    navigation.
  - PPA is part of the scene network: PPA + RSC + occipital place
    area (OPA / TOS).

Functional properties:
  - Scene/place selectivity: strong response to environments,
    landscapes, rooms, buildings.
  - Spatial layout selectivity: PPA responds to spatial structure
    even without recognizable objects — empty rooms drive it as
    strongly as furnished rooms (Epstein & Kanwisher 1998); responses
    track local geometry / spatial layout (Epstein 2008 review).
  - High spatial frequency preference (Kornblith et al. 2013;
    Rajimehr et al. 2011 for monkey homolog).
  - Encodes scene category and viewpoint; supports navigation,
    landmark recognition, scene-based spatial memory.
  - Scene-selective response is fast (~150-250 ms) and largely
    automatic (Bar 2003 — rapid scene gist).

PPA lesions / damage produce topographical disorientation and
landmark agnosia.

KEY FINDINGS
============
1. PPA responds selectively to scenes/places with spatial layout,
   weakly to objects, not at all to faces — discovery paper —
   [Epstein R 1998, Nature 392:598, doi:10.1038/33402]
2. PPA encodes spatial layout and geometry; reviews evidence that PPA
   represents local environmental geometry —
   [Epstein RA 2008, Trends Cogn Sci 12:388, doi:10.1016/j.tics.2008.07.004]
3. Top-down facilitation of visual recognition: medial temporal /
   parahippocampal context aids rapid scene gist —
   [Bar M 2003, J Cogn Neurosci 15:600, doi:10.1162/089892903321662976]
4. PPA preferentially responds to high spatial frequencies in human
   and macaque homolog, consistent with layout/geometry coding —
   [Kornblith S 2013, Curr Biol 23:1936, doi:10.1016/j.cub.2013.07.083]
5. Convergent fMRI evidence: parahippocampal cortex responds to
   environmental scenes / topographical content in episodic spatial
   memory —
   [Aguirre GK 1996, Cereb Cortex 6:823, doi:10.1093/cercor/6.6.823]

INPUTS
======
- VisualAreaV4.v4_drive (mid-level form input)
- InferotemporalCortex.it_drive (high-level visual context)
- PostrhinalCortex.postrhinal_drive (spatial / contextual MTL)
- HippocampalCA1Output / EntorhinalCortexGridCells (spatial gating)

OUTPUTS
=======
- ppa_drive (0-1)
- scene_signal (0-1) — scene/place selectivity
- spatial_layout_signal (0-1) — geometric layout (Epstein 2008)
- landmark_signal (0-1) — landmark/place recognition
- entorhinal_input_signal (0-1) — PPA → EC (spatial pathway)
- rsc_input_signal (0-1) — PPA → retrosplenial cortex
- ppa_state (str): "scene_recognized" | "layout_active"
                   | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ParahippocampalPlaceArea(BrainMechanism):
    """PPA — scene/place recognition and spatial layout coding."""

    BASELINE = 0.07
    SMOOTH = 0.20
    SCENE_THRESHOLD = 0.45
    LAYOUT_THRESHOLD = 0.30
    ENGAGED_THRESHOLD = 0.18
    QUIET_THRESHOLD = 0.12

    def __init__(self):
        super().__init__(
            name="ParahippocampalPlaceArea",
            human_analog="PPA (parahippocampal place area, Epstein 1998)",
            layer="neocortical",
        )
        self.state.setdefault("ppa_drive", self.BASELINE)
        self.state.setdefault("scene_signal", 0.0)
        self.state.setdefault("spatial_layout_signal", 0.0)
        self.state.setdefault("landmark_signal", 0.0)
        self.state.setdefault("entorhinal_input_signal", 0.0)
        self.state.setdefault("rsc_input_signal", 0.0)
        self.state.setdefault("ppa_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("scene_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v4: float, it: float, postrhinal: float,
                       ec: float) -> float:
        """Pooled PPA drive (Epstein 1998 / 2008)."""
        target = (self.BASELINE
                  + v4 * 0.20
                  + it * 0.25
                  + postrhinal * 0.30
                  + ec * 0.15)
        return min(1.0, target)

    def _scene_response(self, drive: float, it: float,
                         postrhinal: float) -> float:
        """Scene/place-selective response (Epstein 1998)."""
        # PPA responds to scenes selectively — pooled IT (high-level
        # category context) and postrhinal (spatial/contextual MTL).
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, it * 0.35 + postrhinal * 0.40 + drive * 0.25)

    def _spatial_layout(self, drive: float, v4: float,
                         postrhinal: float) -> float:
        """Spatial layout / geometry response (Epstein 2008, Kornblith 2013)."""
        # Layout-selective component — drives even on empty rooms;
        # high-spatial-frequency / geometric content.
        if drive < 0.15:
            return 0.0
        return min(1.0, v4 * 0.30 + postrhinal * 0.35 + drive * 0.30)

    def _landmark(self, scene: float, layout: float) -> float:
        """Landmark / place recognition (Aguirre 1996)."""
        # Landmark recognition emerges from scene + layout pooling.
        return min(1.0, scene * 0.55 + layout * 0.40)

    def _entorhinal_input(self, scene: float, layout: float,
                           landmark: float) -> float:
        """PPA → EC (spatial pathway into MTL / hippocampal grid)."""
        return min(1.0, scene * 0.30 + layout * 0.35 + landmark * 0.30)

    def _rsc_input(self, scene: float, layout: float,
                    drive: float) -> float:
        """PPA → retrosplenial cortex (scene / heading network)."""
        return min(1.0, scene * 0.40 + layout * 0.35 + drive * 0.20)

    def _classify_state(self, drive: float, scene: float,
                         layout: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if scene > self.SCENE_THRESHOLD:
            return "scene_recognized"
        if layout > self.LAYOUT_THRESHOLD:
            return "layout_active"
        if drive > self.ENGAGED_THRESHOLD:
            return "engaged"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v4_data = prior.get("VisualAreaV4", {})
        if not v4_data:
            v4_data = prior.get("V4", {})
        v4 = float(v4_data.get("v4_drive", 0.0))

        it_data = prior.get("InferotemporalCortex", {})
        if not it_data:
            it_data = prior.get("IT", {})
        it = float(it_data.get("it_drive",
                          it_data.get("object_signal", 0.0)))

        post_data = prior.get("PostrhinalCortex", {})
        if not post_data:
            post_data = prior.get("ParahippocampalCortex", {})
        postrhinal = float(post_data.get("postrhinal_drive",
                                  post_data.get("postrhinal_signal",
                                    post_data.get("drive", 0.0))))

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        if not ec_data:
            ec_data = prior.get("EntorhinalLayer3", {})
        ec = float(ec_data.get("grid_signal",
                          ec_data.get("ec_drive",
                            ec_data.get("temporoammonic_signal", 0.0))))

        target = self._drive_target(v4, it, postrhinal, ec)
        prev_drive = float(self.state.get("ppa_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        scene = self._scene_response(new_drive, it, postrhinal)
        layout = self._spatial_layout(new_drive, v4, postrhinal)
        landmark = self._landmark(scene, layout)
        ec_in = self._entorhinal_input(scene, layout, landmark)
        rsc_in = self._rsc_input(scene, layout, new_drive)
        state = self._classify_state(new_drive, scene, layout)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        scene_count = int(self.state.get("scene_count", 0))
        if state == "scene_recognized":
            scene_count += 1

        self.state["ppa_drive"] = round(new_drive, 4)
        self.state["scene_signal"] = round(scene, 4)
        self.state["spatial_layout_signal"] = round(layout, 4)
        self.state["landmark_signal"] = round(landmark, 4)
        self.state["entorhinal_input_signal"] = round(ec_in, 4)
        self.state["rsc_input_signal"] = round(rsc_in, 4)
        self.state["ppa_state"] = state
        self.state["recent_states"] = recent
        self.state["scene_count"] = scene_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ppa_drive": round(new_drive, 4),
            "scene_signal": round(scene, 4),
            "spatial_layout_signal": round(layout, 4),
            "landmark_signal": round(landmark, 4),
            "entorhinal_input_signal": round(ec_in, 4),
            "rsc_input_signal": round(rsc_in, 4),
            "ppa_state": state,
        }

    def _scene_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("scene_count", 0) / ticks

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ppa_drive", 0.0),
            "scene": self.state.get("scene_signal", 0.0),
            "layout": self.state.get("spatial_layout_signal", 0.0),
            "landmark": self.state.get("landmark_signal", 0.0),
            "state": self.state.get("ppa_state", "quiet"),
        }
