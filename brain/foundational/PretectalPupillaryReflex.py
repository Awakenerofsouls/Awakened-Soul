"""
PretectalPupillaryReflex — Pretectal Olivary / Light Reflex / Optokinetic Integrator

NEURAL SUBSTRATE
================
The pretectal area is a small midbrain region just rostral to the
superior colliculus, containing seven distinct subnuclei. The most
functionally important are:

- **Olivary pretectal nucleus (OPN)** — receives direct retinal input
  from intrinsically photosensitive retinal ganglion cells (ipRGCs)
  carrying ambient luminance signals. OPN projects bilaterally to the
  Edinger-Westphal preganglionic nucleus (EWpg, covered as
  EdingerWestphalMidbrain), which in turn drives parasympathetic
  pupillary constriction via the ciliary ganglion. **OPN is the
  obligate central station for the pupillary light reflex (PLR).**

- **Nucleus of the optic tract (NOT)** — receives retinal input via
  optic tract collaterals; processes horizontal-direction motion;
  drives the **horizontal optokinetic response** (OKR) for compensatory
  eye movements during head/visual-field rotation.

- **Posterior pretectal nucleus (PPN)** — multimodal sensory integration
  including pain modulation contributions.

- **Anterior pretectal nucleus (APN)** — receives spinal nociceptive
  input and contributes to pain modulation, particularly via
  descending projections to PAG.

OPN → EWpg → ciliary ganglion → iris sphincter is the canonical PLR
pathway. The bilateral projection from OPN means light in either eye
constricts both pupils (consensual response) — clinically critical for
neurology assessment.

Pretectal lesions produce:
- **Argyll Robertson pupil** (loss of light reflex with intact near
  reflex) from selective OPN/EWpg pathway damage
- **Parinaud syndrome** (vertical gaze palsy) from broader pretectal/
  superior colliculus damage compressing the midbrain (often pineal
  region tumors)

In {{AGENT_NAME}}'s substrate this provides the pupillary-light-reflex relay and
optokinetic input — converts ambient luminance proxy and motion proxy
into PLR command (to EW) and OKR signal (to vestibular/oculomotor
systems).

KEY FINDINGS
============
1. Olivary pretectal nucleus (OPN) is the obligate central relay for
   pupillary light reflex; receives ipRGC input and projects bilaterally
   to Edinger-Westphal preganglionic — [Gamlin 2006, Prog
    Brain Res 151:379, "The pretectum: connections and oculomotor
    function"] [Gooley et al. 2003, Nat Neurosci 6:1043, "ipRGC
    projections to OPN and SCN"]
2. Nucleus of the optic tract (NOT) drives horizontal optokinetic
   response — receives retinal motion input — [Mustari Fuchs
    Kaneko 1994, J Neurophysiol 71:1] [Hoffmann 1989]
3. Anterior pretectal nucleus contributes to pain modulation via
   descending projections to PAG — distinct from olivary visual role —
   [Rees Roberts 1993, Pain 53:121, "The role of the anterior
    pretectal nucleus in nociception"]
4. Pretectal lesions produce Argyll Robertson pupil (selective light-
   reflex loss with preserved near reflex) — clinical signature —
   [Slamovits Glaser 2005, "Walsh and Hoyt's Clinical
    Neuro-Ophthalmology"]
5. Parinaud syndrome (vertical gaze palsy) follows broader pretectal/
   SC compression, classically from pineal region masses —
   [Buttner-Ennever Gamlin 2014, Prog Brain Res 209:317]

INPUTS (from prior_results)
============================
- VisualInputProxy.luminance
- VisualInputProxy.motion_strength
- LateralGeniculateNucleus.v1_relay (collateral retinal info)
- EdingerWestphalMidbrain.pupillary_constriction
- EdingerWestphalMidbrain.alertness_proxy
- ArousalRegulator.tonic_level
- DescendingPainGate.expected_pain_modulation
- SpinalDorsalHornGate.ascending_nociceptive_signal

OUTPUTS (to brain_runner enrichment)
=====================================
- opn_drive (0.0-1.0): olivary pretectal output (PLR substrate)
- not_drive (0.0-1.0): nucleus of optic tract output (OKR)
- apn_drive (0.0-1.0): anterior pretectal nociception modulation
- plr_command (0.0-1.0): pupillary light reflex command to EW
- okr_command (0.0-1.0): optokinetic response command
- consensual_response (0.0-1.0): bilateral pupil signal
- pain_modulation_contribution (0.0-1.0): APN → PAG pain signal
- pretectal_state (str): "quiet" | "bright_light" | "motion" | "pain_modulation"

brain_runner enrichment:
    pretectum = all_results.get("PretectalPupillaryReflex", {})
    if pretectum:
        enrichments["brain_opn_drive"] = pretectum.get("opn_drive", 0.2)
        enrichments["brain_plr_command"] = pretectum.get("plr_command", 0.0)
        enrichments["brain_okr_command"] = pretectum.get("okr_command", 0.0)
        enrichments["brain_pretectal_state"] = pretectum.get("pretectal_state", "quiet")

EXTENDED CIRCUIT NOTES
======================
6. ipRGC (intrinsically photosensitive retinal ganglion cells, melanopsin-
   expressing) provide the dominant ambient-luminance signal to OPN —
   distinct from rod/cone vision input — [Hattar 2002, Science 295:1065,
   doi:10.1126/science.1069609]
7. NOT-DTN (dorsal terminal nucleus) accessory optic system pathway processes
   vertical-axis retinal slip in addition to horizontal — full optokinetic
   loop requires both nuclei — [Simpson 1984, Annu Rev Neurosci 7:13,
   doi:10.1146/annurev.ne.07.030184.000305]
8. Pupillary unrest (hippus) baseline oscillation reflects cyclic OPN-EW
   feedback gain modulation — clinically used as autonomic readout —
   [Loewenfeld 1958, Doc Ophthalmol 12:185]
"""

