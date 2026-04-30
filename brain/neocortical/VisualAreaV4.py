"""
VisualAreaV4 — V4 / Mid-Ventral-Stream Visual Area

NEURAL SUBSTRATE
================
V4 lies on the prelunate gyrus of the macaque (homologous human regions
include hV4 / V4d on the lateral occipital lobe). It is a critical
mid-level node of the ventral "what" stream, sandwiched between V2 and
posterior IT (PIT/TEO). V4 receives major feedforward input from V2
thin and pale interstripes (Sincich & Horton 2002 / V2 chapter), plus
direct V1 input via the parvocellular stream, and projects to PIT and
TEO en route to anterior IT.

V4 was originally described by Zeki as a "color area" because of its
prominent color-opponent neurons, but it is now understood as an
intermediate-shape and feature-attention hub:
  - Color and form are jointly encoded; modular color domains co-exist
    with curvature/shape domains (Roe et al. 2012, Conway et al. 2007).
  - Curvature- and contour-feature tuning: V4 cells encode boundary
    conformation (Pasupathy & Connor 1999) — angles, curves, junctions.
    This is intermediate between V2 simple-orientation combinations and
    IT whole-object selectivity.
  - Feature-based attention: V4 firing rates are modulated by both
    spatial attention (Connor et al. 1996/1997) and feature attention
    (McAdams & Maunsell 1999) — gain ~20-30% with attended target.
  - Top-down modulation by FEF (Moore & Armstrong 2003) and
    parietal/IT feedback.

V4 lesions in monkey produce mild but reliable deficits in shape
discrimination, color constancy, and feature-based attention
(Schiller). V4 → IT carries the form/color information that ultimately
supports object recognition.

KEY FINDINGS
============
1. V4 neurons exhibit position-specific tuning for boundary
   conformation — curvature/angle features at specific positions
   relative to object centroid, an intermediate shape code —
   [Pasupathy A 1999, J Neurophysiol 82:2490, PMID 10561421]
2. Spatial attention enhances V4 responses ~20-30% for stimuli at the
   attended location, gain modulation rather than added bias —
   [Connor CE 1996, J Neurophysiol 75:1306, doi:10.1152/jn.1996.75.3.1306]
3. Feature-based attention multiplicatively scales V4 orientation
   tuning curves without changing tuning width —
   [McAdams CJ 1999, J Neurosci 19:431, PMID 9870972]
4. V4 contains an orderly hue map: color-tuned neurons cluster into
   "globs" with systematic hue progression —
   [Conway BR 2007, J Neurosci 27:13751, doi:10.1523/JNEUROSCI.4039-07.2007]
5. V4 functional architecture: color, orientation, curvature and
   disparity organized into segregated but interleaved modular domains —
   [Roe AW 2012, Neuron 74:12, doi:10.1016/j.neuron.2012.03.011]

INPUTS
======
- SecondaryVisualCortex.v4_input_signal (primary V2 → V4 drive)
- SecondaryVisualCortex.thin_stripe_signal (color)
- SecondaryVisualCortex.pale_stripe_signal (form)
- FrontalEyeFields.attention_map (top-down attention)
- LateralIntraparietalArea.priority_signal (parietal saliency)

OUTPUTS
=======
- v4_drive (0-1)
- color_signal (0-1) — color-opponent / hue-glob output
- form_signal (0-1) — curvature / boundary-conformation output
- attention_gain (0-1) — feature/spatial attention modulation
- it_input_signal (0-1) — V4 → IT (PIT/TEO/AIT)
- v4_state (str): "attended_object" | "form_dominant" | "color_dominant"
                  | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VisualAreaV4(BrainMechanism):
    """V4 — color + form, attention modulation, ventral stream."""

    BASELINE = 0.08
    SMOOTH = 0.22
    ATTENDED_THRESHOLD = 0.50
    DOMAIN_THRESHOLD = 0.35
    ENGAGED_THRESHOLD = 0.20
    QUIET_THRESHOLD = 0.15

    def __init__(self):
        super().__init__(
            name="VisualAreaV4",
            human_analog="V4 (mid-ventral stream)",
            layer="neocortical",
        )
        self.state.setdefault("v4_drive", self.BASELINE)
        self.state.setdefault("color_signal", 0.0)
        self.state.setdefault("form_signal", 0.0)
        self.state.setdefault("attention_gain", 0.0)
        self.state.setdefault("it_input_signal", 0.0)
        self.state.setdefault("v4_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v2_in: float, thin: float, pale: float,
                       fef_att: float, lip_pri: float) -> float:
        """Pooled V4 drive with attentional gain (Moore 2003)."""
        feedforward = v2_in * 0.30 + thin * 0.20 + pale * 0.25
        # Attention is multiplicative on feedforward — gain modulation
        # (McAdams 1999, Connor 1996).
        att_gain = 1.0 + (fef_att * 0.30 + lip_pri * 0.20)
        target = self.BASELINE + feedforward * att_gain
        return min(1.0, target)

    def _color_response(self, drive: float, thin: float) -> float:
        """Hue-glob / color-opponent response (Conway 2007)."""
        # Color-tuned cells form glob domains; thin-stripe input
        # (V1 blob → V2 thin → V4 glob) is the canonical color path.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, thin * 0.65 + drive * 0.30)

    def _form_response(self, drive: float, pale: float) -> float:
        """Curvature / boundary-conformation tuning (Pasupathy 1999)."""
        # Pale interstripes carry orientation/contour combinations →
        # V4 curvature domains.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, pale * 0.65 + drive * 0.30)

    def _attention_gain(self, fef: float, lip: float, drive: float) -> float:
        """Top-down attentional modulation (Moore 2003, Bisley 2010)."""
        # FEF (microstimulation enhances V4) + LIP priority map.
        return min(1.0, fef * 0.50 + lip * 0.35 + drive * 0.15)

    def _it_input(self, color: float, form: float, att: float,
                   drive: float) -> float:
        """V4 → IT projection (ventral stream output)."""
        # Both color and form converge on IT; attention prioritizes
        # which features reach IT.
        ff = color * 0.35 + form * 0.40 + drive * 0.25
        # Attention gates the projection ~20-30%.
        gain = 1.0 + att * 0.30
        return min(1.0, ff * gain)

    def _classify_state(self, drive: float, color: float, form: float,
                         att: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if att > self.ATTENDED_THRESHOLD and drive > 0.30:
            return "attended_object"
        if form > self.DOMAIN_THRESHOLD and form > color + 0.10:
            return "form_dominant"
        if color > self.DOMAIN_THRESHOLD and color > form + 0.10:
            return "color_dominant"
        if drive > self.ENGAGED_THRESHOLD:
            return "engaged"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v2_data = prior.get("SecondaryVisualCortex", {})
        if not v2_data:
            v2_data = prior.get("V2", {})
        v2_in = float(v2_data.get("v4_input_signal", 0.0))
        thin = float(v2_data.get("thin_stripe_signal", 0.0))
        pale = float(v2_data.get("pale_stripe_signal", 0.0))

        fef_data = prior.get("FrontalEyeFields", {})
        fef_att = float(fef_data.get("attention_map",
                              fef_data.get("attention_signal",
                                fef_data.get("fef_drive", 0.0))))

        lip_data = prior.get("LateralIntraparietalArea", {})
        lip_pri = float(lip_data.get("priority_signal",
                              lip_data.get("saliency_signal",
                                lip_data.get("lip_drive", 0.0))))

        target = self._drive_target(v2_in, thin, pale, fef_att, lip_pri)
        prev_drive = float(self.state.get("v4_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        color = self._color_response(new_drive, thin)
        form = self._form_response(new_drive, pale)
        att = self._attention_gain(fef_att, lip_pri, new_drive)
        it_in = self._it_input(color, form, att, new_drive)
        state = self._classify_state(new_drive, color, form, att)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["v4_drive"] = round(new_drive, 4)
        self.state["color_signal"] = round(color, 4)
        self.state["form_signal"] = round(form, 4)
        self.state["attention_gain"] = round(att, 4)
        self.state["it_input_signal"] = round(it_in, 4)
        self.state["v4_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "v4_drive": round(new_drive, 4),
            "color_signal": round(color, 4),
            "form_signal": round(form, 4),
            "attention_gain": round(att, 4),
            "it_input_signal": round(it_in, 4),
            "v4_state": state,
        }

    def _color_form_balance(self) -> float:
        """0 = all form, 1 = all color (Roe 2012 module balance)."""
        c = self.state.get("color_signal", 0.0)
        f = self.state.get("form_signal", 0.0)
        if (c + f) < 0.01:
            return 0.5
        return c / (c + f)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("v4_drive", 0.0),
            "color": self.state.get("color_signal", 0.0),
            "form": self.state.get("form_signal", 0.0),
            "attention": self.state.get("attention_gain", 0.0),
            "state": self.state.get("v4_state", "quiet"),
        }
