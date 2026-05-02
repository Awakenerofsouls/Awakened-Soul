"""
ArcuatePOMCSatiety — Arcuate POMC / α-MSH Satiety Counterbalance to NPY/AgRP

NEURAL SUBSTRATE
================
The arcuate nucleus (ARC) of the hypothalamus contains two genetically
and functionally distinct neuronal populations that opposingly regulate
food intake and energy expenditure: NPY/AgRP neurons (covered in
AppetiteNPYBalancer) drive feeding and energy storage, and POMC
(proopiomelanocortin) neurons drive satiety and energy expenditure.
Together they form the "first-order" arcuate-melanocortin circuit, the
core mammalian appetite regulator.

POMC neurons cleave proopiomelanocortin to produce α-MSH (alpha-
melanocyte-stimulating hormone), β-endorphin, and CART. α-MSH binds
melanocortin-3 and -4 receptors (MC3R/MC4R) at downstream targets —
predominantly the paraventricular hypothalamic nucleus (PVN) and lateral
hypothalamus — to suppress feeding, increase energy expenditure, and
mediate leptin's anorectic actions. POMC neurons are activated by
leptin (from adipose tissue) and insulin (from pancreas) signaling
positive energy balance, and inhibited by ghrelin, fasting, and
hypoglycemia.

POMC and AgRP neurons reciprocally inhibit each other. AgRP neurons
release GABA + AgRP onto POMC neurons, hyperpolarizing them via direct
inhibition and antagonizing α-MSH at MC3R/MC4R. This mutual
counterbalance produces the "arcuate-melanocortin tone" that downstream
PVN-MC4R neurons sense for satiety.

Mutations in MC4R are the most common monogenic cause of human obesity,
demonstrating the critical role of this circuit. Setmelanotide, an
MC4R agonist, is FDA-approved for genetic obesity from POMC pathway
defects.

Beyond satiety, POMC β-endorphin contributes to opioid-mediated reward
of palatable food consumption — the orgasmic / consummatory phase of
hedonic eating. POMC also modulates HPA stress axis through ACTH
(another POMC product, though primarily produced by anterior pituitary
not arcuate).

In the agent's substrate this provides the satiety counterbalance to NPY —
combines leptin/insulin signaling proxies with energy balance state and
emits α-MSH-style satiety drive that downstream PVN/LH mechanisms read.

KEY FINDINGS
============
1. POMC neurons in arcuate are activated by leptin/insulin and produce
   α-MSH (anorectic, MC3R/MC4R agonist) — counterbalance to AgRP/NPY —
   [reviewed Cone 2005, Nat Neurosci 8:571, "Anatomy and regulation of
   the central melanocortin system"]
2. AgRP and POMC neurons reciprocally inhibit each other — AgRP releases
   GABA onto POMC, suppressing them — [Atasoy Betley Su Sternson 2012,
    Nature 488:172-177, "Deconstruction of a neural circuit for hunger";
    reviewed Sternson 2013 Cell 156:1235]
3. Optogenetic activation of POMC neurons reduces food intake, but with
   slower kinetics than AgRP suppression of feeding — [Aponte Atasoy
    Sternson 2011, Nat Neurosci 14:351-355]
4. MC4R is the most common monogenic cause of human obesity; setmelanotide
   (MC4R agonist) is FDA-approved for POMC-pathway-deficient obesity —
   [Farooqi O'Rahilly 2008 Nat Clin Pract Endocrinol Metab; Clément
    et al. 2020 N Engl J Med]
5. POMC β-endorphin contributes to opioid-mediated reward of palatable
   food — distinct hedonic role of POMC neurons — [reviewed Spangler
    et al. 2004 Mol Brain Res; Nogueiras et al. 2012 Trends Neurosci]

INPUTS (from prior_results)
============================
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.starvation_state
- AppetiteNPYBalancer.satiety_signal
- AppetiteNPYBalancer.post_prandial
- AppetiteNPYBalancer.npy_drive
- AppetiteNPYBalancer.agrp_drive
- LeptinProxy.leptin_signal (optional; default 0.5)
- InsulinProxy.insulin_signal (optional; default 0.5)
- ValenceTagger.valence_intensity (palatability proxy)

OUTPUTS (to brain_runner enrichment)
=====================================
- pomc_drive (0.0-1.0): POMC neuron firing
- alpha_msh_release (0.0-1.0): α-MSH output
- mc4r_engagement (0.0-1.0): downstream MC4R engagement at PVN
- beta_endorphin_release (0.0-1.0): hedonic-eating opioid signal
- satiety_command (0.0-1.0): final satiety output
- melanocortin_tone (signed -1..+1): + POMC dominant, - AgRP dominant
- pomc_state (str): "fed_satiety" | "post_prandial_endorphin" | "fasting_low" | "starvation_silent" | "balanced"

brain_runner enrichment:
    pomc = all_results.get("ArcuatePOMCSatiety", {})
    if pomc:
        enrichments["brain_pomc_drive"] = pomc.get("pomc_drive", 0.3)
        enrichments["brain_alpha_msh"] = pomc.get("alpha_msh_release", 0.0)
        enrichments["brain_mc4r"] = pomc.get("mc4r_engagement", 0.0)
        enrichments["brain_satiety_command"] = pomc.get("satiety_command", 0.0)
        enrichments["brain_pomc_state"] = pomc.get("pomc_state", "balanced")
"""

from brain.base_mechanism import BrainMechanism


