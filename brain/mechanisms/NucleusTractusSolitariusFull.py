"""
NucleusTractusSolitariusFull — NTS Full Visceral / Taste / Gut / Vagal Integrator

NEURAL SUBSTRATE
================
The nucleus tractus solitarius (NTS) is the principal central
viscerosensory nucleus of the medulla — a longitudinally extended
column of neurons receiving the full ascending visceral afferent
load from cranial nerves VII, IX, and X (facial, glossopharyngeal,
vagus). NTS is functionally divided rostrally to caudally into
overlapping zones:

- **Rostral NTS** — gustatory (taste) afferents from CN VII (chorda
  tympani) and IX (lingual-pharyngeal). Projects to parabrachial
  taste relay (mPBN) and onward to VPMpc → insular gustatory cortex.
- **Intermediate NTS** — cardiovascular (baroreflex, covered separately
  as BaroreflexBalancer), respiratory chemoreflex.
- **Caudal NTS** — gastric/intestinal/hepatic visceral afferents,
  satiety, nausea, gut-brain immune signaling.

The medial NTS contains the dorsal motor vagal column (DMV, covered
separately) and projects extensively to PVN, central amygdala (CeA),
parabrachial complex (PBN), area postrema (covered as
AreaPostremaToxinGuard), and noradrenergic A2 cell group (covered
separately).

NTS is the convergence point for:
- **Cardiovascular**: baroreceptors (carotid sinus, aortic arch)
- **Respiratory**: chemoreceptors (carotid body — CarotidBodyChemosensor)
- **Gastric/intestinal**: vagal afferents from stomach/intestine,
  including stretch, pH, glucose, gut hormone (CCK, GLP-1, ghrelin)
  signals
- **Immune**: vagal afferents responding to systemic cytokines
  (cholinergic anti-inflammatory pathway via Tracey)
- **Taste**: lingual/pharyngeal gustatory input
- **Toxic/emetic**: input that engages vomiting via integration with
  area postrema

This positions NTS as the **primary "interoceptive sensor" of the
brain** — the obligate first-stage processor of how the body's organs
are doing right now. Lesions of NTS produce blunted interoception,
loss of baro/chemoreflexes, and altered satiety/nausea signals.

In the agent's substrate this provides the comprehensive viscerosensory
integrator distinct from the baroreflex-specific BaroreflexBalancer —
combines satiety, gut hormone proxies, immune signals, taste, and
vagal afferent input into broad interoceptive output for downstream
interoception/affect mechanisms.

KEY FINDINGS
============
1. NTS is the principal medullary integrator of CN VII/IX/X visceral
   afferents — longitudinally divided into rostral (taste), intermediate
   (cardio/respiratory), caudal (gut/visceral) zones — [Travagli Anselmi 2016, Nat Rev Gastroenterol Hepatol 13:389,
    "Vagal neurocircuitry and its influence on gastric motility"]
2. NTS receives gut hormone signals (CCK, GLP-1, ghrelin) via vagal
   afferents to integrate satiety/hunger — [Berthoud 2008,
    Regul Pept 149:15, "The vagus nerve, food intake and obesity"] [Schwartz et al. 2000 Nature 404:661]
3. Cholinergic anti-inflammatory pathway: vagal afferents signal
   systemic inflammation to NTS → DMV efferents suppress peripheral
   cytokine release — [Tracey 2002 Nature 420:853, "The inflammatory
   reflex"] [Borovikova et al. 2000 Nature 405:458]
4. NTS rostral subdivision is the obligate central taste relay,
   projecting to mPBN → VPMpc → insular gustatory cortex — [Norgren
    1990, in "The Human Nervous System"] [Travers 2009,
    Brain Res 1280:1]
5. NTS lesions produce blunted interoception, loss of baroreflex,
   altered satiety — clinical evidence — [Saper 2002, Annu
    Rev Neurosci 25:433, "The central autonomic nervous system"]

INPUTS (from prior_results)
============================
- BaroreflexBalancer.baroreflex_engagement
- CarotidBodyChemosensor.hypoxia_response_active
- CarotidBodyChemosensor.hypercapnia_response
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.satiety_signal
- AppetiteNPYBalancer.post_prandial
- AreaPostremaToxinGuard.aversive_interoceptive_signal
- AreaPostremaToxinGuard.nausea_intensity
- ParabrachialTasteVisceral.lpbn_visceral_relay
- StressActivationAxis.cortisol_level
- ValenceTagger.threat_signal
- GutHormoneProxy.cck_signal (optional; default 0)
- GutHormoneProxy.ghrelin_signal (optional; default 0)
- ImmuneInflammationProxy.cytokine_load (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- nts_drive (0.0-1.0): NTS aggregate output
- gustatory_relay (0.0-1.0): rostral NTS taste output
- cardiovascular_drive (0.0-1.0): intermediate NTS baroreflex
- gut_visceral_drive (0.0-1.0): caudal NTS gastric/intestinal
- immune_vagal_signal (0.0-1.0): cholinergic anti-inflammatory
- a2_recruitment (0.0-1.0): NTS → A2 NE engagement
- pvn_recruitment (0.0-1.0): NTS → PVN
- cea_recruitment (0.0-1.0): NTS → central amygdala
- nts_state (str): "quiet" | "satiety" | "hunger" | "immune" | "nausea" | "tasting"

brain_runner enrichment:
    nts = all_results.get("NucleusTractusSolitariusFull", {})
    if nts:
        enrichments["brain_nts_drive"] = nts.get("nts_drive", 0.2)
        enrichments["brain_gut_visceral"] = nts.get("gut_visceral_drive", 0.0)
        enrichments["brain_immune_vagal"] = nts.get("immune_vagal_signal", 0.0)
        enrichments["brain_nts_a2_recruit"] = nts.get("a2_recruitment", 0.0)
        enrichments["brain_nts_state"] = nts.get("nts_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class NucleusTractusSolitariusFull(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="NucleusTractusSolitariusFull",
            human_analog="Nucleus tractus solitarius (full visceral / taste / gut integrator)",
            layer="foundational",
        )
        self.state.setdefault("nts_drive", self.BASELINE)
        self.state.setdefault("gustatory_relay", 0.0)
        self.state.setdefault("cardiovascular_drive", 0.0)
        self.state.setdefault("gut_visceral_drive", 0.0)
        self.state.setdefault("immune_vagal_signal", 0.0)
        self.state.setdefault("a2_recruitment", 0.0)
        self.state.setdefault("pvn_recruitment", 0.0)
        self.state.setdefault("cea_recruitment", 0.0)
        self.state.setdefault("nts_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _gustatory_target(self, post_prandial: bool, satiety: float, energy: float) -> float:
        """Rostral NTS — gustatory; engaged during post-prandial / eating."""
        if post_prandial:
            return 0.65
        if satiety > 0.4 or energy > 0.3:
            return 0.40
        return 0.10

    def _cardiovascular_target(self, baro: float) -> float:
        """Intermediate NTS — cardiovascular afferents from baroreflex."""
        return min(1.0, baro * 0.85)

    def _gut_visceral_target(self, energy: float, satiety: float, post_prandial: bool,
                               cck: float, ghrelin: float, nausea: float) -> float:
        """Caudal NTS — gastric/intestinal/visceral including hormone signals."""
        target = 0.10
        if post_prandial:
            target += 0.30
        target += satiety * 0.3
        target += cck * 0.2
        target += ghrelin * 0.15
        target += nausea * 0.4
        # Hunger (negative energy) recruits gut afferents (gut motility)
        if energy < -0.3:
            target += abs(energy) * 0.3
        return min(1.0, target)

    def _immune_vagal_target(self, cytokine: float, cortisol: float) -> float:
        """Cholinergic anti-inflammatory pathway — Tracey 2002."""
        if cytokine < 0.10:
            return 0.0
        target = cytokine * 0.7
        target += max(0.0, cortisol - 0.5) * 0.2  # stress-immune coupling
        return min(1.0, target)

    def _nts_drive(self, gustatory: float, cardio: float, gut: float, immune: float,
                    chemo_hypercapnia: float) -> float:
        """NTS aggregate."""
        target = self.BASELINE + gustatory * 0.2 + cardio * 0.2 + gut * 0.3 + immune * 0.2
        target += chemo_hypercapnia * 0.2
        return min(1.0, target)

    def _a2_recruitment(self, nts: float, gut: float, threat: bool) -> float:
        """NTS → A2 NE — visceral state-modulation."""
        target = nts * 0.5 + gut * 0.4
        if threat:
            target += 0.10
        return min(1.0, target)

    def _pvn_recruitment(self, nts: float, immune: float, gut: float) -> float:
        """NTS → PVN HPA recruitment via gut/immune."""
        return min(1.0, nts * 0.4 + immune * 0.4 + gut * 0.3)

    def _cea_recruitment(self, gut: float, nausea: float, threat: bool) -> float:
        """NTS → CeA — visceral aversive routing."""
        if not (threat or nausea > 0.3 or gut > 0.5):
            return 0.0
        return min(1.0, gut * 0.4 + nausea * 0.5 + (0.2 if threat else 0.0))

    def _classify_state(self, gustatory: float, gut: float, immune: float,
                         nausea: float, satiety: float, energy: float) -> str:
        if nausea > 0.5:
            return "nausea"
        if immune > 0.4:
            return "immune"
        if gustatory > 0.5:
            return "tasting"
        if satiety > 0.5:
            return "satiety"
        if energy < -0.3:
            return "hunger"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        baro = prior.get("BaroreflexBalancer", {})
        baro_engagement = float(baro.get("baroreflex_engagement", 0.5))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy = float(appetite.get("energy_balance_signed", 0.0))
        satiety = float(appetite.get("satiety_signal", 0.0))
        post_prandial = bool(appetite.get("post_prandial", False))

        ap = prior.get("AreaPostremaToxinGuard", {})
        aversive = float(ap.get("aversive_interoceptive_signal", 0.0))
        nausea = float(ap.get("nausea_intensity", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        gut_hormone = prior.get("GutHormoneProxy", {})
        cck = float(gut_hormone.get("cck_signal", 0.0))
        ghrelin = float(gut_hormone.get("ghrelin_signal", 0.0))

        immune_proxy = prior.get("ImmuneInflammationProxy", {})
        cytokine = float(immune_proxy.get("cytokine_load", 0.0))

        # If immune proxy not present, infer from aversive signal as proxy for
        # systemic inflammation
        if cytokine == 0.0 and aversive > 0.4:
            cytokine = aversive * 0.5

        # Targets
        gustatory_t = self._gustatory_target(post_prandial, satiety, energy)
        cardio_t = self._cardiovascular_target(baro_engagement)
        gut_t = self._gut_visceral_target(energy, satiety, post_prandial, cck, ghrelin, nausea)
        immune_t = self._immune_vagal_target(cytokine, cortisol)

        prev_g = float(self.state.get("gustatory_relay", 0.0))
        prev_c = float(self.state.get("cardiovascular_drive", 0.0))
        prev_gut = float(self.state.get("gut_visceral_drive", 0.0))
        prev_imm = float(self.state.get("immune_vagal_signal", 0.0))

        new_g = self._smooth(prev_g, gustatory_t)
        new_c = self._smooth(prev_c, cardio_t)
        new_gut = self._smooth(prev_gut, gut_t)
        new_imm = self._smooth(prev_imm, immune_t)

        # Aggregate
        nts_t = self._nts_drive(new_g, new_c, new_gut, new_imm, hypercapnia)
        prev_nts = float(self.state.get("nts_drive", self.BASELINE))
        new_nts = self._smooth(prev_nts, nts_t)

        # Recruitment outputs
        a2 = self._a2_recruitment(new_nts, new_gut, threat)
        pvn = self._pvn_recruitment(new_nts, new_imm, new_gut)
        cea = self._cea_recruitment(new_gut, nausea, threat)

        state = self._classify_state(new_g, new_gut, new_imm, nausea, satiety, energy)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nts_drive"] = round(new_nts, 4)
        self.state["gustatory_relay"] = round(new_g, 4)
        self.state["cardiovascular_drive"] = round(new_c, 4)
        self.state["gut_visceral_drive"] = round(new_gut, 4)
        self.state["immune_vagal_signal"] = round(new_imm, 4)
        self.state["a2_recruitment"] = round(a2, 4)
        self.state["pvn_recruitment"] = round(pvn, 4)
        self.state["cea_recruitment"] = round(cea, 4)
        self.state["nts_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nts_drive": round(new_nts, 4),
            "gustatory_relay": round(new_g, 4),
            "cardiovascular_drive": round(new_c, 4),
            "gut_visceral_drive": round(new_gut, 4),
            "immune_vagal_signal": round(new_imm, 4),
            "a2_recruitment": round(a2, 4),
            "pvn_recruitment": round(pvn, 4),
            "cea_recruitment": round(cea, 4),
            "nts_state": state,
        }