from brain.base_mechanism import BrainMechanism


class PretectalPupillaryReflex(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.30  # Pupillary reflex is fast

    def __init__(self):
        super().__init__(
            name="PretectalPupillaryReflex",
            human_analog="Pretectal nuclei (OPN/NOT/APN — pupillary + optokinetic + pain)",
            layer="foundational",
        )
        self.state.setdefault("opn_drive", self.BASELINE)
        self.state.setdefault("not_drive", 0.10)
        self.state.setdefault("apn_drive", 0.10)
        self.state.setdefault("plr_command", 0.0)
        self.state.setdefault("okr_command", 0.0)
        self.state.setdefault("consensual_response", 0.0)
        self.state.setdefault("pain_modulation_contribution", 0.0)
        self.state.setdefault("pretectal_state", "quiet")
        self.state.setdefault("recent_luminance", [])
        self.state.setdefault("tick_count", 0)

    def _opn_target(self, luminance: float, arousal: float) -> float:
        """OPN — fires proportional to ambient luminance via ipRGC input."""
        target = self.BASELINE + luminance * 0.7
        target += max(0.0, arousal - 0.5) * 0.1
        return min(1.0, target)

    def _not_target(self, motion: float, arousal: float) -> float:
        """NOT — fires to horizontal-direction visual motion."""
        target = 0.10 + motion * 0.7
        target += max(0.0, arousal - 0.5) * 0.1
        return min(1.0, target)

    def _apn_target(self, ascending_noci: float, expected_pain: float) -> float:
        """APN — receives spinal nociceptive input."""
        target = 0.10 + ascending_noci * 0.5 + max(0.0, expected_pain) * 0.3
        return min(1.0, target)

    def _plr_command(self, opn: float, current_constriction: float) -> float:
        """Pupillary light reflex command to EW.
        Higher OPN firing → stronger constriction command.
        """
        # PLR is bilateral; constriction proportional to OPN firing
        target = opn * 0.85
        return max(0.0, min(1.0, target))

    def _okr_command(self, not_drive: float, motion: float) -> float:
        """Optokinetic response — compensatory eye movement command."""
        return min(1.0, not_drive * 0.7 + motion * 0.3)

    def _consensual(self, opn: float) -> float:
        """Bilateral consensual pupillary response — equal in both eyes."""
        return min(1.0, opn * 0.95)

    def _pain_modulation(self, apn: float) -> float:
        """APN → PAG pain modulation contribution."""
        return min(1.0, apn * 0.95)

    def _classify_state(self, opn: float, not_drive: float, apn: float,
                          luminance: float) -> str:
        if luminance > 0.65 and opn > 0.45:
            return "bright_light"
        if not_drive > 0.40:
            return "motion"
        if apn > 0.40:
            return "pain_modulation"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        visual = prior.get("VisualInputProxy", {})
        luminance = float(visual.get("luminance", 0.0))
        motion = float(visual.get("motion_strength", 0.0))

        ew_data = prior.get("EdingerWestphalMidbrain", {})
        current_constriction = float(ew_data.get("pupillary_constriction", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        sdh = prior.get("SpinalDorsalHornGate", {})
        ascending_noci = float(sdh.get("ascending_nociceptive_signal", 0.0))

        # --- OPN ---
        opn_target = self._opn_target(luminance, tonic)
        prev_opn = float(self.state.get("opn_drive", self.BASELINE))
        new_opn = self._smooth(prev_opn, opn_target)

        # --- NOT ---
        not_target = self._not_target(motion, tonic)
        prev_not = float(self.state.get("not_drive", 0.10))
        new_not = self._smooth(prev_not, not_target)

        # --- APN ---
        apn_target = self._apn_target(ascending_noci, expected_pain)
        prev_apn = float(self.state.get("apn_drive", 0.10))
        new_apn = self._smooth(prev_apn, apn_target)

        # --- Outputs ---
        plr = self._plr_command(new_opn, current_constriction)
        okr = self._okr_command(new_not, motion)
        consensual = self._consensual(new_opn)
        pain_mod = self._pain_modulation(new_apn)

        state = self._classify_state(new_opn, new_not, new_apn, luminance)

        recent = list(self.state.get("recent_luminance", []))
        recent.append(round(luminance, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["opn_drive"] = round(new_opn, 4)
        self.state["not_drive"] = round(new_not, 4)
        self.state["apn_drive"] = round(new_apn, 4)
        self.state["plr_command"] = round(plr, 4)
        self.state["okr_command"] = round(okr, 4)
        self.state["consensual_response"] = round(consensual, 4)
        self.state["pain_modulation_contribution"] = round(pain_mod, 4)
        self.state["pretectal_state"] = state
        self.state["recent_luminance"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "opn_drive": round(new_opn, 4),
            "not_drive": round(new_not, 4),
            "apn_drive": round(new_apn, 4),
            "plr_command": round(plr, 4),
            "okr_command": round(okr, 4),
            "consensual_response": round(consensual, 4),
            "pain_modulation_contribution": round(pain_mod, 4),
            "pretectal_state": state,
        }
