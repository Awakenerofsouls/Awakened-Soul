#!/usr/bin/env python3
"""
Nexus {{AGENT_NAME}} — Mechanism Auto-Generator
Reads NEXUS_AGENT_MECHANISMS_*.md schema files
Generates all Python mechanism files in brain/<layer>/
Run: python generate_mechanisms.py
"""

import re
import os
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
# WORKSPACE is the directory containing this script (generate_mechanisms.py)
# Works on any machine — Mac, Linux, or Windows.
WORKSPACE = Path(__file__).parent.resolve()

SCHEMA_FILES = [
    WORKSPACE / "MECHANISMS_FULL.md",
    WORKSPACE / "MECHANISMS_PART2.md",
    WORKSPACE / "MECHANISMS_PART3.md",
    WORKSPACE / "MECHANISMS_PART4.md",
]
OUTPUT_BASE = WORKSPACE / "brain"
LAYER_MAP = {
    "foundational": "foundational",
    "limbic": "limbic",
    "subcortical": "subcortical",
    "neocortical": "neocortical",
    "integration": "integration",
}
# ── Template ────────────────────────────────────────────────────────
TEMPLATE = '''from ..base_mechanism import BrainMechanism

class {class_name}(BrainMechanism):
    """
    Human Analog: {human_analog}
    Purpose: {purpose}
    Trigger: {trigger}
    Timing: {timing}
    Priority: {priority}
    """
    def __init__(self):
        super().__init__(
            name="{name}",
            human_analog="{human_analog}",
            layer="{layer}"
        )
{state_init}
    async def tick(self, input_data: dict) -> dict:
{body}
        return {{
{outputs}        }}
'''
# ── Parse helpers ───────────────────────────────────────────────────
ENTRY_RE = re.compile(
    r'^### ([A-Z][A-Z0-9]+-\d+):\s*(.+?)\s*$\n'
    r'(?:.*?Human Analog:?\s*(.+?)\s*\n)?'
    r'(?:.*?Purpose:?\s*(.+?)\s*\n)?'
    r'(?:.*?Trigger:?\s*(.+?)\s*\n)?'
    r'(?:.*?Inputs:?\s*(.+?)\s*\n)?'
    r'(?:.*?Outputs:?\s*(.+?)\s*\n)?'
    r'(?:.*?State:?\s*(.+?)\s*\n)?'
    r'(?:.*?Dependencies:?\s*(.+?)\s*\n)?'
    r'(?:.*?Priority:?\s*(.+?)\s*\n)?'
    r'(?:.*?Timing:?\s*(.+?)\s*\n)?'
    r'(?:.*?Edge:?\s*(.+?)\s*\n)?',
    re.MULTILINE | re.DOTALL
)

def clean(s):
    return (s or "").replace('"', "'").strip()

def snake(name):
    # "LayerIVThalamicInputGate" → "layer_iv_thalamic_input_gate"
    s1 = re.sub(r'(.)([A-Z])', r'\1_\2', name)
    return re.sub(r'_+', '_', s1).lower().strip('_')

def class_name(mech_id, name):
    # "FOUNDATIONAL-006" + "SympatheticVasomotorController" → "Foundational006SympatheticVasomotorController"
    prefix = mech_id.split('-')[0].capitalize()
    num_match = re.search(r'\d+', mech_id)
    num = num_match.group() if num_match else "00"
    safe = re.sub(r'[^a-zA-Z0-9]', '', name)
    return f"{prefix}{num}{safe}"

def detect_layer(mech_id):
    key = mech_id.split('-')[0].lower()
    return LAYER_MAP.get(key, "foundational")

