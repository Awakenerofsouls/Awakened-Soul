"""
SupraopticNucleus — SON — Magnocellular Vasopressin/Oxytocin Output

NEURAL SUBSTRATE
================
The supraoptic nucleus (SON) sits dorsolateral to the optic chiasm and
is the dominant magnocellular neurosecretory nucleus, alongside the
magnocellular subdivision of the PVN. The SON is composed almost
exclusively (~99%) of large magnocellular neurons that project axons
through the internal layer of the median eminence and infundibular
stem to terminate in the posterior pituitary (neurohypophysis), where
they release arginine-vasopressin (AVP) and oxytocin (OT) directly
into systemic blood.

SON neurons are osmotically tuned: they are excited by hypertonicity
detected by intrinsic stretch-inactivated TRPV-like channels and by
glutamatergic afferents from the OVLT and SFO (lamina terminalis
osmoreceptors). They are also activated by the milk-ejection reflex
(suckling input via spinothalamic afferents) and by parturition
(Ferguson reflex from cervical/uterine stretch). Phasic-bursting
firing patterns optimize peptide release at axon terminals.

Unlike PVN, SON is purely magnocellular: it does not house parvocellular
CRH neurons or presympathetic neurons. Its sole output is to the
posterior pituitary (and dendritic local release).

KEY FINDINGS
============
1. Central mechanisms of osmosensation: SON osmosensitive magnocellular
   neurons integrate intrinsic and OVLT/SFO afferent osmoreception —
   [Bourque C 2008, Nat Rev Neurosci 9:519, doi:10.1038/nrn2400]
2. Dendritic peptide release from SON/PVN magnocellular neurons modulates
   distant brain regions independently of axonal release —
   [Ludwig M 2006, Nat Rev Neurosci 7:126, doi:10.1038/nrn1845]
3. Physiological regulation of magnocellular neurosecretory cells
   integrates intrinsic, local and afferent mechanisms; phasic bursting
   optimizes pituitary release —
   [Brown C 2013, J Neuroendocrinol 25:678, doi:10.1111/jne.12051]
4. Saper-Scammell-Lu integrative review of hypothalamic regulation
   places SON within the homeostatic/neuroendocrine network —
   [Saper C 2005, Nature 437:1257, doi:10.1038/nature04284]
5. Vasopressin/oxytocin systems show sex differences regulating social
   behavior; magnocellular outflow contributes to systemic signaling.
   [Dumais K 2016, Front Neuroendocrinol 40:1, doi:10.1016/j.yfrne.2015.04.003]
6. Ulrich-Lai/Herman integrative model: posterior pituitary AVP
   complements PVN-driven HPA outflow in the autonomic stress response
   — [Ulrich-Lai Y 2009, Nat Rev Neurosci 10:397, doi:10.1038/nrn2647]

INPUTS
======
- MedianPreopticNucleus.osmotic_signal (lamina terminalis osmoreceptor)
- A2NoradrenergicNTS.a2_signal (volume/baroreflex)
- ParaventricularNucleusHypothalamus.pvn_drive (cross-coupling)
- MedialAmygdalaPosterior.social_signal (lactation/social context)

OUTPUTS
=======
- son_drive (0-1)
- avp_pituitary (0-1) — neurohypophyseal AVP release
- oxytocin_pituitary (0-1) — neurohypophyseal OT release
- dendritic_peptide_release (0-1) — local autocrine/paracrine
- phasic_burst_signal (0-1) — magnocellular phasic firing index
- son_state (str): "osmotic_release" | "milk_ejection" |
                    "phasic_bursting" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SupraopticNucleus(BrainMechanism):
    """SON — magnocellular AVP/OT to posterior pituitary."""

    BASELINE = 0.08
    SMOOTH = 0.20
    OSMOTIC_THRESHOLD = 0.40
    BURST_THRESHOLD = 0.50
    OT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="SupraopticNucleus",
            human_analog="SON (magnocellular AVP/OT neurosecretion)",
            layer="subcortical",
        )
        self.state.setdefault("son_drive", self.BASELINE)
        self.state.setdefault("avp_pituitary", 0.0)
        self.state.setdefault("oxytocin_pituitary", 0.0)
        self.state.setdefault("dendritic_peptide_release", 0.0)
        self.state.setdefault("phasic_burst_signal", 0.0)
        self.state.setdefault("son_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("burst_count", 0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("burst_phase", 0)

    def _drive_target(self, osmotic: float, a2: float,
                       pvn: float, social: float) -> float:
        """Composite SON drive (Bourque 2008 — osmoreceptive integration)."""
        target = (self.BASELINE
                  + osmotic * 0.45
                  + a2 * 0.20
                  + pvn * 0.15
                  + social * 0.20)
        return min(1.0, target)

    def _avp_release(self, drive: float, osmotic: float,
                      a2: float) -> float:
        """Neurohypophyseal AVP secretion (Brown 2013)."""
        if drive < 0.15 and osmotic < 0.15:
            return 0.0
        return min(1.0, osmotic * 0.55 + drive * 0.30 + a2 * 0.20)

    def _ot_release(self, drive: float, social: float) -> float:
        """Neurohypophyseal oxytocin (Dumais 2016)."""
        if drive < 0.10 and social < 0.10:
            return 0.0
        return min(1.0, social * 0.55 + drive * 0.40)

    def _dendritic(self, drive: float, avp: float, ot: float) -> float:
        """Dendritic peptide release (Ludwig 2006)."""
        # Dendritic release scales with overall peptidergic drive
        return min(1.0, drive * 0.4 + (avp + ot) * 0.30)

    def _phasic_burst(self, drive: float) -> float:
        """Phasic bursting characteristic of magnocellular AVP neurons."""
        # Burst pattern emerges when drive exceeds threshold; oscillates
        if drive < 0.25:
            self.state["burst_phase"] = 0
            return 0.0
        phase = int(self.state.get("burst_phase", 0))
        phase = (phase + 1) % 6
        self.state["burst_phase"] = phase
        # Phasic bursts: 3 active, 3 silent (idealized)
        if phase < 3:
            return min(1.0, drive * 1.0)
        return min(1.0, drive * 0.20)

    def _classify_state(self, drive: float, avp: float,
                         ot: float, burst: float) -> str:
        if drive < 0.15:
            return "quiet"
        if ot > self.OT_THRESHOLD:
            return "milk_ejection"
        if avp > self.OSMOTIC_THRESHOLD:
            return "osmotic_release"
        if burst > self.BURST_THRESHOLD:
            return "phasic_bursting"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mnpo_data = prior.get("MedianPreopticNucleus", {})
        osmotic = float(mnpo_data.get("osmotic_signal",
                            mnpo_data.get("thirst_drive", 0.0)))

        a2_data = prior.get("A2NoradrenergicNTS", {})
        a2 = float(a2_data.get("a2_signal",
                          a2_data.get("noradrenergic_drive", 0.0)))

        pvn_data = prior.get("ParaventricularNucleusHypothalamus", {})
        pvn = float(pvn_data.get("pvn_drive",
                          pvn_data.get("avp_magnocellular", 0.0)))

        social_data = prior.get("MedialAmygdalaPosterior", {})
        social = float(social_data.get("social_signal",
                            social_data.get("med_amyg_drive", 0.0)))

        target = self._drive_target(osmotic, a2, pvn, social)
        prev_drive = float(self.state.get("son_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        avp = self._avp_release(new_drive, osmotic, a2)
        ot = self._ot_release(new_drive, social)
        dendritic = self._dendritic(new_drive, avp, ot)
        burst = self._phasic_burst(new_drive)

        state = self._classify_state(new_drive, avp, ot, burst)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        burst_count = int(self.state.get("burst_count", 0))
        if state == "phasic_bursting":
            burst_count += 1

        self.state["son_drive"] = round(new_drive, 4)
        self.state["avp_pituitary"] = round(avp, 4)
        self.state["oxytocin_pituitary"] = round(ot, 4)
        self.state["dendritic_peptide_release"] = round(dendritic, 4)
        self.state["phasic_burst_signal"] = round(burst, 4)
        self.state["son_state"] = state
        self.state["recent_states"] = recent
        self.state["burst_count"] = burst_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('son_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('son_state', "quiet") if 'son_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "son_drive": round(new_drive, 4),
            "avp_pituitary": round(avp, 4),
            "oxytocin_pituitary": round(ot, 4),
            "dendritic_peptide_release": round(dendritic, 4),
            "phasic_burst_signal": round(burst, 4),
            "son_state": state,
        }

    def _osmotic_load(self) -> float:
        """Cumulative osmotic-release index (Bourque 2008)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("burst_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("son_drive", 0.0),
            "avp": self.state.get("avp_pituitary", 0.0),
            "ot": self.state.get("oxytocin_pituitary", 0.0),
            "state": self.state.get("son_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('son_state', "quiet") if 'son_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('son_drive', 0.0)) if 'son_drive' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('son_drive', 0.0) if 'son_drive' else 0.0,
            "state": self.state.get('son_state', "quiet") if 'son_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

