"""
AnteroDorsalThalamus — AD — head-direction cell relay (Papez)

NEURAL SUBSTRATE
================
The anterodorsal thalamic nucleus (AD) is the canonical thalamic
head-direction (HD) relay. AD contains the highest density of pure HD
cells in the brain — Taube 1995 reported that ~60% of AD cells are
sharply tuned to azimuthal head direction, with narrow tuning curves
that drift with environment manipulations. AD receives bilateral
projection from the lateral mammillary nucleus (LMN) and reciprocal
projections with the postsubiculum (presubiculum) and retrosplenial
cortex. AD HD cells lead behavior by ~25 ms — implicating AD in
predictive head-direction signaling.

Lesions of LMN bilaterally abolish AD HD signal (Bassett et al. 2007),
while lesions of retrosplenial cortex degrade AD HD stability under
landmark rotation (Clark et al. 2010). AD does not require visual
input for HD firing per se, but visual landmarks anchor the HD
representation through the postsubicular-retrosplenial-LMN loop.

KEY FINDINGS
============
1. AD pure head-direction cells with narrow azimuthal tuning
   [Taube JS 1995, J Neurosci 15:70, doi:10.1523/JNEUROSCI.15-01-00070.1995]
2. Lateral mammillary lesions abolish AD head-direction signal
   [Bassett JP 2007, J Neurosci 27:7564, doi:10.1523/JNEUROSCI.0268-07.2007]
3. Retrosplenial lesions impair AD HD stability under landmark rotation
   [Clark BJ 2010, J Neurosci 30:5289, doi:10.1523/JNEUROSCI.5894-09.2010]
4. AD HD cells lead behavior by ~25 ms (anticipatory firing)
   [Blair HT 1995, J Neurosci 15:6260, doi:10.1523/JNEUROSCI.15-09-06260.1995]
5. AD inactivation impairs spatial navigation in radial maze
   [Aggleton JP 1996, Behav Brain Res 81:189, doi:10.1016/S0166-4328(96)89080-2]
6. AD-RSC oscillatory synchrony coordinates HD network
   [Tsanov M 2014, Eur J Neurosci 39:1718, doi:10.1111/ejn.12526]

INPUTS
======
- MammillaryBodyLateral.lmn_drive (bilateral driver — HD+AHV)
- PrePresubiculum.head_direction_signal (postsubicular HD)
- RetrosplenialCortex.cortical_drive (Layer-VI feedback)
- VestibularNuclei.vestibular_signal (indirectly via supragenual/LMN)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- ad_drive (0-1)
- hd_signal (0-1) — head-direction tuning amplitude
- presubicular_signal (0-1)
- retrosplenial_signal (0-1)
- anticipatory_signal (0-1) — phase-led prediction
- ad_state (str): "hd_active" | "drift" | "anchored" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteroDorsalThalamus(BrainMechanism):
    """AD — head-direction cell thalamic relay."""

    BASELINE = 0.09
    SMOOTH = 0.22
    HD_THRESHOLD = 0.35
    ANCHOR_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="AnteroDorsalThalamus",
            human_analog="Anterodorsal thalamic nucleus (AD)",
            layer="subcortical",
        )
        self.state.setdefault("ad_drive", self.BASELINE)
        self.state.setdefault("hd_signal", 0.0)
        self.state.setdefault("presubicular_signal", 0.0)
        self.state.setdefault("retrosplenial_signal", 0.0)
        self.state.setdefault("anticipatory_signal", 0.0)
        self.state.setdefault("ad_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("hd_count", 0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_hd", 0.0)

    # ---- helper sub-signals ----

    def _lmn_driver(self, lmn: float) -> float:
        """Lateral mammillary driver (Bassett 2007).

        Bilateral LMN lesion abolishes AD HD signal — LMN is the
        obligate HD driver. Without LMN, AD HD ≈ 0.
        """
        return min(1.0, lmn * 1.10)

    def _drive_target(self, lmn: float, presub: float, ctx: float,
                      vest: float, trn: float) -> float:
        """Composite AD drive."""
        excitation = (self.BASELINE
                      + lmn * 0.45
                      + presub * 0.20
                      + ctx * 0.10
                      + vest * 0.10)
        inhibition = trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _hd_tuning(self, drive: float, lmn: float, presub: float) -> float:
        """HD tuning amplitude — requires LMN driver (Taube 1995).

        Without LMN, HD signal is abolished even with cortical/presub
        input present (Bassett 2007 lesion data).
        """
        if lmn < 0.05:
            return 0.0
        return min(1.0, lmn * 0.7 + drive * 0.2 + presub * 0.1)

    def _anticipatory(self, hd: float, prev_hd: float) -> float:
        """Anticipatory phase lead (~25 ms; Blair 1995).

        We model anticipation as the positive temporal derivative of HD
        amplitude — when HD is rising AD predicts forthcoming heading.
        """
        delta = hd - prev_hd
        if delta <= 0.0:
            return 0.0
        return min(1.0, delta * 4.0 + hd * 0.3)

    def _anchor_quality(self, hd: float, ctx: float, presub: float) -> float:
        """How well HD is anchored to landmarks (Clark 2010).

        RSC + presubiculum stabilize the HD signal against drift.
        """
        if hd < 0.10:
            return 0.0
        return min(1.0, hd * 0.4 + ctx * 0.35 + presub * 0.25)

    def _presubicular_signal(self, drive: float, hd: float) -> float:
        """Output back to presubiculum."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.45 + hd * 0.35)

    def _retrosplenial_signal(self, drive: float, hd: float,
                               anchor: float) -> float:
        """Output to RSC (Tsanov 2014)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.45 + hd * 0.30 + anchor * 0.20)

    def _classify_state(self, drive: float, hd: float, anchor: float,
                         lmn: float) -> str:
        if drive < 0.13:
            return "quiet"
        if hd < self.HD_THRESHOLD and lmn < 0.10:
            return "drift"
        if anchor > self.ANCHOR_THRESHOLD and hd > self.HD_THRESHOLD:
            return "anchored"
        if hd > self.HD_THRESHOLD:
            return "hd_active"
        return "drift"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lmn_data = prior.get("MammillaryBodyLateral", {})
        if not lmn_data:
            lmn_data = prior.get("LateralMammillary", {})
        if not lmn_data:
            lmn_data = prior.get("MammillaryBody", {})
        lmn = float(lmn_data.get("lmn_drive",
                          lmn_data.get("lateral_mammillary_output",
                              lmn_data.get("hd_drive",
                                  lmn_data.get("output", 0.0)))))

        presub_data = prior.get("PrePresubiculum", {})
        if not presub_data:
            presub_data = prior.get("Postsubiculum", {})
        if not presub_data:
            presub_data = prior.get("ParaSubiculum", {})
        presub = float(presub_data.get("head_direction_signal",
                              presub_data.get("hd_drive",
                                  presub_data.get("presubicular_output", 0.0))))

        ctx_data = prior.get("RetrosplenialCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                          ctx_data.get("rsc_drive", 0.0)))

        vest_data = prior.get("VestibularNuclei", {})
        if not vest_data:
            vest_data = prior.get("MedialVestibularNucleus", {})
        vest = float(vest_data.get("vestibular_signal",
                            vest_data.get("vestibular_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        lmn_eff = self._lmn_driver(lmn)
        target = self._drive_target(lmn_eff, presub, ctx, vest, trn)
        prev_drive = float(self.state.get("ad_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        hd = self._hd_tuning(new_drive, lmn_eff, presub)
        prev_hd = float(self.state.get("last_hd", 0.0))
        antic = self._anticipatory(hd, prev_hd)
        anchor = self._anchor_quality(hd, ctx, presub)

        presub_sig = self._presubicular_signal(new_drive, hd)
        rsc = self._retrosplenial_signal(new_drive, hd, anchor)

        state = self._classify_state(new_drive, hd, anchor, lmn_eff)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        hd_count = int(self.state.get("hd_count", 0))
        if state in ("hd_active", "anchored"):
            hd_count += 1

        self.state["ad_drive"] = round(new_drive, 4)
        self.state["hd_signal"] = round(hd, 4)
        self.state["presubicular_signal"] = round(presub_sig, 4)
        self.state["retrosplenial_signal"] = round(rsc, 4)
        self.state["anticipatory_signal"] = round(antic, 4)
        self.state["ad_state"] = state
        self.state["recent_states"] = recent
        self.state["hd_count"] = hd_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["last_hd"] = round(hd, 4)
        self.persist_state()

        return {
            "ad_drive": round(new_drive, 4),
            "hd_signal": round(hd, 4),
            "presubicular_signal": round(presub_sig, 4),
            "retrosplenial_signal": round(rsc, 4),
            "anticipatory_signal": round(antic, 4),
            "ad_state": state,
        }

    def _hd_engagement(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("hd_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ad_drive", 0.0),
            "hd": self.state.get("hd_signal", 0.0),
            "anchor": self.state.get("retrosplenial_signal", 0.0),
            "state": self.state.get("ad_state", "quiet"),
        }
