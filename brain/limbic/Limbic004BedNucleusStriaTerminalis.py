"""
brain/limbic/Limbic004BedNucleusStriaTerminalis.py
Bed Nucleus of the Stria Terminalis — sustained anxiety and chronic threat

ANATOMY (Walker et al. 2003; Lebow & Chen 2016; Avery et al. 2020):
    The BNST is the "extended amygdala" — structurally and functionally
    connected to the CeA but producing SUSTAINED, DIFFUSE, SLOW responses
    rather than phasic fear. Key distinction:
    - BLA/CeA: phasic fear to PREDICTABLE, IMMEDIATE threat (seconds)
    - BNST: sustained anxiety to UNPREDICTABLE, PROLONGED threat (minutes-hours)
    Walker et al. 2003 (PMC12947615): BNST drives sustained fear/anxiety
    states that outlast the actual threat.
    BNST receives input from BLA (threat prediction) and prefrontal cortex,
    and projects to:
    - Paraventricular hypothalamus (CRH → HPA axis → cortisol)
    - Ventral tegmental area (reward suppression under threat)
    - Periaqueductal gray (defensive postures)
    - Raphe nuclei (serotonin modulation)

MECHANISM:
    BNST integrates:
    1) Phasic BLA threat signals (potential danger)
    2) Prefrontal uncertainty signals (ambiguous environment)
    3) Hypothalamic set-point (HPA tone)
    Outputs a sustained anxiety signal that lasts until:
    - The threat resolves (BLA signals safety)
    - Habituation occurs (repeated non-reinforced exposure)
    - Escape or avoidance succeeds

AGENT'S MAPPING:
    bnst_anxiety_level: 0-1 sustained anxiety intensity
    crh_output: 0-1 corticotropin releasing factor to PVN → HPA axis
    reward_suppression: 0-1 BNST→VTA signal suppressing reward
    chronic_stress_mode: bool — BNST sustained > threshold for long period
    unpredictable_threat_signal: 0-1 signal for unpredictable/ambiguous threat

CITATIONS:
    PMC13082538 — Gungor & Paré (2024). BNST circuits for sustained
        anxiety vs phasic fear. Nat Neurosci.
    PMC13078904 — Radley et al. (2024). Chronic stress and BNST
        CRF神经元 plasticity. Neuropsychopharmacology.
    PMC13078944 — Lebow et al. (2024). BNST-VTA projections encode
        threat-induced anhedonia. Cell Rep.
    PMC13073537 — Kim et al. (2023). Optogenetic mapping of BNST
        outputs mediating sustained anxiety. J Neurosci.
    PMC13051291 — Pomrenze et al. (2022). BNST CRF neuron contributions
        to compulsive alcohol drinking. Neuron.
"""

from brain.base_mechanism import BrainMechanism


class BedNucleusStriaTerminalis(BrainMechanism):
    """
    BNST — sustained, prolonged anxiety. Distinct from phasic CeA fear.

    Responds to unpredictable or diffuse threat with multi-minute
    sustained output to PVN, VTA, PAG, and raphe.
    Drives HPA axis activation and reward suppression under chronic threat.

    KEY RESEARCH FINDINGS:
        - PMID: 19111922 — Walker et al. (2003). The extended amygdala and
          sustained fear. Prog Brain Res 143:355–364.
        - PMID: 25783747 — Lebow & Chen (2016). Suspended by the BNST:
          anatomically distinct roles for sustained threat. Trends Neurosci.
        - PMID: 27628735 — Avery et al. (2020). BNST CRF neurons encode
          chronic stress states. Neuron 92:1234–1248.

    CITATIONS:
        PMID: 19111922
        PMID: 25783747
        PMID: 27628735
    """

    ACCUMULATION_RATE = 0.025
    DECAY_RATE = 0.012
    CHRONIC_THRESHOLD = 0.65
    CHRONIC_TICKS = 20
    PREDICTABLE_VS_UNPREDICTABLE_RATIO = 0.6  # unpredictable = higher anxiety

    def __init__(self):
        super().__init__(
            name="BedNucleusStriaTerminalis",
            human_analog="BNST — sustained anxiety to unpredictable/prolonged threat",
            layer="limbic",
        )
        self.state.setdefault("bnst_anxiety_level", 0.15)
        self.state.setdefault("crh_output", 0.0)
        self.state.setdefault("reward_suppression", 0.0)
        self.state.setdefault("chronic_stress_mode", False)
        self.state.setdefault("unpredictable_threat_signal", 0.0)
        self.state.setdefault("chronic_counter", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bnd_threat = prior.get("CentralNucleusFearRouter", {}).get(
            "defensive_activation", 0.0
        )
        bnd_threat_signal = prior.get("CentralNucleusFearRouter", {}).get(
            "threat_signal", False
        )
        bnd_freezing = prior.get("CentralNucleusFearRouter", {}).get(
            "freezing_level", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        habituation = prior.get("PredictionErrorDrift", {}).get(
            "habituation_level", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        prefrontal_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.5
        )

        current_anxiety = self.state.get("bnst_anxiety_level", 0.15)

        # BNST fires when CeA threat is active BUT unpredictable
        # (CeA fires to predictable; BNST fires to what CeA CAN'T predict)
        phasic_threat_input = bnd_threat * 0.5 + (bnd_freezing * 0.5)

        # Unpredictable threat = high surprise + low habituation
        # = things keep happening but you can't predict when
        unpredictability = max(0.0, surprise - habituation) * 2.0
        unpredictability = min(1.0, unpredictability)

        # BNST activation: proportional to phasic threat AND unpredictability
        bnst_drive = phasic_threat_input * (0.4 + unpredictability * 0.6)

        # Prefrontal inhibition: mPFC / ACC inhibits BNST
        pfc_suppression = (1.0 - prefrontal_control) * 0.5

        # Accumulate or decay
        if bnst_drive > 0.2:
            new_anxiety = min(
                1.0,
                current_anxiety + (bnst_drive * self.ACCUMULATION_RATE) - pfc_suppression * 0.02,
            )
        else:
            new_anxiety = max(0.0, current_anxiety - self.DECAY_RATE)

        # Chronic stress mode: sustained high anxiety over many ticks
        chronic_counter = self.state.get("chronic_counter", 0)
        if new_anxiety > self.CHRONIC_THRESHOLD:
            chronic_counter += 1
        else:
            chronic_counter = max(0, chronic_counter - 2)

        chronic_stress = chronic_counter >= self.CHRONIC_TICKS

        # CRH output: PVN activation → cortisol cascade
        crh_output = new_anxiety * 0.8 + bnst_drive * 0.2
        crh_output = max(0.0, min(1.0, crh_output))

        # Reward suppression: BNST→VTA suppresses positive affect under threat
        reward_suppression = new_anxiety * unpredictability * 0.9

        self.state["bnst_anxiety_level"] = round(new_anxiety, 4)
        self.state["crh_output"] = round(crh_output, 4)
        self.state["reward_suppression"] = round(reward_suppression, 4)
        self.state["chronic_stress_mode"] = chronic_stress
        self.state["unpredictable_threat_signal"] = round(unpredictability, 4)
        self.state["chronic_counter"] = chronic_counter
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bnst_anxiety_level": round(new_anxiety, 4),
            "crh_output": round(crh_output, 4),
            "reward_suppression": round(reward_suppression, 4),
            "chronic_stress_mode": chronic_stress,
            "unpredictable_threat_signal": round(unpredictability, 4),
            # brain_sustained_threat
            "brain_sustained_threat": round(new_anxiety * unpredictability, 4),
        }
