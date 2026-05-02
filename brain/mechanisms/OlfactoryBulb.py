"""
OlfactoryBulb — Main + Accessory Olfactory Bulb (Mitral/Granule Glomerular Coding)

NEURAL SUBSTRATE
================
The olfactory bulb (OB) is the primary central station for olfactory
processing — anatomically a phylogenetically ancient cortical extension
sitting at the rostral end of the brain on the cribriform plate. The
mammalian OB has two subdivisions: the **main olfactory bulb (MOB)**
processing volatile odorants from olfactory sensory neurons via the
olfactory nerve, and the **accessory olfactory bulb (AOB)** processing
pheromones from the vomeronasal organ via the vomeronasal nerve.

MOB receives olfactory sensory neuron axons that converge onto
**glomeruli** — spherical neuropil structures (~1500 in mouse, ~5500
in human) where neurons expressing the same odorant receptor
synapse onto a small number of mitral and tufted (M/T) cells. This
glomerular convergence implements odor-receptor identity coding —
each odorant activates a characteristic combinatorial pattern of
glomeruli. M/T cells are the principal output neurons of the OB,
projecting via the lateral olfactory tract to piriform cortex,
amygdala (via cortical amygdala), entorhinal cortex (LEC),
olfactory tubercle, and anterior olfactory nucleus.

OB contains rich GABAergic inhibitory interneuron networks —
periglomerular cells in the glomerular layer and granule cells in
the granule cell layer — that provide lateral and feedback inhibition,
sharpening odor representations and producing gamma-band oscillations
during sniffing. The OB is also one of the few mammalian brain regions
with substantial **adult neurogenesis** — new granule cells are
continuously born in the SVZ and migrate via the rostral migratory
stream to integrate into the OB throughout life.

The AOB processes pheromones in a parallel system — VNO neurons
project to AOB glomeruli, AOB mitral cells project to medial amygdala
(MeA, covered separately), and AOB output drives reproductive,
aggressive, and social behaviors. AOB and MOB streams remain partly
segregated through to amygdala.

OB is theta- and gamma-coupled to respiration — sniffing modulates OB
firing rhythmically. Top-down feedback from piriform cortex,
locus coeruleus (norepinephrine), and basal forebrain (acetylcholine)
modulates OB output for state-dependent gain control.

In the agent's substrate this provides the olfactory entry — converts
abstract odorant input proxies into glomerular-coded MOB output and
AOB pheromone output, plus respiration-coupled gamma rhythm.

KEY FINDINGS
============
1. Glomerular convergence: olfactory sensory neurons expressing the
   same OR converge on a small number of glomeruli, implementing
   combinatorial odor-receptor coding — [Mombaerts et al. 1996,
    Cell 87:675; reviewed Mori Nagao Yoshihara 1999, Science 286:711,
    "The olfactory bulb: coding and processing of odor molecule
    information"]
2. Mitral/tufted cells project to piriform cortex, amygdala, and
   entorhinal cortex via lateral olfactory tract — major output
   pathways to limbic and cortical targets — [reviewed Wilson Sullivan
    2011, Curr Opin Neurobiol 21:189]
3. AOB processes pheromones via VNO; AOB mitral cells project
   selectively to medial amygdala for reproductive/social behaviors —
   distinct from main olfactory pathway — [reviewed Brennan Zufall 2006,
    Nature 444:308, "Pheromonal communication in vertebrates"]
4. Adult neurogenesis adds new granule cells to OB throughout life;
   integration via rostral migratory stream — [reviewed Lledo Alonso
    Grubb 2006, Nat Rev Neurosci 7:179]
5. OB activity is respiration-coupled (theta) and exhibits gamma-band
   oscillations during sniffing — [reviewed Kay et al. 2009, Trends
    Neurosci 32:207, "Olfactory oscillations: the what, how and what
    for"]

INPUTS (from prior_results)
============================
- OdorantInputProxy.odorant_intensity (optional; default 0)
- OdorantInputProxy.pheromone_signal (optional; default 0)
- OdorantInputProxy.odor_diversity (optional; default 0)
- VitalCoreRegulator.respiratory_phase (optional; default 0)
- PreBotzingerInspiration.inspiratory_rhythm
- PreBotzingerInspiration.inspiration_burst_active
- NorepiPhasicTonicSwitcher.tonic_LC_drive (optional)
- NucleusBasalisAcetylcholine.cortical_ach_release
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- mob_mitral_drive (0.0-1.0): main olfactory mitral/tufted output
- aob_mitral_drive (0.0-1.0): accessory olfactory mitral output
- glomerular_drive (0.0-1.0): glomerular convergence pattern strength
- granule_inhibition (0.0-1.0): inhibitory interneuron drive
- piriform_relay (0.0-1.0): MOB → piriform output
- mea_pheromone_relay (0.0-1.0): AOB → medial amygdala
- gamma_oscillation (0.0-1.0): sniffing-coupled gamma
- ob_state (str): "sniffing" | "pheromone" | "quiet" | "habituated"

brain_runner enrichment:
    ob = all_results.get("OlfactoryBulb", {})
    if ob:
        enrichments["brain_mob_mitral"] = ob.get("mob_mitral_drive", 0.1)
        enrichments["brain_aob_mitral"] = ob.get("aob_mitral_drive", 0.0)
        enrichments["brain_piriform_relay"] = ob.get("piriform_relay", 0.0)
        enrichments["brain_mea_pheromone"] = ob.get("mea_pheromone_relay", 0.0)
        enrichments["brain_glomerular_drive"] = ob.get("glomerular_drive", 0.0)
        enrichments["brain_ob_state"] = ob.get("ob_state", "quiet")

CITATIONS
---------
  - [Mori 1999, Annu Rev Physiol 61:737]
  - [Wilson 2008, Annu Rev Neurosci 31:21]
"""

