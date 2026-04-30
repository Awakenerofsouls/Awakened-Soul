"""
InferotemporalCortex — IT / Inferior Temporal Cortex (TE/TEO)

NEURAL SUBSTRATE
================
Inferotemporal cortex (IT) is the apex of the ventral visual ("what")
stream in primates. In macaque it spans area TEO (posterior IT) and
area TE (anterior IT) on the inferior surface and lateral wall of the
temporal lobe; in human, the homologous regions include lateral
occipitotemporal cortex, the fusiform gyrus, and inferior temporal
gyrus (LOC, FFA, OTS). IT receives feedforward input from V4 (PIT/TEO
→ TE), heavy reciprocal projections from perirhinal cortex (area 35/36),
modulatory input from amygdala, prefrontal cortex (top-down), and
pulvinar.

Functionally IT is where vision becomes object recognition:
  - Object cells: single IT neurons selective for complex objects
    (Tanaka 1996), often invariant across position, size, and partly
    across viewpoint (Logothetis & Pauls 1995).
  - Face patches: 6 functionally connected face-selective regions
    (PL, ML, MF, AL, AF, AM) in macaque IT, each ~1-2 mm wide; nearly
    all neurons in middle face patches are face-selective (Tsao et al.
    2006). Patches form a hierarchy from view-specific (ML/MF) to
    view-invariant identity (AM) — Freiwald & Tsao 2010.
  - Categorical encoding: population code reads object identity from
    ~100-200 IT neurons in ~100 ms (Hung et al. 2005), supporting
    rapid categorization.
  - View invariance: a small (~5-10%) but systematic IT subpopulation
    is view-invariant; experience tunes invariance.
  - DiCarlo's untangling: IT representation makes object identity
    linearly separable, "untangling" pixel manifolds (DiCarlo et al.
    2012).

IT lesions abolish object/face discrimination while sparing low-level
vision; pharmacological perturbation of face patches biases identity
judgments. IT is the cortical substrate of semantic visual recognition.

KEY FINDINGS
============
1. View-tuned and view-invariant IT cells emerge with experience;
   majority view-tuned, ~5-10% view-invariant —
   [Logothetis NK 1995, Cereb Cortex 5:270, doi:10.1093/cercor/5.3.270]
2. Six face patches in macaque IT; cells in middle face patches are
   ~97% face-selective —
   [Tsao DY 2006, Science 311:670, doi:10.1126/science.1119983]
3. Macaque face-patch hierarchy progresses from view-specific (ML/MF)
   to mirror-symmetric (AL) to view-invariant identity (AM) —
   [Freiwald WA 2010, Science 330:845, doi:10.1126/science.1194908]
4. Object identity is linearly decodable from a small population of IT
   neurons (~100), with ~100 ms latency, supporting rapid object
   recognition —
   [Hung CP 2005, Science 310:863, doi:10.1126/science.1117593]
5. Ventral stream "untangles" object identity into a linearly
   separable representation — IT is the readout layer for recognition —
   [DiCarlo JJ 2012, Neuron 73:415, doi:10.1016/j.neuron.2012.01.010]

INPUTS
======
- VisualAreaV4.it_input_signal (V4 → PIT → TE)
- VisualAreaV4.color_signal
- VisualAreaV4.form_signal
- VisualAreaV4.attention_gain
- PerirhinalCortex.perirhinal_drive (reciprocal)
- AmygdalaBasolateral / LateralAmygdala (emotional modulation, optional)

OUTPUTS
=======
- it_drive (0-1) — overall IT activation
- object_signal (0-1) — generic object/category readout
- face_signal (0-1) — face-patch pool activity
- view_invariance (0-1) — invariance index (AM-like)
- recognition_signal (0-1) — linearly readable identity (DiCarlo 2012)
- perirhinal_input_signal (0-1) — IT → perirhinal / MTL
- it_state (str): "face_active" | "object_active" | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class InferotemporalCortex(BrainMechanism):
    """IT / TE — object & face recognition, view-invariance, ventral apex."""

    BASELINE = 0.07
    SMOOTH = 0.20
    FACE_THRESHOLD = 0.45
    OBJECT_THRESHOLD = 0.35
    ENGAGED_THRESHOLD = 0.18
    QUIET_THRESHOLD = 0.12

    def __init__(self):
        super().__init__(
            name="InferotemporalCortex",
            human_analog="IT (TE/TEO/FFA) — ventral stream apex",
            layer="neocortical",
        )
        self.state.setdefault("it_drive", self.BASELINE)
        self.state.setdefault("object_signal", 0.0)
        self.state.setdefault("face_signal", 0.0)
        self.state.setdefault("view_invariance", 0.0)
        self.state.setdefault("recognition_signal", 0.0)
        self.state.setdefault("perirhinal_input_signal", 0.0)
        self.state.setdefault("it_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("face_event_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v4_in: float, color: float, form: float,
                       att: float, perirhinal: float) -> float:
        """Pooled IT drive — V4 dominates with attentional gain."""
        ff = v4_in * 0.35 + color * 0.15 + form * 0.20 + perirhinal * 0.15
        gain = 1.0 + att * 0.30  # attentional gain (Moore 2003 chain)
        target = self.BASELINE + ff * gain
        return min(1.0, target)

    def _object_response(self, drive: float, form: float,
                          color: float) -> float:
        """Generic object-cell pool (Tanaka 1996, DiCarlo 2012)."""
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, form * 0.45 + color * 0.25 + drive * 0.30)

    def _face_response(self, drive: float, form: float,
                        att: float) -> float:
        """Face-patch pool (Tsao 2006, Freiwald 2010)."""
        # Face patches dominate when high-form input + sufficient drive;
        # attentional gain enhances face-patch firing.
        if drive < 0.20:
            return 0.0
        base = form * 0.55 + drive * 0.35
        gain = 1.0 + att * 0.20
        return min(1.0, base * gain)

    def _view_invariance(self, drive: float, face: float,
                          object_sig: float) -> float:
        """View-invariance index (Logothetis 1995, Freiwald 2010 AM)."""
        # View-invariance grows with sustained drive; AM-like cells are
        # rare (~5-10%) but systematic. Index pooled from face/object
        # population strength.
        if drive < 0.20:
            return 0.0
        # Invariance is sub-linear in drive (only a fraction of cells).
        return min(1.0, (face + object_sig) * 0.30 + drive * 0.20)

    def _recognition_readout(self, drive: float, object_sig: float,
                               face: float, invar: float) -> float:
        """Linearly readable identity signal (DiCarlo 2012, Hung 2005)."""
        # Population code → linearly separable identity.
        return min(1.0, object_sig * 0.40 + face * 0.30 + invar * 0.20
                    + drive * 0.10)

    def _perirhinal_input(self, recognition: float, drive: float) -> float:
        """IT → perirhinal cortex (gateway to MTL)."""
        return min(1.0, recognition * 0.65 + drive * 0.30)

    def _classify_state(self, drive: float, face: float,
                         object_sig: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if face > self.FACE_THRESHOLD and face >= object_sig:
            return "face_active"
        if object_sig > self.OBJECT_THRESHOLD:
            return "object_active"
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
        v4_in = float(v4_data.get("it_input_signal", 0.0))
        color = float(v4_data.get("color_signal", 0.0))
        form = float(v4_data.get("form_signal", 0.0))
        att = float(v4_data.get("attention_gain", 0.0))

        peri_data = prior.get("PerirhinalCortex", {})
        perirhinal = float(peri_data.get("perirhinal_drive",
                                  peri_data.get("perirhinal_signal",
                                    peri_data.get("drive", 0.0))))

        target = self._drive_target(v4_in, color, form, att, perirhinal)
        prev_drive = float(self.state.get("it_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        object_sig = self._object_response(new_drive, form, color)
        face = self._face_response(new_drive, form, att)
        invar = self._view_invariance(new_drive, face, object_sig)
        recognition = self._recognition_readout(new_drive, object_sig,
                                                  face, invar)
        peri_in = self._perirhinal_input(recognition, new_drive)
        state = self._classify_state(new_drive, face, object_sig)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        face_count = int(self.state.get("face_event_count", 0))
        if state == "face_active":
            face_count += 1

        self.state["it_drive"] = round(new_drive, 4)
        self.state["object_signal"] = round(object_sig, 4)
        self.state["face_signal"] = round(face, 4)
        self.state["view_invariance"] = round(invar, 4)
        self.state["recognition_signal"] = round(recognition, 4)
        self.state["perirhinal_input_signal"] = round(peri_in, 4)
        self.state["it_state"] = state
        self.state["recent_states"] = recent
        self.state["face_event_count"] = face_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "it_drive": round(new_drive, 4),
            "object_signal": round(object_sig, 4),
            "face_signal": round(face, 4),
            "view_invariance": round(invar, 4),
            "recognition_signal": round(recognition, 4),
            "perirhinal_input_signal": round(peri_in, 4),
            "it_state": state,
        }

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("it_drive", 0.0),
            "object": self.state.get("object_signal", 0.0),
            "face": self.state.get("face_signal", 0.0),
            "invariance": self.state.get("view_invariance", 0.0),
            "state": self.state.get("it_state", "quiet"),
        }
