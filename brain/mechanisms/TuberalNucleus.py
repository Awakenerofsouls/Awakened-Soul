"""
TuberalNucleus — TuN — Hypothalamic Predator-Defense / Aggression

NEURAL SUBSTRATE
================
The tuberal nuclei occupy the tuberal/middle hypothalamic region between
the anterior preoptic and the mammillary regions. In the rodent
hypothalamus, the tuberal-region nuclei include the dorsomedial,
ventromedial, arcuate and tuberomammillary nuclei; the term "tuberal
nucleus" specifically refers to a small population dorsolateral to the
ventromedial nucleus (the "lateral tuberal nucleus" in primates).

Anatomical and behavioral evidence places tuberal-region neurons within
the broader hypothalamic predator-defense and aggression network. The
adjacent ventral premammillary nucleus (PMv) houses dopamine-transporter-
expressing (PMvDAT) neurons whose activation is sufficient to trigger
attack and establish social hierarchy (Stagkourakis 2018). The tuberal
region is reciprocally connected with VMHvl/AH (aggression locus) and
projects to PAG and supramammillary nuclei (aggression reward).

This module implements the tuberal-region predator-defense / aggression
node that integrates pheromonal threat, conspecific cues and limbic
threat assessment to drive species-typical defense and attack execution.

KEY FINDINGS
============
1. PMvDAT neural network for intermale aggression establishes social
   hierarchy; brief manipulation switches dominance for weeks.
   [Stagkourakis S 2018, Nat Neurosci 21:834, doi:10.1038/s41593-018-0153-x]
2. VMHvl-projecting Vglut1+ neurons in posterior amygdala gate
   territorial aggression through the tuberal/VMHvl region.
   [Zha X 2020, Cell Rep 31:107517, doi:10.1016/j.celrep.2020.03.081]
3. Hypothalamic Esr1+ neurons scale aggression from investigation
   through attack in the VMHvl/tuberal region.
   [Lee H 2014, Nature 509:627, doi:10.1038/nature13169]
4. Optogenetic functional identification of an aggression locus in
   the mouse hypothalamus.
   [Lin D 2011, Nature 470:221, doi:10.1038/nature09736]
5. Ethology and pharmacology of hypothalamic aggression in rat:
   tuberal/VMHvl-region stimulation evokes attack.
   [Kruk M 1991, Neurosci Biobehav Rev 15:527, doi:10.1016/s0149-7634(05)80144-7]
6. Decoding hypothalamic activity during aggression reveals tuning
   to male conspecifics.
   [Falkner A 2014, J Neurosci 34:5971, doi:10.1523/JNEUROSCI.5109-13.2014]

INPUTS
======
- AnteriorHypothalamus.ah_drive (aggression locus coupling)
- VentromedialHypothalamus.vmh_drive (VMHvl/dm)
- MedialAmygdalaPosterior.med_amyg_drive (pheromone)
- LateralHabenula.lhb_drive (negative valence)
- HypothalamicSupramammillary.sum_drive (aggression-reward coupling)

OUTPUTS
=======
- tun_drive (0-1)
- predator_defense_signal (0-1)
- attack_execution_signal (0-1)
- pmv_dat_proxy (0-1) — PMvDAT-like population proxy
- pag_defense_signal (0-1) — to PAG (Bandler 2000)
- social_hierarchy_signal (0-1) — dominance switch index
- tun_state (str): "predator_defense" | "intermale_attack" |
                    "submission" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class TuberalNucleus(BrainMechanism):
    """TuN — tuberal-region predator-defense / aggression."""

    BASELINE = 0.08
    SMOOTH = 0.20
    DEFENSE_THRESHOLD = 0.40
    ATTACK_THRESHOLD = 0.55
    DOMINANCE_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="TuberalNucleus",
            human_analog="Tuberal nucleus (predator defense, aggression)",
            layer="subcortical",
        )
        self.state.setdefault("tun_drive", self.BASELINE)
        self.state.setdefault("predator_defense_signal", 0.0)
        self.state.setdefault("attack_execution_signal", 0.0)
        self.state.setdefault("pmv_dat_proxy", 0.0)
        self.state.setdefault("pag_defense_signal", 0.0)
        self.state.setdefault("social_hierarchy_signal", 0.0)
        self.state.setdefault("tun_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("attack_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ah: float, vmh: float, mea: float,
                       lhb: float, sum_drive: float) -> float:
        """Composite tuberal drive (Stagkourakis 2018, Lee 2014)."""
        target = (self.BASELINE
                  + ah * 0.30
                  + vmh * 0.25
                  + mea * 0.25
                  + lhb * 0.10
                  + sum_drive * 0.15)
        return min(1.0, target)

    def _predator_defense(self, drive: float, mea: float,
                           lhb: float) -> float:
        """Predator-defense response (Zha 2020)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.45 + mea * 0.30 + lhb * 0.30)

    def _attack(self, drive: float, ah: float, vmh: float) -> float:
        """Intermale attack execution (Lin 2011, Lee 2014)."""
        if drive < 0.25:
            return 0.0
        return min(1.0, drive * 0.40 + ah * 0.35 + vmh * 0.30)

    def _pmv_dat(self, drive: float, attack: float,
                  sum_drive: float) -> float:
        """PMvDAT-like aggression-organizer proxy (Stagkourakis 2018)."""
        return min(1.0, drive * 0.40 + attack * 0.40 + sum_drive * 0.25)

    def _pag_defense(self, drive: float, defense: float,
                      attack: float) -> float:
        """PAG defense column (Bandler 2000)."""
        return min(1.0, drive * 0.30 + defense * 0.45 + attack * 0.35)

    def _hierarchy(self, attack: float, ah: float) -> float:
        """Social hierarchy/dominance index (Stagkourakis 2018)."""
        return min(1.0, attack * 0.55 + ah * 0.40)

    def _classify_state(self, drive: float, defense: float,
                         attack: float, hierarchy: float) -> str:
        if drive < 0.18:
            return "quiet"
        if attack > self.ATTACK_THRESHOLD:
            return "intermale_attack"
        if defense > self.DEFENSE_THRESHOLD:
            return "predator_defense"
        if hierarchy < 0.10 and drive > 0.20:
            return "submission"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ah_data = prior.get("AnteriorHypothalamus", {})
        ah = float(ah_data.get("ah_drive",
                          ah_data.get("aggression_signal", 0.0)))

        vmh_data = prior.get("VentromedialHypothalamus", {})
        vmh = float(vmh_data.get("vmh_drive",
                          vmh_data.get("vmhvl_drive", 0.0)))

        mea_data = prior.get("MedialAmygdalaPosterior", {})
        if not mea_data:
            mea_data = prior.get("AmygdaloidMedialAnterior", {})
        mea = float(mea_data.get("med_amyg_drive",
                          mea_data.get("social_signal", 0.0)))

        lhb_data = prior.get("LateralHabenula", {})
        lhb = float(lhb_data.get("lhb_drive", 0.0))

        sum_data = prior.get("HypothalamicSupramammillary", {})
        sum_drive = float(sum_data.get("sum_drive",
                                sum_data.get("rem_theta", 0.0)))

        target = self._drive_target(ah, vmh, mea, lhb, sum_drive)
        prev_drive = float(self.state.get("tun_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        defense = self._predator_defense(new_drive, mea, lhb)
        attack = self._attack(new_drive, ah, vmh)
        pmv = self._pmv_dat(new_drive, attack, sum_drive)
        pag = self._pag_defense(new_drive, defense, attack)
        hierarchy = self._hierarchy(attack, ah)

        state = self._classify_state(new_drive, defense, attack, hierarchy)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        ac = int(self.state.get("attack_count", 0))
        if state == "intermale_attack":
            ac += 1

        self.state["tun_drive"] = round(new_drive, 4)
        self.state["predator_defense_signal"] = round(defense, 4)
        self.state["attack_execution_signal"] = round(attack, 4)
        self.state["pmv_dat_proxy"] = round(pmv, 4)
        self.state["pag_defense_signal"] = round(pag, 4)
        self.state["social_hierarchy_signal"] = round(hierarchy, 4)
        self.state["tun_state"] = state
        self.state["recent_states"] = recent
        self.state["attack_count"] = ac
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('tun_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('tun_state', "quiet") if 'tun_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "tun_drive": round(new_drive, 4),
            "predator_defense_signal": round(defense, 4),
            "attack_execution_signal": round(attack, 4),
            "pmv_dat_proxy": round(pmv, 4),
            "pag_defense_signal": round(pag, 4),
            "social_hierarchy_signal": round(hierarchy, 4),
            "tun_state": state,
        }

    def _aggression_pressure(self) -> float:
        """Cumulative attack-engagement (Stagkourakis 2018)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("attack_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("tun_drive", 0.0),
            "defense": self.state.get("predator_defense_signal", 0.0),
            "attack": self.state.get("attack_execution_signal", 0.0),
            "state": self.state.get("tun_state", "quiet"),
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
            return self.state.get('tun_state', "quiet") if 'tun_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('tun_drive', 0.0)) if 'tun_drive' else 0.0
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
            "drive": self.state.get('tun_drive', 0.0) if 'tun_drive' else 0.0,
            "state": self.state.get('tun_state', "quiet") if 'tun_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

