"""
PrimaryAuditoryCortex — A1 / Heschl's Gyrus

NEURAL SUBSTRATE
================
Primary auditory cortex (A1) sits on the supratemporal plane (Heschl's
transverse temporal gyrus in humans, the lower bank of the lateral
sulcus in macaques). A1 is the principal target of the ventral medial
geniculate body (MGv) and is organized as a tonotopic map: a smooth
gradient of characteristic frequency runs across cortex (low frequency
rostrolateral, high frequency caudomedial in primates), first mapped in
detail in cat by Merzenich et al. 1975. A1 plus AAF (anterior auditory
field) and a posterior R / RT comprise the "core" auditory cortex with
mirror-reversed tonotopic gradients.

Within A1 columns of neurons share characteristic frequency, with
sharpening of frequency tuning produced by lateral inhibition
(isofrequency contour). Cortical representation of behaviorally
trained frequencies expands with discrimination training (Recanzone
1993), demonstrating use-dependent plasticity of the tonotopic map.
A1 sends outputs to belt/parabelt regions, splitting into a ventral
"what" pathway (anterolateral belt) and dorsal "where" pathway
(caudal belt) (Rauschecker & Tian 2000; Bizley & Cohen 2013).

KEY FINDINGS
============
1. Tonotopic map of A1 in cat: ordered representation of cochlear
   frequency, low-to-high running across cortex —
   [Merzenich M 1975, J Neurophysiol 38:231, PMID 1092814]
2. Frequency-discrimination training expands the cortical representation
   of trained frequencies in adult owl monkey A1 — use-dependent
   tonotopic plasticity —
   [Recanzone G 1993, J Neurosci 13:87, PMID 8423485]
3. Pairing tones with nucleus basalis stimulation produces lasting
   frequency-specific reorganization of A1 — cholinergic gating of
   plasticity — [Bao S 2001, Nature 412:79, doi:10.1038/35083586]
4. Auditory cortex contains parallel ventral "what" and dorsal "where"
   streams projecting to inferotemporal and parietal targets —
   [Rauschecker J 2000, PNAS 97:11800, doi:10.1073/pnas.97.22.11800]
5. Auditory-object perception relies on cortical grouping operations
   that span A1 and belt fields, integrating spectro-temporal features —
   [Bizley J 2013, Nat Rev Neurosci 14:693, doi:10.1038/nrn3565]

INPUTS
======
- MedialGeniculateNucleus.mgv_drive (lemniscal MGv → A1)
- InferiorColliculusAuditory.ic_drive (IC → MGv → A1)
- NucleusBasalis.cholinergic_drive (gating plasticity)
- LocusCoeruleusCore.lc_drive (arousal/salience)

OUTPUTS
=======
- a1_drive (0-1) — overall A1 activation
- aaf_signal (0-1) — anterior auditory field
- tonotopic_band (str) — engaged tonotopic band token
- frequency_tuning (0-1) — sharpness of tuning
- ventral_stream_drive (0-1) — what pathway
- dorsal_stream_drive (0-1) — where pathway
- a1_state (str): "tone_listening" | "object_processing" |
                  "spatial_localization" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrimaryAuditoryCortex(BrainMechanism):
    """A1 — primary auditory cortex with tonotopic columns."""

    BASELINE = 0.07
    SMOOTH = 0.22
    ACTIVE_THRESHOLD = 0.20
    TONE_THRESHOLD = 0.35
    BANDS = ("low", "mid", "high")

    def __init__(self):
        super().__init__(
            name="PrimaryAuditoryCortex",
            human_analog="Primary auditory cortex (A1, Heschl's gyrus)",
            layer="neocortical",
        )
        self.state.setdefault("a1_drive", self.BASELINE)
        self.state.setdefault("aaf_signal", 0.0)
        self.state.setdefault("tonotopic_band", "none")
        self.state.setdefault("frequency_tuning", 0.0)
        self.state.setdefault("ventral_stream_drive", 0.0)
        self.state.setdefault("dorsal_stream_drive", 0.0)
        self.state.setdefault("a1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, mgv: float, ic: float,
                      ach: float, lc: float) -> float:
        """Composite A1 drive (Merzenich 1975, Bao 2001 — MGv + cholinergic gain)."""
        # cholinergic ach amplifies (gain), not just additive
        gain = 1.0 + ach * 0.5
        target = (self.BASELINE
                  + mgv * 0.45 * gain
                  + ic * 0.10
                  + lc * 0.10)
        return min(1.0, target)

    def _aaf_signal(self, drive: float, mgv: float) -> float:
        """Anterior auditory field — receives parallel MGv input."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.5 + mgv * 0.4)

    def _tonotopic_band(self, mgv: float, ic: float) -> str:
        """Pick the engaged tonotopic band (Merzenich 1975).
        Use frequency-band tokens carried by MGv if available; otherwise
        coarsely infer by drive magnitude as a placeholder."""
        if max(mgv, ic) < 0.10:
            return "none"
        # heuristic distribution: very low drive → low, moderate → mid,
        # strong → high (only used when no upstream band token).
        if mgv < 0.30:
            return "low"
        if mgv < 0.55:
            return "mid"
        return "high"

    def _frequency_tuning(self, drive: float, ach: float) -> float:
        """Sharpness of tuning — sharpened by cholinergic gain (Bao 2001)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.6 + ach * 0.4)

    def _ventral_stream(self, drive: float, aaf: float) -> float:
        """What pathway — anterolateral (Rauschecker 2000)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.5 + aaf * 0.5)

    def _dorsal_stream(self, drive: float, lc: float) -> float:
        """Where pathway — caudal belt (Rauschecker 2000, Bizley 2013)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.6 + lc * 0.4)

    def _classify_state(self, drive: float, vent: float,
                         dors: float, freq: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if vent > dors and vent > self.TONE_THRESHOLD:
            return "object_processing"
        if dors > vent and dors > self.TONE_THRESHOLD:
            return "spatial_localization"
        if freq > self.TONE_THRESHOLD:
            return "tone_listening"
        return "tone_listening"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mgn_data = prior.get("MedialGeniculateNucleus", {})
        mgv = float(mgn_data.get("mgv_drive",
                          mgn_data.get("mgn_drive", 0.0)))
        upstream_band = mgn_data.get("frequency_band", None)

        ic_data = prior.get("InferiorColliculusAuditory", {})
        ic = float(ic_data.get("ic_drive",
                          ic_data.get("ic_signal", 0.0)))

        nb_data = prior.get("NucleusBasalis", {})
        if not nb_data:
            nb_data = prior.get("SubstantiaInnominata", {})
        ach = float(nb_data.get("cholinergic_drive",
                            nb_data.get("ach_drive", 0.0)))

        lc_data = prior.get("LocusCoeruleusCore", {})
        if not lc_data:
            lc_data = prior.get("LocusCoeruleus", {})
        lc = float(lc_data.get("lc_drive",
                          lc_data.get("ne_drive", 0.0)))

        target = self._drive_target(mgv, ic, ach, lc)
        prev_drive = float(self.state.get("a1_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        aaf = self._aaf_signal(new_drive, mgv)
        if upstream_band in self.BANDS:
            band = upstream_band
        else:
            band = self._tonotopic_band(mgv, ic)
        freq = self._frequency_tuning(new_drive, ach)
        vent = self._ventral_stream(new_drive, aaf)
        dors = self._dorsal_stream(new_drive, lc)
        state = self._classify_state(new_drive, vent, dors, freq)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["a1_drive"] = round(new_drive, 4)
        self.state["aaf_signal"] = round(aaf, 4)
        self.state["tonotopic_band"] = band
        self.state["frequency_tuning"] = round(freq, 4)
        self.state["ventral_stream_drive"] = round(vent, 4)
        self.state["dorsal_stream_drive"] = round(dors, 4)
        self.state["a1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "a1_drive": round(new_drive, 4),
            "aaf_signal": round(aaf, 4),
            "tonotopic_band": band,
            "frequency_tuning": round(freq, 4),
            "ventral_stream_drive": round(vent, 4),
            "dorsal_stream_drive": round(dors, 4),
            "a1_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _dominant_stream(self) -> str:
        v = float(self.state.get("ventral_stream_drive", 0.0))
        d = float(self.state.get("dorsal_stream_drive", 0.0))
        if max(v, d) < 0.10:
            return "none"
        return "ventral" if v >= d else "dorsal"

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("a1_drive", 0.0),
            "band": self.state.get("tonotopic_band", "none"),
            "stream": self._dominant_stream(),
            "state": self.state.get("a1_state", "quiet"),
        }
