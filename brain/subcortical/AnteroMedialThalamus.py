"""
AnteroMedialThalamus — AM — Papez / mPFC-cingulate-hippocampal integration

NEURAL SUBSTRATE
================
The anteromedial thalamic nucleus (AM) is the most medial of the three
anterior thalamic nuclei (with AV, AD) and the principal node integrating
prefrontal, cingulate and hippocampal-formation signals within the
extended Papez circuit. AM receives input from medial mammillary nucleus
(via the mammillothalamic tract), subiculum (via the postcommissural
fornix), retrosplenial cortex, perirhinal cortex, and prelimbic /
infralimbic cortex; AM projects to medial prefrontal cortex (especially
prelimbic and anterior cingulate) and perirhinal cortex.

Functionally AM is implicated in temporal-order memory, recency memory,
and rapid transfer of information between hippocampus and prefrontal
cortex (Jankowski et al. 2013; Jankowski 2014). AM lesions impair recency
discrimination and tasks requiring integration of contextual and temporal
information. Sub-regional functional dissection (Mathiasen et al. 2017;
Aggleton & O'Mara 2022) suggests AM serves a coordinating role similar
in spirit to nucleus reuniens but anchored within the Papez return loop.

KEY FINDINGS
============
1. AM densely interconnected with prefrontal / perirhinal cortex
   [Shibata H 1992, J Comp Neurol 323:117, doi:10.1002/cne.903230110]
2. AM lesions impair recency / temporal-order memory in rats
   [Mitchell AS 2007, Neuropsychologia 45:1538, doi:10.1016/j.neuropsychologia.2006.12.009]
3. Anterior thalamic nuclei (incl. AM) support memory and spatial navigation
   [Jankowski MM 2013, Front Syst Neurosci 7:45, doi:10.3389/fnsys.2013.00045]
4. AM head-direction and theta-modulated cells (spatial integration)
   [Jankowski MM 2014, J Neurosci 34:12246, doi:10.1523/JNEUROSCI.2588-14.2014]
5. AM and AV form distinct mPFC sub-circuits with parallel anatomy
   [Mathiasen ML 2017, Cereb Cortex 27:5887, doi:10.1093/cercor/bhx272]
6. AM contributes to flexible decision-making via prefrontal coupling
   [Wolff M 2015, J Neurosci 35:13551, doi:10.1523/JNEUROSCI.0210-15.2015]

INPUTS
======
- MammillaryBodyMedial.mmn_drive (mammillothalamic driver)
- SubiculumDorsal.subiculum_output (postcommissural fornix)
- PrelimbicCortex.cortical_drive (Layer-VI feedback)
- RetrosplenialCortex.cortical_drive
- PerirhinalCortex.cortical_drive (recency / item memory)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- am_drive (0-1)
- pfc_signal (0-1) — to prelimbic / cingulate
- perirhinal_signal (0-1) — recency / item integration
- temporal_order_signal (0-1)
- hippo_pfc_bridge_signal (0-1)
- am_state (str): "integrating" | "recency_active" | "relay" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteroMedialThalamus(BrainMechanism):
    """AM — Papez/mPFC/hippocampal integration thalamic relay."""

    BASELINE = 0.09
    SMOOTH = 0.22
    INTEGRATE_THRESHOLD = 0.40
    RECENCY_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="AnteroMedialThalamus",
            human_analog="Anteromedial thalamic nucleus (AM)",
            layer="subcortical",
        )
        self.state.setdefault("am_drive", self.BASELINE)
        self.state.setdefault("pfc_signal", 0.0)
        self.state.setdefault("perirhinal_signal", 0.0)
        self.state.setdefault("temporal_order_signal", 0.0)
        self.state.setdefault("hippo_pfc_bridge_signal", 0.0)
        self.state.setdefault("am_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("integrate_count", 0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("recency_buffer", [])

    # ---- helper sub-signals ----

    def _papez_driver(self, mmn: float, sub: float) -> float:
        """Pooled Papez (MMN + subicular) driver input.

        Both sources converge on AM via mammillothalamic tract and
        postcommissural fornix respectively.
        """
        return min(1.0, mmn * 0.55 + sub * 0.55)

    def _drive_target(self, papez: float, pfc: float, rsc: float,
                      perr: float, trn: float) -> float:
        """Composite AM drive."""
        excitation = (self.BASELINE
                      + papez * 0.40
                      + pfc * 0.20
                      + rsc * 0.12
                      + perr * 0.13)
        inhibition = trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _temporal_order(self, drive: float, perr: float,
                        recency_var: float) -> float:
        """Recency / temporal-order memory (Mitchell 2007).

        AM is required for ordering recent items; we model this as drive
        × perirhinal × recency-buffer variability (changing recent input
        increases temporal-order signal).
        """
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + perr * 0.4 + recency_var * 0.4)

    def _hippo_pfc_bridge(self, drive: float, sub: float,
                           pfc: float) -> float:
        """Hippocampal-prefrontal coordination signal (Jankowski 2013)."""
        if drive < 0.12:
            return 0.0
        # bridge requires BOTH hippocampal (subicular) and PFC drive
        return min(1.0, drive * 0.3 + sub * pfc * 1.4)

    def _pfc_signal(self, drive: float, papez: float) -> float:
        """Output to prelimbic / cingulate (Shibata 1992)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.50 + papez * 0.30)

    def _perirhinal_signal(self, drive: float, perr_in: float) -> float:
        """Output to perirhinal cortex."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.40 + perr_in * 0.35)

    def _classify_state(self, drive: float, bridge: float,
                         temporal: float) -> str:
        if drive < 0.13:
            return "quiet"
        if bridge > self.INTEGRATE_THRESHOLD:
            return "integrating"
        if temporal > self.RECENCY_THRESHOLD:
            return "recency_active"
        return "relay"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mmn_data = prior.get("MammillaryBodyMedial", {})
        if not mmn_data:
            mmn_data = prior.get("MedialMammillary", {})
        if not mmn_data:
            mmn_data = prior.get("MammillaryBody", {})
        mmn = float(mmn_data.get("mmn_drive",
                          mmn_data.get("medial_mammillary_output",
                              mmn_data.get("output", 0.0))))

        sub_data = prior.get("SubiculumDorsal", {})
        if not sub_data:
            sub_data = prior.get("Subiculum", {})
        sub = float(sub_data.get("subiculum_output",
                          sub_data.get("subicular_output", 0.0)))

        pfc_data = prior.get("PrelimbicCortex", {})
        if not pfc_data:
            pfc_data = prior.get("mPFC", {})
        if not pfc_data:
            pfc_data = prior.get("CingulateAnterior", {})
        pfc = float(pfc_data.get("cortical_drive",
                          pfc_data.get("pfc_drive",
                              pfc_data.get("prelimbic_drive", 0.0))))

        rsc_data = prior.get("RetrosplenialCortex", {})
        rsc = float(rsc_data.get("cortical_drive",
                           rsc_data.get("rsc_drive", 0.0)))

        perr_data = prior.get("PerirhinalCortex", {})
        perr = float(perr_data.get("cortical_drive",
                            perr_data.get("perirhinal_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        papez = self._papez_driver(mmn, sub)
        target = self._drive_target(papez, pfc, rsc, perr, trn)
        prev_drive = float(self.state.get("am_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # Update recency buffer (last 5 inputs of perr)
        buf = list(self.state.get("recency_buffer", []))
        buf.append(round(perr, 3))
        if len(buf) > 5:
            buf = buf[-5:]
        # Variability of recent perirhinal input — proxies item-change
        if len(buf) >= 2:
            mean = sum(buf) / len(buf)
            recency_var = sum(abs(x - mean) for x in buf) / len(buf)
        else:
            recency_var = 0.0
        recency_var = min(1.0, recency_var * 2.0)

        temporal = self._temporal_order(new_drive, perr, recency_var)
        bridge = self._hippo_pfc_bridge(new_drive, sub, pfc)
        pfc_sig = self._pfc_signal(new_drive, papez)
        perr_sig = self._perirhinal_signal(new_drive, perr)

        state = self._classify_state(new_drive, bridge, temporal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        integrate_count = int(self.state.get("integrate_count", 0))
        if state == "integrating":
            integrate_count += 1

        self.state["am_drive"] = round(new_drive, 4)
        self.state["pfc_signal"] = round(pfc_sig, 4)
        self.state["perirhinal_signal"] = round(perr_sig, 4)
        self.state["temporal_order_signal"] = round(temporal, 4)
        self.state["hippo_pfc_bridge_signal"] = round(bridge, 4)
        self.state["am_state"] = state
        self.state["recent_states"] = recent
        self.state["integrate_count"] = integrate_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["recency_buffer"] = buf
        self.persist_state()

        return {
            "am_drive": round(new_drive, 4),
            "pfc_signal": round(pfc_sig, 4),
            "perirhinal_signal": round(perr_sig, 4),
            "temporal_order_signal": round(temporal, 4),
            "hippo_pfc_bridge_signal": round(bridge, 4),
            "am_state": state,
        }

    def _integration_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("integrate_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("am_drive", 0.0),
            "pfc": self.state.get("pfc_signal", 0.0),
            "bridge": self.state.get("hippo_pfc_bridge_signal", 0.0),
            "state": self.state.get("am_state", "quiet"),
        }
