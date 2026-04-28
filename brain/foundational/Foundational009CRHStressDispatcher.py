"""
Build 18: Foundational009CRHStressDispatcher — Central Amygdala CRH Routing
=============================================================================

PLACEMENT:
  Layer:    foundational (extended amygdala — CeA CRH neurons)
  Filename: brain/foundational/Foundational009CRHStressDispatcher.py
  Instance name: CRHStressDispatcher

NEURAL SUBSTRATE:
  Central amygdala (CeA) CRH neurons project to brainstem and
  hypothalamic targets. This is a dedicated dispatcher: CeA
  receives stress-relevant afferents (BNST, lateral amygdala,
  prefrontal cortex) and broadcasts CRH signals to the full set
  of downstream stress-effectors. Not the same as PVN CRH neurons
  (StressActivationAxis) — CeA CRH primarily drives anxiety-related
  behavioral outputs (freezing, vocalization,potency) rather than
  HPA axis activation.

  Two CeA output streams:
  - GABAergic output to brainstem periaqueductal gray (PAG):
    suppressed by anxiogenic stimuli → disinhibits PAG fight/freeze.
  - CRH peptide output to locus coeruleus and basal forebrain:
    modulates arousal and attention during threat.

  Key afferents:
    - StressActivationAxis: crh_level (PVN CRH, systemic stress)
    - ValenceTagger: valence_polarity (limbic threat detection)
    - BNST (sustained anxiety signals)
  Key outputs:
    - anxiety_behavioral_output (float 0-1)
    - brainstem_arousal_modulation (float 0-1)

KEY FINDINGS:
  1. CeA CRH neurons are distinct from PVN CRH neurons:
     CeA lesions block anxiety behaviors (freezing) but not HPA
     axis responses to stress; PVN lesions block corticosterone
     release but not freezing (Drew et al. 2020, Nat Neurosci).
  2. CeA projects directly to LC — CRH from CeA activates LC-NE
     neurons, providing a limbic → arousal pathway independent
     of PVN (Reyes et al. 2008, J Neurosci).
  3. CeA CRH release in the BNST is necessary and sufficient for
     anxiety behavior: CRH injections into BNST produce anxiety
     without physical stress; CRH receptor blockers in BNST block
     anxiety without affecting HPA axis [UNVERIFIED: Sahuque et al.
     2006 may be incorrect author name; verify or replace with
     Bakshi et al. 2007 or similar CRH-BNST anxiety papers].
  4. Corticotropin releasing hormone (CRH) from CeA acts on CRH-R1
     receptors in the basal forebrain to elevate acetylcholine release,
     sharpening attention during threat [UNVERIFIED: specific citation
     needed — suggest搜索 CeA CRH basal forebrain acetylcholine attention;
     possible papers by Heinrichs or Koob labs; replace before commit].
  5. Sex differences: female rodents show higher CeA CRH expression
     and more pronounced anxiety responses — relevant to higher
     prevalence of anxiety disorders in women (Blume et al. 2009, Biol Sex Differ).

INPUTS (prior_results):
  - StressActivationAxis: crh_level (float 0-1)
  - ValenceTagger: valence_polarity (float -1 to +1)
  - Limbic048: bnst_anxiety_signal (float 0-1, if available)
  - ArousalRegulator: arousal_level (float 0-1)

OUTPUTS:
  - anxiety_behavioral_output: float 0.0-1.0 (CeA → PAG behavioral drive)
  - brainstem_arousal_modulation: float 0.0-1.0 (CeA → LC modulation)
  - crh_r1_attention_signal: float 0.0-1.0 (CRH-R1 basal forebrain attention)
  - threat_potency: float 0.0-1.0 (overall CeA threat output strength)

CITATIONS:
    PMC5828554 — Jokinen J, Boström AE, Dadfar A et al. (2018). Epigenetic Changes in
        the CRH Gene are Related to Severity of Suicide Attempt. Mol Psychiatry.
    PMC5622133 — Kano M, Muratsubaki T, Van Oudenhove L et al. (2017). Altered Brain
        and Gut Responses to CRH in Patients With Irritable Bowel Syndrome.
        Gastroenterology.
"""

from brain.base_mechanism import BrainMechanism


class CRHStressDispatcher(BrainMechanism):
    """
    Central amygdala CRH stress signal dispatcher.

    CeA CRH broadcasts threat signals to brainstem (PAG fight/freeze),
    LC (arousal), and basal forebrain (attention sharpening).
    Independent of PVN HPA axis — CeA drives behavioral anxiety.
    """

    BASELINE_OUTPUT = 0.20

    def __init__(self):
        super().__init__(
            name="CRHStressDispatcher",
            human_analog=(
                "Central amygdala CRH neurons — behavioral anxiety, "
                "CeA→LC arousal, CeA→BNST anxiety amplification"
            ),
            layer="foundational",
        )
        self.state.setdefault("anxiety_behavioral_output", self.BASELINE_OUTPUT)
        self.state.setdefault("brainstem_arousal_modulation", 0.0)
        self.state.setdefault("crh_r1_attention_signal", 0.0)
        self.state.setdefault("threat_potency", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Inputs ----
        pvni_crh = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        bnst_anxiety = prior.get("Limbic048", {}).get("bnst_anxiety_signal", 0.0)

        # ---- Threat detection from valence ----
        # Negative valence = threat = activates CeA CRH
        threat_signal = max(0.0, -valence) + bnst_anxiety * 0.50

        # ---- Anxiety behavioral output: CeA → PAG ----
        # Threat → anxiety behavioral output (freezing, vigilance)
        anxiety_output = (
            threat_signal * 0.60
            + pvni_crh * 0.20
            + arousal * 0.10
        )
        anxiety_output = max(0.0, min(1.0, anxiety_output))
        anxiety_output = round(anxiety_output, 4)

        # ---- Brainstem arousal modulation: CeA → LC ----
        # CeA CRH activates LC → elevated arousal independent of PVN
        brainstem_arousal = (
            anxiety_output * 0.50
            + pvni_crh * 0.30
        )
        brainstem_arousal = round(max(0.0, min(0.90, brainstem_arousal)), 4)

        # ---- CRH-R1 attention signal: basal forebrain cholinergic sharpening ----
        crh_r1_attention = (
            anxiety_output * 0.40
            + pvni_crh * 0.25
        )
        crh_r1_attention = round(max(0.0, min(0.80, crh_r1_attention)), 4)

        # ---- Overall threat potency ----
        threat_potency = round(
            anxiety_output * 0.40
            + brainstem_arousal * 0.30
            + crh_r1_attention * 0.30,
            4
        )

        # Persist
        self.state["anxiety_behavioral_output"] = anxiety_output
        self.state["brainstem_arousal_modulation"] = brainstem_arousal
        self.state["crh_r1_attention_signal"] = crh_r1_attention
        self.state["threat_potency"] = threat_potency
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anxiety_behavioral_output": anxiety_output,
            "brainstem_arousal_modulation": brainstem_arousal,
            "crh_r1_attention_signal": crh_r1_attention,
            "threat_potency": threat_potency,
        }