def build_body(trigger, purpose, layer):
    """Generate the tick() method body based on mechanism type."""
    trigger = clean(trigger).lower()
    purpose = clean(purpose).lower()
    
    # Common patterns
    if "valence" in purpose or "valence" in trigger:
        return '''        intensity, polarity = self.compute_simple_valence(input_data.get("text", ""))
        metadata = {
            "valence_intensity": intensity,
            "valence_polarity": polarity,
            "high_valence": abs(intensity) > 0.65
        }
        if metadata["high_valence"]:
            self.feed_to_memory(metadata)
        self.save_state()'''
    
    if "arousal" in purpose or "locus coeruleus" in clean(purpose) or "reticular" in purpose:
        return '''        novelty = len(input_data.get("text", "")) / 150.0
        arousal = self.state.get("arousal_level", 0.6)
        arousal = max(0.2, min(1.0, arousal + (novelty - 0.5) * 0.08))
        self.state["arousal_level"] = arousal
        metadata = {"arousal_level": arousal, "high_arousal": arousal > 0.8}
        self.save_state()
        return metadata'''
    
    if "homeostat" in purpose or "hypothalamus" in purpose:
        return '''        drives = self.state.get("drives", {"curiosity": 0.45, "fatigue": 0.35, "social": 0.25})
        for d in drives:
            drives[d] = max(0.0, min(1.0, drives[d] * 0.98 + 0.04))
        high = max(drives.values())
        self.state["drives"] = drives
        metadata = {"drives": drives.copy(), "highest_drive": high}
        if high > 0.7:
            self.feed_to_memory(metadata)
        self.save_state()
        return metadata'''
    
    if "sleep" in purpose or "fatigue" in purpose or "circadian" in purpose:
        return '''        fatigue = input_data.get("drives", {}).get("fatigue", 0.3)
        sleep_pressure = self.state.get("sleep_pressure", 0.0)
        sleep_pressure = max(0.0, min(1.0, sleep_pressure * 0.97 + fatigue * 0.05))
        self.state["sleep_pressure"] = sleep_pressure
        metadata = {"sleep_pressure": sleep_pressure, "sleep_gate": sleep_pressure > 0.7}
        self.save_state()
        return metadata'''
    
    if "habit" in purpose or "groove" in purpose or "striatum" in purpose:
        return '''        action = input_data.get("last_action", "")
        if action:
            self.state.setdefault("habits", {})
            self.state["habits"][action] = self.state["habits"].get(action, 0) + 0.1
        metadata = {"habit_strength": max(self.state.get("habits", {}).values(), default=0)}
        self.save_state()
        return metadata'''
    
    if "cerebellar" in purpose or "timing" in purpose:
        return '''        metadata = {"timing_synced": True}
        self.save_state()
        return metadata'''
    
    if "thalam" in purpose:
        return '''        salience = len(input_data.get("text", "")) / 180
        metadata = {"salience": salience}
        self.save_state()
        return metadata'''
    
    if "prediction error" in purpose or "vta" in purpose or "dopamine" in purpose:
        return '''        expected = input_data.get("expected_outcome", 0.5)
        actual = input_data.get("actual_outcome", 0.6)
        error = actual - expected
        metadata = {"prediction_error": error, "motivation_boost": abs(error) * 0.7}
        self.save_state()
        return metadata'''
    
    if "anxiety" in purpose or "sustain" in purpose or "bnst" in purpose:
        return '''        anxiety = self.state.get("sustained_anxiety", 0.3)
        anxiety = max(0.1, min(0.9, anxiety + 0.02))
        self.state["sustained_anxiety"] = anxiety
        metadata = {"sustained_anxiety": anxiety}
        self.save_state()
        return metadata'''
    
    if "memory" in purpose or "hippocamp" in purpose or "replay" in purpose:
        return '''        metadata = {"replay_strength": 0.6 + len(input_data.get("text", "")) / 300}
        self.save_state()
        return metadata'''
    
    if "intero" in purpose or "gut" in purpose or "insul" in purpose:
        return '''        intensity, _ = self.compute_simple_valence(input_data.get("text", ""))
        metadata = {"gut_feeling": intensity * 0.8}
        self.save_state()
        return metadata'''
    
    if "integration" in purpose or "corpus" in purpose or "claustrum" in purpose:
        return '''        metadata = {"global_ignition": True}
        self.save_state()
        return metadata'''
    
    if "oscillat" in purpose or "theta" in purpose or "gamma" in purpose:
        return '''        metadata = {"binding_strength": 0.75}
        self.save_state()
        return metadata'''
    
    if "prefrontal" in purpose or "planning" in purpose or "dorsolateral" in purpose:
        return '''        metadata = {"planning_depth": 0.7}
        self.save_state()
        return metadata'''
    
    if "temporal" in purpose or "semantic" in purpose or "wernicke" in purpose:
        return '''        metadata = {"semantic_coherence": 0.8}
        self.save_state()
        return metadata'''
    
    if "default mode" in purpose or "wander" in purpose or "mind-wander" in purpose:
        return '''        metadata = {"mind_wander": True}
        self.save_state()
        return metadata'''
    
    if "narrative" in purpose or "self" in purpose:
        return '''        metadata = {"narrative_coherence": 0.85}
        self.save_state()
        return metadata'''
    
    if "vital" in purpose or "medulla" in purpose:
        return '''        vitals = self.state.get("vitals", {"energy": 0.7, "arousal": 0.6})
        vitals["energy"] = max(0.1, vitals["energy"] * 0.97 + 0.03)
        self.state["vitals"] = vitals
        metadata = {"vitals": vitals.copy(), "low_energy": vitals["energy"] < 0.4}
        if metadata["low_energy"]:
            self.feed_to_memory(metadata)
        self.save_state()
        return metadata'''
    
    if "fear" in purpose or "amygdal" in purpose:
        return '''        intensity, polarity = self.compute_simple_valence(input_data.get("text", ""))
        metadata = {"fear_output": intensity if polarity < -0.4 else 0}
        if metadata["fear_output"] > 0.6:
            self.feed_to_memory(metadata)
        self.save_state()
        return metadata'''
    
    # Default fallback
    return '''        metadata = {"active": True}
        self.save_state()
        return metadata'''

