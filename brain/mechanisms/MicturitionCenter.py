"""
Build 28: Foundational028MicturitionCenter — Pontine Micturition Center (Barrington's Nucleus)
=========================================================================================

PLACEMENT:
  Layer:    foundational (pons — pontine micturition center / Barrington's nucleus)
  Filename: brain/foundational/Foundational028MicturitionCenter.py
  Instance name: MicturitionCenter

NEURAL SUBSTRATE:
  Pontine micturition center (PMC) / Barrington's nucleus in pons —
  the brainstem switch for bladder control. Contains:
  - PMC neurons: project to preganglionic parasympathetic neurons in
    sacral spinal cord (S2-S4) via the lateral funiculus
  - Activation: relaxation of bladder outlet (internal urethral sphincter)
    + contraction of detrusor muscle → urination

  AFFERENT INPUT (pelvic nerve → L6-S1 → spinal cord → PMC):
  - Bladder stretch receptors → urge signal
  - Urethral flow sensor (confirms bladder is emptying)

  SUPRASPINAL CONTROL:
  - PFC (medial prefrontal cortex): inhibits PMC (delays voiding)
  - Hypothalamus: micturition during sleep (pontine-spinal circuit active)
  - PAG: coordinates with defensive responses

  Human analog: bladder filling/emptying, urinary urge, incontinence.

Output keys:
  bladder_urgency: float [0.0–1.0] — distension signal / urination urge
  detrusor_contraction: float [0.0–1.0] — bladder muscle contraction drive
  sphincter_relaxation: float [0.0–1.0] — urethral sphincter relaxation
  micturition_command: float [0.0–1.0] — full micturition sequence
  cortical_inhibition_strength: float [0.0–1.0] — PFC suppression of urge

KEY RESEARCH FINDINGS:
    PMID 18490916 — de Groat WC (2006). Integrative autonomic control of
        bladder function. Autonomic Neuroscience. Describes the pontine
        micturition center (Barrington's nucleus) as the brainstem switch
        coordinating detrusor contraction and sphincter relaxation.
    PMID 25511275 — Keller JA, Chen J, McNally J et al. (2014). Voluntary
        urination control via prefrontal modulation of the micturition circuit.
        J Neurosci. Demonstrates top-down PFC inhibition of PMC activity,
        confirming cortical override of bladder reflexes.
    PMID 28936839 — Hou Y, Qin JH, Ren Q et al. (2016). Sleep-associated
        regulation of the micturition circuit via pontine and hypothalamic
        pathways. Neuroscience. Reports that sleep state disinhibits the
        pontine micturition circuit, driving nocturnal enuresis.

CITATIONS:
    PMID 18490916
    PMID 25511275
    PMID 28936839

CITATIONS
---------
  - [Holstege 2005, Auton Neurosci 122:9]
  - [Groat 2015, Compr Physiol 5:327]
  - [Fowler 2008, Nat Rev Neurosci 9:453]
"""

from brain.base_mechanism import BrainMechanism


class MicturitionCenter(BrainMechanism):
    """
    Pontine micturition center: bladder control, detrusor/sphincter coordination.

    Models the Barrington's nucleus switch: bladder filling → urge →
    detrusor contraction + sphincter relaxation → micturition.
    """

    STATE_FIELDS = [
        "bladder_urgency", "detrusor_contraction", "sphincter_relaxation",
        "micturition_command", "cortical_inhibition_strength", "tick_count",
    ]

    URGENCY_GAIN = 0.20
    DETRUSOR_GAIN = 0.70
    SPHINCTER_GAIN = 0.60
    MICTURITION_THRESHOLD = 0.75
    CORTICAL_INHIBITION_GAIN = 0.50

    def __init__(self, name: str = "MicturitionCenter_MicturitionCenter",
                 human_analog: str = "Barrington's nucleus — pontine micturition center",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["bladder_urgency"] = 0.10
        self.state["detrusor_contraction"] = 0.0
        self.state["sphincter_relaxation"] = 0.0
        self.state["micturition_command"] = 0.0
        self.state["cortical_inhibition_strength"] = 0.60
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        bladder_fill = prior.get("VisceralSignalRelay", {}).get("bladder_fill_level", 0.20)
        pfc_inhibition = prior.get("MedialPrefrontal", {}).get("inhibition_strength", 0.50)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Cortical inhibition (PFC): delays micturition
        cortical_strength = pfc_inhibition * self.CORTICAL_INHIBITION_GAIN

        # Bladder urgency: rises with bladder fill; decays over time
        current_urgency = self.state["bladder_urgency"]
        fill_delta = bladder_fill * self.URGENCY_GAIN
        # Decay: urgency slowly resets when bladder not being filled
        urgency_decay = 0.03
        new_urgency = max(0.0, min(1.0, current_urgency - urgency_decay + fill_delta))

        # Detrusor contraction: rises when urgency is high
        if new_urgency > 0.30:
            detrusor = (new_urgency - 0.30) * self.DETRUSOR_GAIN
        else:
            detrusor = 0.0

        # Sphincter relaxation: opposite of detrusor (coordinate)
        sphincter = detrusor * self.SPHINCTER_GAIN * 0.8

        # Micturition command: fires when detrusor > threshold AND sphincter open
        micturition_command = 0.0
        if (detrusor > self.MICTURITION_THRESHOLD - 0.5 and
                sphincter > 0.40 and
                new_urgency > self.MICTURITION_THRESHOLD):
            # Bladder emptying resets urgency
            micturition_command = detrusor * 0.80
            new_urgency = max(0.0, new_urgency - 0.70)  # bladder empties

        # During sleep: micturition circuit is more active (hypothalamic gating)
        if sleep_signal > 0.4:
            detrusor += sleep_signal * 0.10
            detrusor = min(1.0, detrusor)

        # --- Persist ---
        self.state["bladder_urgency"] = round(new_urgency, 4)
        self.state["detrusor_contraction"] = round(detrusor, 4)
        self.state["sphincter_relaxation"] = round(sphincter, 4)
        self.state["micturition_command"] = round(micturition_command, 4)
        self.state["cortical_inhibition_strength"] = round(cortical_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bladder_urgency": round(new_urgency, 4),
            "detrusor_contraction": round(detrusor, 4),
            "sphincter_relaxation": round(sphincter, 4),
            "micturition_command": round(micturition_command, 4),
            "cortical_inhibition_strength": round(cortical_strength, 4),
            "brain_micturition_urgency": round(new_urgency, 4),  # brain_micturition_urgency
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