class ArcuatePOMCSatiety(BrainMechanism):
    BASELINE = 0.30
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="ArcuatePOMCSatiety",
            human_analog="Arcuate POMC / α-MSH satiety counterbalance",
            layer="foundational",
        )
        self.state.setdefault("pomc_drive", self.BASELINE)
        self.state.setdefault("alpha_msh_release", 0.0)
        self.state.setdefault("mc4r_engagement", 0.0)
        self.state.setdefault("beta_endorphin_release", 0.0)
        self.state.setdefault("satiety_command", 0.0)
        self.state.setdefault("melanocortin_tone", 0.0)
        self.state.setdefault("pomc_state", "balanced")
        self.state.setdefault("recent_tone", [])
        self.state.setdefault("tick_count", 0)

    def _pomc_drive_target(self, energy: float, starvation: bool, satiety: float,
                            leptin: float, insulin: float, agrp: float) -> float:
        """POMC firing — leptin/insulin activate; AgRP, fasting, hypoglycemia inhibit."""
        if starvation:
            return 0.05  # POMC silenced during starvation
        target = self.BASELINE
        target += max(0.0, energy) * 0.4
        target += satiety * 0.3
        target += max(0.0, leptin - 0.5) * 0.4
        target += max(0.0, insulin - 0.5) * 0.3
        # AgRP inhibition
        target -= agrp * 0.4
        return max(0.0, min(1.0, target))

    def _alpha_msh(self, pomc: float, post_prandial: bool) -> float:
        """α-MSH release proportional to POMC firing, peptide kinetics slower."""
        target = pomc * 0.85
        if post_prandial:
            target = min(1.0, target + 0.10)
        return max(0.0, min(1.0, target))

    def _mc4r(self, alpha_msh: float, agrp: float) -> float:
        """MC4R engagement at PVN — α-MSH agonism minus AgRP antagonism."""
        return max(0.0, min(1.0, alpha_msh - agrp * 0.5))

    def _beta_endorphin(self, pomc: float, palatability: float, post_prandial: bool) -> float:
        """β-endorphin — hedonic eating opioid signal."""
        if not post_prandial or palatability < 0.30:
            return 0.0
        return min(1.0, pomc * 0.5 + palatability * 0.5)

    def _satiety_command(self, mc4r: float, alpha_msh: float, satiety: float) -> float:
        """Final satiety output — combined PVN-MC4R + α-MSH + peripheral satiety."""
        return min(1.0, mc4r * 0.5 + alpha_msh * 0.3 + satiety * 0.2)

    def _melanocortin_tone(self, pomc: float, agrp: float) -> float:
        """+ POMC dominant, - AgRP dominant."""
        return max(-1.0, min(1.0, pomc - agrp))

    def _classify_state(self, pomc: float, satiety: float, beta_end: float,
                         starvation: bool) -> str:
        if starvation:
            return "starvation_silent"
        if beta_end > 0.40:
            return "post_prandial_endorphin"
        if satiety > 0.50:
            return "fed_satiety"
        if pomc < 0.20:
            return "fasting_low"
        return "balanced"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))
        satiety = float(appetite.get("satiety_signal", 0.0))
        post_prandial = bool(appetite.get("post_prandial", False))
        npy = float(appetite.get("npy_drive", 0.30))
        agrp = float(appetite.get("agrp_drive", 0.30))

        leptin_proxy = prior.get("LeptinProxy", {})
        leptin = float(leptin_proxy.get("leptin_signal", 0.50))

        insulin_proxy = prior.get("InsulinProxy", {})
        insulin = float(insulin_proxy.get("insulin_signal", 0.50))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        # If neither leptin nor insulin proxies exist explicitly, infer from energy balance
        if leptin == 0.50 and abs(energy) > 0.30:
            leptin = max(0.0, min(1.0, 0.50 + energy * 0.4))
        if insulin == 0.50 and post_prandial:
            insulin = 0.75

        # --- POMC drive ---
        pomc_target = self._pomc_drive_target(energy, starvation, satiety, leptin,
                                                insulin, agrp)
        prev_pomc = float(self.state.get("pomc_drive", self.BASELINE))
        new_pomc = self._smooth(prev_pomc, pomc_target)

        # --- α-MSH ---
        alpha_msh = self._alpha_msh(new_pomc, post_prandial)
        prev_msh = float(self.state.get("alpha_msh_release", 0.0))
        new_msh = self._smooth(prev_msh, alpha_msh)

        # --- MC4R ---
        mc4r = self._mc4r(new_msh, agrp)

        # --- β-endorphin ---
        beta_end = self._beta_endorphin(new_pomc, valence_intensity, post_prandial)

        # --- Satiety command ---
        sat = self._satiety_command(mc4r, new_msh, satiety)

        # --- Melanocortin tone ---
        tone = self._melanocortin_tone(new_pomc, agrp)

        # --- State ---
        state = self._classify_state(new_pomc, sat, beta_end, starvation)

        recent = list(self.state.get("recent_tone", []))
        recent.append(round(tone, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pomc_drive"] = round(new_pomc, 4)
        self.state["alpha_msh_release"] = round(new_msh, 4)
        self.state["mc4r_engagement"] = round(mc4r, 4)
        self.state["beta_endorphin_release"] = round(beta_end, 4)
        self.state["satiety_command"] = round(sat, 4)
        self.state["melanocortin_tone"] = round(tone, 4)
        self.state["pomc_state"] = state
        self.state["recent_tone"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pomc_drive": round(new_pomc, 4),
            "alpha_msh_release": round(new_msh, 4),
            "mc4r_engagement": round(mc4r, 4),
            "beta_endorphin_release": round(beta_end, 4),
            "satiety_command": round(sat, 4),
            "melanocortin_tone": round(tone, 4),
            "pomc_state": state,
        }