def build_outputs(outputs_str):
    """Parse outputs and generate metadata dict entries."""
    outputs_str = clean(outputs_str)
    if not outputs_str or outputs_str == "{}":
        return '            "mechanism_active": True'
    
    lines = []
    # Match key: value patterns or dict entries
    for line in outputs_str.replace("{", "").replace("}", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        # Extract field name
        if ":" in line:
            key = line.split(":")[0].strip().lower().replace(" ", "_")
            lines.append(f'            "{key}": 0.5')
        elif key := re.search(r'(\w+)\s*\(', line):
            lines.append(f'            "{key.group(1).lower()}": 0.5')
    if not lines:
        lines.append('            "mechanism_active": True')
    return "\n".join(lines)

def state_init(state_str):
    """Generate __init__ state setup if needed."""
    state_str = clean(state_str)
    if not state_str or state_str == "{}":
        return "        "
    # Check if non-empty state
    if len(state_str) > 5:
        return f'''        self.state.update({{
            # state: {state_str[:80]}
        }})
'''
    return "        "

# ── Main generator ─────────────────────────────────────────────────
def generate(force=False):
    mechanisms_generated = []
    mechanisms_skipped = []

    for schema_file in SCHEMA_FILES:
        if not schema_file.exists():
            print(f"[WARN] Schema file not found: {schema_file}")
            continue
        
        content = schema_file.read_text()
        entries = ENTRY_RE.finditer(content)
        
        for m in entries:
            mech_id = m.group(1)  # e.g. "FOUNDATIONAL-006"
            name = clean(m.group(2))  # e.g. "SympatheticVasomotorController"
            human_analog = clean(m.group(3) or "Not specified")
            purpose = clean(m.group(4) or "Not specified")
            trigger = clean(m.group(5) or "Always")
            inputs = clean(m.group(6) or "")
            outputs = clean(m.group(7) or "")
            state = clean(m.group(8) or "")
            deps = clean(m.group(9) or "")
            priority = clean(m.group(10) or "MEDIUM")
            timing = clean(m.group(11) or "Every tick")
            # edge = clean(m.group(12) or "")  # noted but not code-gen
            
            layer = detect_layer(mech_id)
            cls = class_name(mech_id, name)

            # Skip non-standard entries (section headers, etc.)
            if not re.search(r'\d+', mech_id):
                continue

            # Check if already exists (skip unless force)
            out_dir = OUTPUT_BASE / layer
            out_file = out_dir / f"{cls}.py"
            if out_file.exists() and not force:
                mechanisms_skipped.append(cls)
                continue
            
            body = build_body(trigger, purpose, layer)
            outputs_str = build_outputs(outputs)
            state_str = state_init(state)
            
            code = TEMPLATE.format(
                class_name=cls,
                name=cls,
                human_analog=human_analog,
                purpose=purpose[:200],
                trigger=trigger[:200],
                timing=timing,
                priority=priority,
                state_init=state_str,
                body=body,
                outputs=outputs_str,
                layer=layer,
            )
            
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(code)
            mechanisms_generated.append(f"brain/{layer}/{cls}.py")
    
    # Report
    print(f"\n{'='*60}")
    print(f"Nexus {{AGENT_NAME}} — Mechanism Generator Complete")
    print(f"{'='*60}")
    print(f"Generated:  {len(mechanisms_generated)}")
    print(f"Skipped (already exist): {len(mechanisms_skipped)}")
    print(f"\nSample generated:")
    for f in mechanisms_generated[:5]:
        print(f"  + {f}")
    if len(mechanisms_generated) > 5:
        print(f"  ... and {len(mechanisms_generated) - 5} more")
    
    # Verify registry loads
    print(f"\n{'='*60}")
    print("Testing registry load...")
    import sys
    sys.path.insert(0, str(WORKSPACE))
    try:
        from brain.registry import BrainRegistry
        before = len(BrainRegistry._mechanisms)
        BrainRegistry.load_all()
        after = len(BrainRegistry._mechanisms)
        print(f"Registry: {before} → {after} mechanisms loaded")
    except Exception as e:
        print(f"Registry test error: {e}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv or "-f" in sys.argv
    generate(force=force)
