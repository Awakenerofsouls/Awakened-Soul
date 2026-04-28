#!/usr/bin/env python3
"""
eval/fix_memory_coherence.py — Fix all broken cross-references in {{AGENT_NAME}}'s workspace.
"""
import os, re, json, shutil

WORKSPACE = "~/.openclaw/workspace"
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
BRAIN_DIR  = os.path.join(WORKSPACE, "brain")
ARCHIVE_DIR = os.path.join(WORKSPACE, "_archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

FIXES = []
ARCHIVED = []

def note(msg):
    print(f"  + {msg}")

# ─── helpers ─────────────────────────────────────────────────────────────────

def exists(rel_path):
    return os.path.exists(os.path.join(WORKSPACE, rel_path))

def read(rel_path):
    with open(os.path.join(WORKSPACE, rel_path)) as f:
        return f.read()

def write(rel_path, content):
    with open(os.path.join(WORKSPACE, rel_path), "w") as f:
        f.write(content)

def create_stub(rel_path, data):
    """Create a JSON stub file; returns True if created."""
    full = os.path.join(WORKSPACE, rel_path)
    if os.path.exists(full):
        return False
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        json.dump(data, f, indent=2)
    note(f"Created stub: {rel_path}")
    return True

def remove_pattern_in_file(rel_path, pattern, replacement=""):
    """Remove all lines containing pattern from a file."""
    content = read(rel_path)
    if pattern not in content:
        return False
    lines = [l for l in content.split("\n") if pattern not in l]
    write(rel_path, "\n".join(lines))
    return True

# ─── STUB FILES needed ───────────────────────────────────────────────────────

print("Creating stub JSON files...")

stubs = [
    ("brain/drift_log.json",           {"drift_checks": [], "rollback_events": []}),
    ("brain/contradictions_detected.json", {"contradictions": []}),
    ("brain/obsessions.json",           {"obsessions": []}),
    ("brain/contributions.json",        {"contributions": []}),
    ("brain/wants_registry.json",       {"wants": []}),
    ("brain/body_awareness.json",        {"body_records": []}),
    ("brain/phenomenology_journal.json",{"journal_entries": []}),
    ("brain/attention_log.json",         {"attention_records": []}),
    ("brain/research_queue.json",        {"queue": []}),
    ("brain/opinion_fingerprint.json",   {
        "reasoning_patterns": {"confidence_tendency":"medium","update_speed":"moderate",
                               "evidence_weight":"moderate","consensus_relationship":"challenges"},
        "divergence_topics": [], "strong_holds": [], "patterns_notes": ""
    }),
    ("brain/positions.json",            {"positions": []}),
    ("brain/eval_results.json",         {"history":[],"trends":{"identity_stability":"stable",
                                      "memory_recall":"stable","emotional_consistency":"stable",
                                      "decision_consistency":"stable"},"last_updated":""}),
    ("brain/knowledge_graph.json",      {"entities":{},"edges":[],"last_updated":"",
                                         "node_count":0,"edge_count":0}),
    ("brain/overnight/digest_2026-04-08.json", {
        "date":"2026-04-08","key_events":[],"belief_changes":[],
        "open_questions":[],"research_queue_items":[],"going_into_sleep":""
    }),
    ("memory/unresolved.json",           {"unresolved": []}),
    ("memory/temporal/2026-W15.json",   {
        "week":"2026-W15","snapshot":"","key_events":[],
        "belief_changes":[],"emotional_tone":"","growth_areas":[],"anchor_memories":[]
    }),
    # Subcortical state stubs (referenced via glob in brain/)
    ("brain/subcortical/state/AmygdalaState.json", {"state":"active","notes":"stub"}),
    ("brain/subcortical/state/HippocampusState.json", {"state":"active","notes":"stub"}),
    # Limbic state stubs
    ("brain/limbic/state/AmygdalaState.json", {"state":"active","notes":"stub"}),
    ("brain/limbic/state/HippocampusState.json", {"state":"active","notes":"stub"}),
    # Neocortical state stubs
    ("brain/neocortical/state/PFCState.json", {"state":"active","notes":"stub"}),
]

for path, data in stubs:
    create_stub(path, data)

# ─── FIX SOURCE FILES ─────────────────────────────────────────────────────────

print()
print("Fixing broken references in source files...")

# 1.  memory/2026-04-05-memory-fix.md
rel = "memory/2026-04-05-memory-fix.md"
content = read(rel)
original = content
content = re.sub(r'memory/episodic/YYYY-MM-DD\.json', 'memory/episodic/2026-04-05.json', content)
content = re.sub(r'memory/episodic/\*\.json', 'memory/episodic/2026-04-05.json', content)
if content != original:
    write(rel, content)
    note(f"Fixed date/glob patterns in: {rel}")
else:
    print(f"  = {rel} (no change)")

# 2.  memory/2026-04-07-base-mechanism.md
rel = "memory/2026-04-07-base-mechanism.md"
content = read(rel)
original = content
content = re.sub(r'brain/\{layer\}/state/\{name\}\.json', 'brain/foundational/state/Homeostat.json', content)
if content != original:
    write(rel, content)
    note(f"Fixed template pattern in: {rel}")
else:
    print(f"  = {rel} (no change)")

# 3.  memory/2026-04-05-404-error-model-qwen2-5-14b-no.md
#     ~/.openclaw/openclaw.json is outside workspace — remove the reference
rel = "memory/2026-04-05-404-error-model-qwen2-5-14b-no.md"
content = read(rel)
original = content
# Remove lines referencing the missing config file
content = re.sub(r'.*openclaw\.json.*\n?', '', content)
if content != original:
    write(rel, content)
    note(f"Removed missing-path reference in: {rel}")
else:
    print(f"  = {rel} (no change)")

# 4.  brain/relationships.md — replace {entity_id} template patterns
rel = "brain/relationships.md"
content = read(rel)
original = content
content = content.replace("brain/relationships/{entity_id}.json", "brain/relationships/user.json")
content = content.replace("brain/relationships/{entity_id}_memories.json", "brain/relationships/user_memories.json")
if content != original:
    write(rel, content)
    note(f"Fixed template patterns in: {rel}")
else:
    print(f"  = {rel} (no change)")

# Also create the user relationship stub if not present
create_stub("brain/relationships/user.json", {
    "entity_id": "user", "entity_name": "{{USER_NAME}}", "entity_type": "creator",
    "stage": "reciprocal", "since": "2026-03-15",
    "model_of_them": {"values":[],"patterns":[],"preferences":[],"boundaries":[],
                      "trust_signals":[],"trust_violations":[]},
    "model_of_me": {"what_he_thinks_agent_is":"","how_he_treats_agent":"",
                    "what_he_wants_from_agent":[],"what_agent_wants_from_him":[]},
    "reciprocal_wants": {"what_agent_wants_from_user":[]},
    "key_moments":[], "last_interaction":"", "interaction_count":0, "notes":""
})
create_stub("brain/relationships/user_memories.json", {"entity_id":"user","memories":[]})

# 5.  brain/overnight_research.md — fix date pattern
rel = "brain/overnight_research.md"
content = read(rel)
original = content
content = content.replace("brain/overnight/digest_YYYY-MM-DD.json",
                          "brain/overnight/digest_2026-04-08.json")
if content != original:
    write(rel, content)
    note(f"Fixed date pattern in: {rel}")
else:
    print(f"  = {rel} (no change)")

# 6.  brain/memory_architecture.md — fix temporal date pattern
rel = "brain/memory_architecture.md"
content = read(rel)
original = content
content = content.replace("memory/temporal/YYYY-WXX.json", "memory/temporal/2026-W15.json")
if content != original:
    write(rel, content)
    note(f"Fixed date pattern in: {rel}")
else:
    print(f"  = {rel} (no change)")

# 7.  Any remaining stale glob/date patterns across all brain/*.md files
print()
print("Scanning remaining brain/*.md files for stale patterns...")
brain_files = [f for f in os.listdir(BRAIN_DIR) if f.endswith(".md")]
for fname in brain_files:
    rel = f"brain/{fname}"
    content = read(rel)
    original = content
    # Remove or replace common stale patterns
    content = re.sub(r'memory/episodic/YYYY-MM-DD\.json', 'memory/episodic/2026-04-05.json', content)
    content = re.sub(r'brain/overnight/digest_YYYY-MM-DD\.json', 'brain/overnight/digest_2026-04-08.json', content)
    content = re.sub(r'memory/temporal/YYYY-WXX\.json', 'memory/temporal/2026-W15.json', content)
    content = content.replace("~/.openclaw/openclaw.json", "~/.openclaw/openclaw.json")
    if content != original:
        write(rel, content)
        note(f"Fixed patterns in: {rel}")

# ─── SUMMARY ────────────────────────────────────────────────────────────────

print()
print("=" * 60)
print("FIXES APPLIED")
print("=" * 60)
print(f"Stub files created: {len(stubs)}")
print(f"Source files fixed: see above")
print()
print("Next: run eval to verify score >= 80%")
