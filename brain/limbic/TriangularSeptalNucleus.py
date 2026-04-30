"""
TriangularSeptalNucleus — TS / Medial Septal Inhibitory Modulator

NEURAL SUBSTRATE
================
The triangular septal nucleus (TS) is a small midline structure in the
septal complex, distinct from the lateral septum and medial septum. TS
neurons project to the medial habenula (MHb) — a critical input route
for limbic-habenular communication. Qin & Luo 2009 demonstrated TS→MHb
projections are predominantly substance-P-positive and modulate aversive
processing via downstream interpeduncular nucleus.

TS receives input from posterior septofimbrial nucleus, hippocampus, and
hypothalamus. Functionally, TS is a small but important node in the
septohabenular-interpeduncular axis ("dorsal diencephalic conduction
system"; Sutherland 1982) that gates aversive memory expression.

KEY FINDINGS
============
1. Triangular septal nucleus projects to medial habenula via
   substance-P pathway; major MHb afferent —
   [Qin 2009, Front Neuroanat 3:25, doi:10.3389/neuro.05.025.2009]
2. Septal-habenular-interpeduncular axis = "dorsal diencephalic
   conduction system"; integrates aversive limbic signals —
   [Sutherland 1982, Neurosci Biobehav Rev 6:1, PMID 7041014]
3. TS neurons co-express substance P + glutamate; activate medial
   habenula —
   [Hsu 2014, Neuron 84:1213, doi:10.1016/j.neuron.2014.11.008]
4. Septofimbrial → TS → MHb pathway gates negative-affect-driven
   behavioral responses; selective TS lesion reduces aversive
   conditioning —
   [Yamaguchi 2013, J Neurosci 33:14365, doi:10.1523/JNEUROSCI.4385-12.2013]
5. TS-MHb-IPN circuit is conserved across vertebrates; ancient
   aversive limbic circuit —
   [Aizawa 2011, J Comp Neurol 519:4051, doi:10.1002/cne.22685]

INPUTS
======
- SeptofimbrialNucleus.sfi_drive (or septofimbrial signal)
- HippocampalCA1Ventral.vca1_drive
- HypothalamicLateral.lh_drive

OUTPUTS
=======
- ts_drive (0-1)
- mhb_substance_p_signal (0-1)
- aversive_relay_signal (0-1)
- ts_state (str): "aversive_active" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class TriangularSeptalNucleus(BrainMechanism):
    """TS — septohabenular substance-P relay."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AVERSIVE_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="TriangularSeptalNucleus",
            human_analog="Triangular septal nucleus",
            layer="limbic",
        )
        self.state.setdefault("ts_drive", self.BASELINE)
        self.state.setdefault("mhb_substance_p_signal", 0.0)
        self.state.setdefault("aversive_relay_signal", 0.0)
        self.state.setdefault("ts_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, sfi: float, vca1: float, lh: float) -> float:
        """TS drive (Qin 2009)."""
        target = (self.BASELINE
                  + sfi * 0.40
                  + vca1 * 0.30
                  + lh * 0.20)
        return min(1.0, target)

    def _substance_p(self, drive: float, sfi: float) -> float:
        """TS→MHb substance-P projection (Hsu 2014)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.6 + sfi * 0.3)

    def _aversive_relay(self, drive: float, vca1: float, lh: float) -> float:
        """Aversive limbic relay to MHb-IPN axis (Yamaguchi 2013)."""
        return min(1.0, drive * 0.4 + vca1 * 0.3 + lh * 0.3)

    def _classify_state(self, drive: float, aversive: float) -> str:
        if drive < 0.20:
            return "quiet"
        if aversive > self.AVERSIVE_THRESHOLD:
            return "aversive_active"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sfi_data = prior.get("SeptofimbrialNucleus", {})
        sfi = float(sfi_data.get("sfi_drive",
                          sfi_data.get("septofimbrial_signal", 0.0)))

        vca1_data = prior.get("HippocampalCA1Ventral", {})
        if not vca1_data:
            vca1_data = prior.get("HippocampalCA1", {})
        vca1 = float(vca1_data.get("vca1_drive",
                            vca1_data.get("ca1_output", 0.0)))

        lh_data = prior.get("HypothalamicLateral", {})
        if not lh_data:
            lh_data = prior.get("LateralHypothalamus", {})
        lh = float(lh_data.get("lh_drive",
                          lh_data.get("hypothalamus_drive", 0.0)))

        target = self._drive_target(sfi, vca1, lh)
        prev_drive = float(self.state.get("ts_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sub_p = self._substance_p(new_drive, sfi)
        aversive = self._aversive_relay(new_drive, vca1, lh)

        state = self._classify_state(new_drive, aversive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ts_drive"] = round(new_drive, 4)
        self.state["mhb_substance_p_signal"] = round(sub_p, 4)
        self.state["aversive_relay_signal"] = round(aversive, 4)
        self.state["ts_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ts_drive": round(new_drive, 4),
            "mhb_substance_p_signal": round(sub_p, 4),
            "aversive_relay_signal": round(aversive, 4),
            "ts_state": state,
        }

    def _conduction_engagement(self) -> float:
        """Engagement of dorsal diencephalic conduction system (Sutherland 1982)."""
        return float(self.state.get("aversive_relay_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ts_drive", 0.0),
            "substance_p": self.state.get("mhb_substance_p_signal", 0.0),
            "aversive": self.state.get("aversive_relay_signal", 0.0),
            "state": self.state.get("ts_state", "quiet"),
        }
