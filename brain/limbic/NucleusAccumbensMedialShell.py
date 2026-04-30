"""
NucleusAccumbensMedialShell -- NAc-MS / Hedonic Hotspot

NEURAL SUBSTRATE
================
Medial shell of nucleus accumbens (NAc-MS) contains the canonical
hedonic hotspot -- a roughly 1mm³ subregion in rostrodorsal medial shell
where mu-opioid stimulation doubles "liking" reactions to sucrose
(Pecina & Berridge 2005). The principal substrate for affective
pleasure / "liking" -- distinct from "wanting" (which is broadly
distributed across NAc).

Inputs: BLA (appetitive), ventral hippocampus, mPFC, VTA dopamine,
PFC. Outputs: ventral pallidum (hedonic-hotspot interaction), LH,
VTA feedback.

Mu-opioid receptor expression in this hotspot is critical. Chronic
stress disrupts hedonic hotspot function -- anhedonia model.

KEY FINDINGS
============
1. NAc-MS rostrodorsal medial shell ~1 mm³ region: mu-opioid stim
   doubles hedonic impact of sweet tastes -- "liking" hotspot --
   [Pecina 2005, J Neurosci 25:11777, doi:10.1523/JNEUROSCI.2329-05.2005]
2. NAc shell + ventral pallidum hedonic hotspots interact bidirectionally
   to amplify pleasure -- opioid limbic circuit -- [Smith 2007,
   J Neurosci 27:1594, doi:10.1523/JNEUROSCI.4205-06.2007]
3. Pleasure systems in brain involve hedonic hotspots in NAc shell, VP,
   and orbitofrontal cortex -- limited not unitary --
   [Berridge 2008, Neuron 86:646, PMC4425246]
4. NAc shell hedonic dysfunction in chronic stress models = anhedonia;
   mu-opioid signaling impaired -- [Russo 2013, Nat Rev Neurosci 14:609,
   doi:10.1038/nrn3381]
5. D1+ direct pathway in NAc shell drives reward; D2+ indirect inhibits;
   distinct populations -- [Kravitz 2012, Nat Neurosci 15:816,
   doi:10.1038/nn.3100]

INPUTS
======
- BasolateralAmygdala.appetitive_signal (or BasalAmygdala.nac_drive_command)
- HippocampalCA1Output.ca1_drive
- VentralTegmentalDopamine.da_release
- ValenceTagger.valence_sign, .valence_intensity
- OpioidProxy.mu_opioid_level

OUTPUTS
=======
- nac_ms_drive (0-1)
- liking_hedonic_signal (0-1)
- wanting_motivation_signal (0-1)
- vp_appetitive_drive (0-1)
- d1_direct_pathway (0-1)
- d2_indirect_pathway (0-1)
- nac_ms_state (str): "liking_active" | "wanting_active" |
  "anhedonic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensMedialShell(BrainMechanism):
    """NAc-MS -- hedonic hotspot, "liking" + "wanting" signals."""

    BASELINE = 0.10
    SMOOTH = 0.20
    LIKING_THRESHOLD = 0.40
    WANTING_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensMedialShell",
            human_analog="Nucleus accumbens medial shell (hedonic hotspot)",
            layer="limbic",
        )
        self.state.setdefault("nac_ms_drive", self.BASELINE)
        self.state.setdefault("liking_hedonic_signal", 0.0)
        self.state.setdefault("wanting_motivation_signal", 0.0)
        self.state.setdefault("vp_appetitive_drive", 0.0)
        self.state.setdefault("d1_direct_pathway", 0.0)
        self.state.setdefault("d2_indirect_pathway", 0.0)
        self.state.setdefault("nac_ms_state", "quiet")
        self.state.setdefault("anhedonia_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, ca1: float, da: float,
                       appetitive: float, mu_opioid: float) -> float:
        """NAc-MS firing -- appetitive-driven, opioid-amplified (Pecina 2005)."""
        target = self.BASELINE + bla * 0.30 + ca1 * 0.15 + appetitive * 0.30
        target += mu_opioid * 0.25
        target += da * 0.15
        return min(1.0, target)

    def _liking_signal(self, mu_opioid: float, drive: float,
                         appetitive: float) -> float:
        """Liking hedonic signal -- mu-opioid required for amplification
        (Pecina 2005). Without opioid, liking is at baseline only.
        """
        if mu_opioid < 0.20:
            # Baseline liking proportional to drive
            return min(1.0, drive * 0.3 + appetitive * 0.15)  # lowered from 0.3; anhedonia requires appetitive to NOT drive liking without opioid
        # Hedonic hotspot -- opioid doubles liking
        return min(1.0, drive * 0.4 + appetitive * 0.3 + mu_opioid * 0.6)

    def _wanting_signal(self, da: float, drive: float) -> float:
        """Wanting motivation -- DA-driven, distinct from liking."""
        return min(1.0, da * 0.6 + drive * 0.4)

    def _vp_appetitive(self, drive: float, liking: float) -> float:
        """NAc-MS→VP appetitive output (Smith 2007 hotspot interaction)."""
        return min(1.0, drive * 0.5 + liking * 0.5)

    def _d1_direct(self, drive: float, da: float) -> float:
        """D1+ direct pathway (Kravitz 2012)."""
        return min(1.0, drive * 0.5 + da * 0.5)

    def _d2_indirect(self, drive: float, da: float) -> float:
        """D2+ indirect pathway -- inhibitory; rises when DA is low."""
        if da > 0.50:
            return drive * 0.2
        return min(1.0, drive * 0.5 + (1.0 - da) * 0.4)

    def _classify_state(self, liking: float, wanting: float, drive: float,
                          anhedonia_streak: int) -> str:
        if anhedonia_streak > 50 and liking < 0.10:
            return "anhedonic"
        if liking > self.LIKING_THRESHOLD:
            return "liking_active"
        if wanting > self.WANTING_THRESHOLD:
            return "wanting_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("appetitive_signal",
                        bla_data.get("nac_drive_command",
                            bla_data.get("ba_extinction_neurons", 0.0))))

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        vta_data = prior.get("VentralTegmentalDopamine", {})
        da = float(vta_data.get("da_release", vta_data.get("da_burst", 0.0)))

        valence = prior.get("ValenceTagger", {})
        sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        appetitive = max(0.0, sign * intensity)

        opioid_data = prior.get("OpioidProxy", {})
        mu_opioid = float(opioid_data.get("mu_opioid_level", 0.0))

        target = self._drive_target(bla, ca1, da, appetitive, mu_opioid)
        prev_drive = float(self.state.get("nac_ms_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        liking = self._liking_signal(mu_opioid, new_drive, appetitive)
        wanting = self._wanting_signal(da, new_drive)
        vp_app = self._vp_appetitive(new_drive, liking)
        d1 = self._d1_direct(new_drive, da)
        d2 = self._d2_indirect(new_drive, da)

        prev_streak = int(self.state.get("anhedonia_streak", 0))
        if liking < 0.20 and appetitive > 0.30:
            anhedonia_streak = prev_streak + 1
        else:
            anhedonia_streak = max(0, prev_streak - 2)

        state = self._classify_state(liking, wanting, new_drive, anhedonia_streak)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nac_ms_drive"] = round(new_drive, 4)
        self.state["liking_hedonic_signal"] = round(liking, 4)
        self.state["wanting_motivation_signal"] = round(wanting, 4)
        self.state["vp_appetitive_drive"] = round(vp_app, 4)
        self.state["d1_direct_pathway"] = round(d1, 4)
        self.state["d2_indirect_pathway"] = round(d2, 4)
        self.state["nac_ms_state"] = state
        self.state["anhedonia_streak"] = anhedonia_streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nac_ms_drive": round(new_drive, 4),
            "liking_hedonic_signal": round(liking, 4),
            "wanting_motivation_signal": round(wanting, 4),
            "vp_appetitive_drive": round(vp_app, 4),
            "d1_direct_pathway": round(d1, 4),
            "d2_indirect_pathway": round(d2, 4),
            "nac_ms_state": state,
            "anhedonia_streak": anhedonia_streak,
        }

    def _hotspot_amplification(self, mu_opioid: float, baseline: float) -> float:
        """Hedonic hotspot amplification factor -- Pecina 2005 measured
        approximately 2x liking gain at peak. Multiplier returned."""
        if mu_opioid < 0.20:
            return 1.0
        return 1.0 + min(1.0, mu_opioid * 1.2)

    def _anhedonia_severity_index(self, anhedonia_streak: int,
                                     liking: float) -> float:
        """Anhedonia severity index -- NAc-MS liking signal
        below threshold for sustained period. Returns clinical
        proxy (0=subclinical, 1=severe anhedonia)."""
        if anhedonia_streak < 10:
            return 0.0
        return min(1.0, anhedonia_streak / 100.0 * (1.0 - liking))

    def _dopamine_sensitivity_proxy(self, da: float,
                                      wanting: float) -> float:
        """Dopamine sensitivity proxy -- NAc-MS DA response
        magnitude. High DA + high wanting = normal sensitivity;
        high DA + low wanting = blunted DA sensitivity."""
        if da < 0.10:
            return 0.0
        if wanting > da * 0.5:
            return min(1.0, wanting / max(0.1, da))
        return max(0.0, 1.0 - wanting / max(0.1, da))

    def _incentive_sensitization_proxy(self, wanting: float,
                                        da: float,
                                        prev_wanting: float) -> float:
        """Incentive sensitization proxy -- wanting grows
        faster than DA over time in sensitized state.
        Model of addiction incentive sensitization theory."""
        if da < 0.20 or prev_wanting < 0.20:
            return 0.0
        growth = wanting - prev_wanting
        return max(0.0, growth * 2.0)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("nac_ms_drive", 0.0),
            "liking": self.state.get("liking_hedonic_signal", 0.0),
            "wanting": self.state.get("wanting_motivation_signal", 0.0),
            "state": self.state.get("nac_ms_state", "quiet"),
        }