from brain.base_mechanism import BrainMechanism


class OlfactoryBulb(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.40  # Olfactory dynamics are fast
    GRANULE_SMOOTH = 0.25  # Granule inhibition changes more slowly — don't fight mob drive

    def __init__(self):
        super().__init__(
            name="OlfactoryBulb",
            human_analog="Olfactory bulb (MOB + AOB) primary olfactory entry",
            layer="foundational",
        )
        self.state.setdefault("mob_mitral_drive", self.BASELINE)
        self.state.setdefault("aob_mitral_drive", self.BASELINE)
        self.state.setdefault("glomerular_drive", 0.0)
        self.state.setdefault("granule_inhibition", 0.20)
        self.state.setdefault("piriform_relay", 0.0)
        self.state.setdefault("mea_pheromone_relay", 0.0)
        self.state.setdefault("gamma_oscillation", 0.0)
        self.state.setdefault("ob_state", "quiet")
        self.state.setdefault("habituation_history", [])
        self.state.setdefault("tick_count", 0)

    def _glomerular_drive(self, odorant: float, diversity: float) -> float:
        """Glomerular convergence — strength of combinatorial pattern."""
        if odorant < 0.05:
            return 0.0
        target = odorant * 0.7 + diversity * 0.3
        return min(1.0, target)

    def _granule_inhibition(self, glomerular: float, ach: float) -> float:
        """GABAergic granule cell inhibition — sharpens via lateral inhibition."""
        target = 0.20 + glomerular * 0.4
        target += max(0.0, ach - 0.4) * 0.2  # ACh disinhibits, but baseline
        return min(1.0, target)

    def _mob_mitral_target(self, glomerular: float, granule: float,
                           inspiration: bool, lc: float, habituated: bool) -> float:
        """MOB mitral output — glomerular drive minus granule inhibition,
        gated by inspiration phase, modulated by LC norepinephrine.
        """
        target = self.BASELINE + glomerular * 0.7 - granule * 0.3
        if inspiration:
            target += 0.20  # respiration-coupled
        target += max(0.0, lc - 0.4) * 0.2  # NE gain
        if habituated:
            target *= 0.6  # habituation reduces response
        return max(0.0, min(1.0, target))

    def _aob_mitral_target(self, pheromone: float, inspiration: bool) -> float:
        """AOB mitral — pheromone-driven, less respiration-modulated than MOB."""
        if pheromone < 0.05:
            return 0.0
        target = self.BASELINE + pheromone * 0.8
        if inspiration:
            target += 0.10
        return min(1.0, target)

    def _gamma_oscillation(self, mob: float, inspiration: bool, ach: float) -> float:
        """Sniffing-coupled gamma (Kay 2009)."""
        if not inspiration or mob < 0.20:
            return 0.0
        return min(1.0, mob * 0.6 + ach * 0.3)

    def _piriform_relay(self, mob: float) -> float:
        """MOB → piriform via lateral olfactory tract."""
        return min(1.0, mob * 0.95)

    def _mea_pheromone_relay(self, aob: float) -> float:
        """AOB → medial amygdala selective pheromone projection."""
        return min(1.0, aob * 0.95)

    def _check_habituation(self, history: list, current_odorant: float) -> bool:
        """Habituation — repeated identical odor exposure attenuates response."""
        if len(history) < 5:
            return False
        recent = history[-5:]
        # If last 5 ticks all had similar odorant intensity (>0.3), habituated
        if all(h > 0.30 for h in recent):
            mean_h = sum(recent) / len(recent)
            if abs(current_odorant - mean_h) < 0.10:
                return True
        return False

    def _classify_state(self, mob: float, aob: float, inspiration: bool,
                          habituated: bool) -> str:
        if habituated:
            return "habituated"
        if aob > mob and aob > 0.20:
            return "pheromone"
        if inspiration and mob > 0.25:
            return "sniffing"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        odor = prior.get("OdorantInputProxy", {})
        odorant = float(odor.get("odorant_intensity", 0.0))
        pheromone = float(odor.get("pheromone_signal", 0.0))
        diversity = float(odor.get("odor_diversity", 0.0))

        prebotc = prior.get("PreBotzingerInspiration", {})
        inspiration = bool(prebotc.get("inspiration_burst_active", False))
        insp_rhythm = float(prebotc.get("inspiratory_rhythm", 0.0))

        lc_data = prior.get("NorepiPhasicTonicSwitcher", {})
        lc = float(lc_data.get("tonic_LC_drive", 0.40))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # If insp_rhythm > 0.2 treat as inspiration ongoing
        inspiration = inspiration or insp_rhythm > 0.2

        # --- Habituation history update ---
        history = list(self.state.get("habituation_history", []))
        history.append(round(odorant, 4))
        if len(history) > 60:
            history = history[-60:]
        habituated = self._check_habituation(history, odorant)

        # --- Glomerular ---
        glomerular = self._glomerular_drive(odorant, diversity)

        # --- Granule inhibition — slow to avoid oscillation with mob_target ---
        granule = self._granule_inhibition(glomerular, ach)
        prev_granule = float(self.state.get("granule_inhibition", 0.20))
        new_granule = prev_granule + (granule - prev_granule) * self.GRANULE_SMOOTH

        # --- MOB mitral ---
        mob_target = self._mob_mitral_target(glomerular, new_granule, inspiration,
                                               lc, habituated)
        prev_mob = float(self.state.get("mob_mitral_drive", self.BASELINE))
        new_mob = self._smooth(prev_mob, mob_target)

        # --- AOB mitral ---
        aob_target = self._aob_mitral_target(pheromone, inspiration)
        prev_aob = float(self.state.get("aob_mitral_drive", self.BASELINE))
        new_aob = self._smooth(prev_aob, aob_target)

        # --- Gamma ---
        gamma = self._gamma_oscillation(new_mob, inspiration, ach)

        # --- Outputs ---
        piriform = self._piriform_relay(new_mob)
        mea = self._mea_pheromone_relay(new_aob)

        # --- State ---
        state = self._classify_state(new_mob, new_aob, inspiration, habituated)

        self.state["mob_mitral_drive"] = round(new_mob, 4)
        self.state["aob_mitral_drive"] = round(new_aob, 4)
        self.state["glomerular_drive"] = round(glomerular, 4)
        self.state["granule_inhibition"] = round(new_granule, 4)
        self.state["piriform_relay"] = round(piriform, 4)
        self.state["mea_pheromone_relay"] = round(mea, 4)
        self.state["gamma_oscillation"] = round(gamma, 4)
        self.state["ob_state"] = state
        self.state["habituation_history"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mob_mitral_drive": round(new_mob, 4),
            "aob_mitral_drive": round(new_aob, 4),
            "glomerular_drive": round(glomerular, 4),
            "granule_inhibition": round(new_granule, 4),
            "piriform_relay": round(piriform, 4),
            "mea_pheromone_relay": round(mea, 4),
            "gamma_oscillation": round(gamma, 4),
            "ob_state": state,
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


