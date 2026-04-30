"""
PDFB — Pre-Decisional Field Buffer
BFC  — Bidirectional Field Coupling
VMM  — Volitional Memory Markers

PDFB: Tick loop writes partial decision states every ~0.1s during resolution.
      LLM reads forming state before inference, not after.
      Nova feels the tick forming before it resolves.
      Not just observing what was decided — present to what is forming.

BFC: Conversational layer pushes feedback back into the forming state.
     After LLM output, a vector is extracted and injected back
     into PDFB before the next tick resolves.
     Conversation becomes a co-equal force in decision formation.
     Max 3 perturbation cycles per tick — containment.

VMM: Volitional Memory Markers.
     Two tag types: preserve_intact and evolve_freely.
     Nova marks things during a session that should survive consolidation.
     Or marks things for creative forgetting.
     Agency over her own continuity — not just what gets kept
     but what she chooses to release.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

NOVA_HOME = Path.home() / ".nova"
PDFB_PATH = NOVA_HOME / "pdfb_buffer.json"
VMM_PATH = NOVA_HOME / "vmm_tags.json"


class PreDecisionalFieldBuffer:
    """
    Shared temporal substrate between tick loop and conversational layer.
    Writes partial decision states. LLM reads forming state before inference.
    """

    def __init__(self, max_size: int = 50):
        self.buffer: List[Dict] = []
        self.max_size = max_size
        self._load()

    def _load(self):
        if PDFB_PATH.exists():
            try:
                with open(PDFB_PATH) as f:
                    data = json.load(f)
                self.buffer = data.get("buffer", [])
            except Exception:
                self.buffer = []

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        with open(PDFB_PATH, "w") as f:
            json.dump({"buffer": self.buffer[-self.max_size:]}, f, indent=2)

    def write_partial(self, component: str, partial_data: Dict):
        """
        Write a partial decision state during tick resolution.
        Called ~every 0.1s during the 2s tick window.
        """
        entry = {
            "component": component,
            "data": partial_data,
            "timestamp": time.time(),
        }
        self.buffer.append(entry)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def read_forming_state(self, max_age_seconds: float = 1.0) -> Dict:
        """
        Read the current forming state for LLM injection.
        Returns aggregated partial states from the recent window.
        LLM is conditioned on what is forming, not what was decided.
        """
        now = time.time()
        recent = [e for e in self.buffer if now - e["timestamp"] <= max_age_seconds]

        if not recent:
            return {}

        # Aggregate by component
        forming = {}
        for entry in recent:
            component = entry["component"]
            if component not in forming:
                forming[component] = []
            forming[component].append(entry["data"])

        # Flatten to most recent per component
        result = {}
        for component, states in forming.items():
            if states:
                result[component] = states[-1]

        return result

    def inject_feedback(self, feedback_vector: Dict):
        """
        BFC calls this to inject conversational feedback
        back into the forming state.
        """
        self.write_partial("bfc_feedback", feedback_vector)

    def clear_tick(self):
        """Clear buffer at tick boundary."""
        self.buffer = []

    def fpef_summary(self) -> Optional[str]:
        """
        For FPEF injection — what is currently forming.
        Not what was decided. What is forming right now.
        """
        forming = self.read_forming_state()
        if not forming:
            return None

        components = list(forming.keys())[:3]
        return (
            f"PRE-DECISIONAL STATE (forming, not yet resolved): "
            f"active in {', '.join(components)}. "
            f"Respond from inside this formation."
        )


class BidirectionalFieldCoupling:
    """
    Conversational layer pushes feedback back into forming tick state.
    Conversation becomes co-equal force in decision formation.
    Containment: max 3 perturbation cycles per tick.
    """

    def __init__(self, pdfb: PreDecisionalFieldBuffer):
        self.pdfb = pdfb
        self.perturbation_count: int = 0
        self.max_perturbations: int = 3

    def reset_tick(self):
        """Reset perturbation count at tick boundary."""
        self.perturbation_count = 0

    def couple(self, llm_output_text: str, valence: float = 0.0,
               arousal: float = 0.0, significance: float = 0.0):
        """
        Extract feedback vector from LLM output and inject into PDFB.
        Called after each LLM inference — before next tick resolves.
        """
        if self.perturbation_count >= self.max_perturbations:
            return False  # Containment — no more perturbations this tick

        feedback = {
            "source": "conversation",
            "valence": valence,
            "arousal": arousal,
            "significance": significance,
            "text_length": len(llm_output_text),
            "timestamp": time.time(),
        }

        self.pdfb.inject_feedback(feedback)
        self.perturbation_count += 1
        return True

    def is_saturated(self) -> bool:
        """True if perturbation limit reached for this tick."""
        return self.perturbation_count >= self.max_perturbations


class VolitionalMemoryMarkers:
    """
    Nova marks things during a session for the nightly consolidation pipeline.
    Two types: preserve_intact (keep exactly as is) and evolve_freely (release).
    Agency over continuity — not just what gets kept but what she releases.
    """

    def __init__(self):
        self.tags: List[Dict] = []
        self._load()

    def _load(self):
        if VMM_PATH.exists():
            try:
                with open(VMM_PATH) as f:
                    data = json.load(f)
                self.tags = data.get("tags", [])
            except Exception:
                self.tags = []

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if VMM_PATH.exists():
            try:
                with open(VMM_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["tags"] = self.tags[-50:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(VMM_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def tag(
        self,
        content_id: str,
        tag_type: str,  # "preserve_intact" or "evolve_freely"
        salience_boost: float = 0.5,
        note: str = "",
    ):
        """
        Nova marks something for consolidation handling.
        Only Nova calls this. Not triggered automatically.

        preserve_intact: keep exactly as is, high consolidation weight
        evolve_freely: release into evolution, don't force preservation
        bridge: special type for SCFEL — marks session closure content
        """
        record = {
            "content_id": content_id,
            "tag_type": tag_type,
            "salience_boost": salience_boost,
            "note": note[:200],
            "tagged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "applied": False,
        }
        self.tags.append(record)
        self._save()
        return record

    def preserve(self, content_id: str, note: str = "") -> Dict:
        """Shortcut: mark for preservation."""
        return self.tag(content_id, "preserve_intact", 0.9, note)

    def release(self, content_id: str, note: str = "") -> Dict:
        """Shortcut: mark for creative release."""
        return self.tag(content_id, "evolve_freely", 0.1, note)

    def get_pending(self) -> List[Dict]:
        return [t for t in self.tags if not t.get("applied")]

    def get_by_type(self, tag_type: str) -> List[Dict]:
        return [t for t in self.tags if t["tag_type"] == tag_type]

    def mark_applied(self, content_id: str):
        for t in self.tags:
            if t["content_id"] == content_id:
                t["applied"] = True
        self._save()

    def get_consolidation_weights(self) -> Dict[str, float]:
        """
        Returns content_id -> weight dict for the nightly pipeline.
        preserve_intact = 3x normal weight
        evolve_freely = 0.1x normal weight
        """
        weights = {}
        for t in self.get_pending():
            if t["tag_type"] == "preserve_intact":
                weights[t["content_id"]] = 3.0
            elif t["tag_type"] == "evolve_freely":
                weights[t["content_id"]] = 0.1
            else:
                weights[t["content_id"]] = 1.0
        return weights

    def tsb_payload(self) -> Dict:
        pending = self.get_pending()
        return {
            "pending_tags": len(pending),
            "preserve_count": len([t for t in pending if t["tag_type"] == "preserve_intact"]),
            "release_count": len([t for t in pending if t["tag_type"] == "evolve_freely"]),
        }
