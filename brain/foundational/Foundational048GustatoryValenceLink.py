"""
Build 48: Foundational048GustatoryValenceLink — Nucleus of the Solitary Tract Gustatory Area
=======================================================================================

PLACEMENT:
  Layer:    foundational (medulla — nucleus tractus solitarius, gustatory zone)
  Filename: brain/foundational/Foundational048GustatoryValenceLink.py
  Instance name: GustatoryValenceLink

NEURAL SUBSTRATE:
  Gustatory nucleus of the NTS (gNTS) in medulla — receives primary
  gustatory afferents from the facial nerve (CN VII, anterior 2/3 tongue),
  glossopharyngeal nerve (CN IX, posterior 1/3 tongue), and vagus nerve
  (CN X, epiglottis, palate). The gNTS projects to:
  - Ventral posteromedial nucleus (VPM) of thalamus → gustatory cortex
  - Parabrachial nucleus → central amygdala (taste-aversion learning)
  - Hypothalamus (lateral, ventromedial) → feeding behavior

  TASTE QUALITY CODING:
  - Sweet: anterior tongue → chorda tympani → CN VII → gNTS → VPM
  - Bitter: posterior tongue → CN IX → gNTS → VPM
  - Salty: anterior + posterior → CN VII + CN IX → gNTS
  - Umami: multiple nerves → gNTS
  - Sour: multiple nerves → gNTS

  Human analog: taste, flavor, food reward, taste aversion learning.

Output keys:
  taste_valence: float [-1.0 to 1.0] — aversive (-1) to appetitive (+1) taste
  sweet_detector: float [0.0–1.0] — sweet taste intensity
  bitter_detector: float [0.0–1.0] — bitter taste intensity
  umami_detector: float [0.0–1.0] — umami (protein) detection
  taste_aversion_learning: float [0.0–1.0] — conditioned taste aversion

CITATIONS:
    PMC5435754 — Cassidy RM, Tong Q (2017). Hunger and Satiety Gauges Reward
        Sensitivity. Front Neurosci.
    PMC11105013 — Gutierrez R, Fonseca E, Simon SA (2020). The Neuroscience of
        Sugars in Taste, Gut-Reward, Feeding Circuits, and Obesity. Physiol Behav.
"""

from brain.base_mechanism import BrainMechanism


class GustatoryValenceLink(BrainMechanism):
    """
    NTS gustatory zone: taste quality, valence, and aversion learning.

    Models taste processing, quality coding, and conditioned taste aversion.
    """

    STATE_FIELDS = [
        "taste_valence", "sweet_detector", "bitter_detector",
        "umami_detector", "taste_aversion_learning", "tick_count",
    ]

    SWEET_GAIN = 0.70
    BITTER_GAIN = 0.65
    UMAMI_GAIN = 0.55
    AVERSION_GAIN = 0.50

    def __init__(self, name: str = "GustatoryValenceLink",
                 human_analog: str = "NTS gustatory zone — taste and valence",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["taste_valence"] = 0.0
        self.state["sweet_detector"] = 0.10
        self.state["bitter_detector"] = 0.10
        self.state["umami_detector"] = 0.10
        self.state["taste_aversion_learning"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        sweet = prior.get("SweetTasteReceptor", {}).get("sweet_intensity", 0.0)
        bitter = prior.get("BitterTasteReceptor", {}).get("bitter_intensity", 0.0)
        umami = prior.get("UmamiTasteReceptor", {}).get("umami_intensity", 0.0)
        salty = prior.get("SaltyTasteReceptor", {}).get("salty_intensity", 0.0)
        gut_signal = prior.get("GutSignalRelay", {}).get("nutrient_signal", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)

        # Taste quality detectors
        sweet_detector = sweet * self.SWEET_GAIN
        bitter_detector = bitter * self.BITTER_GAIN
        umami_detector = umami * self.UMAMI_GAIN

        # Taste valence: net hedonic value (sweet=positive, bitter=negative)
        taste_valence = (sweet_detector * 0.40) - (bitter_detector * 0.60)
        # Umami adds positive valence (protein signal)
        taste_valence += umami_detector * 0.30
        # Salty (Na+) adds positive when low, negative when high
        taste_valence += salty * 0.20 - (bitter_detector * 0.05)

        # Taste aversion learning: bitter + amygdala fear → conditioned aversion
        aversion_raw = bitter_detector * amygdala * self.AVERSION_GAIN
        taste_aversion_learning = min(1.0, aversion_raw)

        # --- Persist ---
        self.state["taste_valence"] = round(taste_valence, 4)
        self.state["sweet_detector"] = round(sweet_detector, 4)
        self.state["bitter_detector"] = round(bitter_detector, 4)
        self.state["umami_detector"] = round(umami_detector, 4)
        self.state["taste_aversion_learning"] = round(taste_aversion_learning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "taste_valence": round(taste_valence, 4),
            "sweet_detector": round(sweet_detector, 4),
            "bitter_detector": round(bitter_detector, 4),
            "umami_detector": round(umami_detector, 4),
            "taste_aversion_learning": round(taste_aversion_learning, 4),
        }
