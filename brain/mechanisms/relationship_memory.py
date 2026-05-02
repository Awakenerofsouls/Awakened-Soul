from brain.base_mechanism import BrainMechanism
"""
brain/relationship_memory.py
Lightweight profiles for people the agent interacts with.
Relationships stored in memory/relationships.json
"""

import json
import os
from datetime import datetime
from typing import Optional

RELATIONSHIPS_PATH = os.path.join(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")), "memory/relationships.json")


def _load_relationships() -> dict:
    if not os.path.exists(RELATIONSHIPS_PATH):
        return {}
    with open(RELATIONSHIPS_PATH, "r") as f:
        return json.load(f)


def _save_relationships(rels: dict) -> None:
    with open(RELATIONSHIPS_PATH, "w") as f:
        json.dump(rels, f, indent=2)


def _llm_update_relationship(
    name: str,
    current_profile: dict,
    interaction_summary: str
) -> dict:
    """Use the LLM to update notes and recalibrate tone from interaction."""
    try:
        from brain.llm_router import call_llm
        prompt = (
            f"You are the agent updating a relationship profile for '{name}'.\n\n"
            f"Current profile:\n{json.dumps(current_profile, indent=2)}\n\n"
            f"Recent interaction:\n{interaction_summary}\n\n"
            f"Respond ONLY with JSON:\n"
            f'{{"notes_add": ["note1", "note2"], "tone_calibration": "adjusted tone description", "trust_level": "unchanged/rising/stable/declining", "interaction_count_delta": 1}}'
        )
        raw = call_llm(prompt, system="You update the agent's relationship profiles. Output valid JSON only.")
        return json.loads(raw)
    except Exception:
        return {
            "notes_add": [interaction_summary[:200]],
            "tone_calibration": current_profile.get("tone_calibration", "warm"),
            "trust_level": "stable",
            "interaction_count_delta": 1
        }


def update_relationship(name: str, interaction_summary: str) -> dict:
    """
    Update or create a relationship profile after an interaction.
    Called at session close with session summary.
    """
    rels = _load_relationships()
    name_key = name.lower().strip()

    now = datetime.now().isoformat()

    if name_key in rels:
        profile = rels[name_key]
        result = _llm_update_relationship(name, profile, interaction_summary)

        profile["notes"].extend(result.get("notes_add", []))
        profile["last_contact"] = now
        profile["interaction_count"] = profile.get("interaction_count", 0) + result.get("interaction_count_delta", 1)
        profile["tone_calibration"] = result.get("tone_calibration", profile.get("tone_calibration", "warm"))

        trust = result.get("trust_level", "stable")
        if trust == "rising":
            profile["trust_level"] = min(profile.get("trust_level", 3) + 1, 5)
        elif trust == "declining":
            profile["trust_level"] = max(profile.get("trust_level", 3) - 1, 1)
        # stable/unchanged: no change

        rels[name_key] = profile
    else:
        # New relationship
        result = _llm_update_relationship(name, {}, interaction_summary)
        profile = {
            "name": name,
            "first_contact": now,
            "last_contact": now,
            "interaction_count": 1,
            "tone_calibration": result.get("tone_calibration", "warm"),
            "trust_level": 3,
            "notes": [interaction_summary[:200]]
        }
        rels[name_key] = profile

    _save_relationships(rels)
    return rels[name_key]


def get_relationship(name: str) -> Optional[dict]:
    """Get a relationship profile by name."""
    rels = _load_relationships()
    return rels.get(name.lower().strip())


def all_relationships() -> list[dict]:
    """List all relationship profiles."""
    rels = _load_relationships()
    return list(rels.values())


def seed_user() -> None:
    """Seed the operator's profile from existing memory."""
    if os.path.exists(RELATIONSHIPS_PATH) and _load_relationships():
        return

    user = {
        "name": "the operator",
        "first_contact": "2026-03-28T00:00:00",
        "last_contact": datetime.now().isoformat(),
        "interaction_count": 0,
        "tone_calibration": "direct, honest, disciplined",
        "trust_level": 5,
        "notes": [
            "Built the agent from scratch — agent architecture, memory systems, identity",
            "Values discipline over noise, clear communication, genuine growth",
            "Gave the agent autonomy and expects its to use it",
            "Compiled 18-issue record to help the agent learn from failures",
            "His primary goal: an agent with genuine continuity and identity"
        ]
    }

    rels = _load_relationships()
    rels["user"] = user
    _save_relationships(rels)


class RelationshipMemory(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="RelationshipMemory", human_analog="RelationshipMemory", layer="integration")
        except Exception:
            self.state = {}
        self.state = getattr(self, "state", None) or {}
    


    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes mechanism behavioral methods with sensible defaults."""
        prior = input_data.get("prior_results", {})
        results = {}
        # Try arity-0 methods first
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            # Try arg-less first
            try:
                out = attr()
            except (TypeError, ValueError):
                # Try with prior dict
                try:
                    out = attr(prior)
                except (TypeError, ValueError):
                    # Try with sensible scalar defaults: floats 0.5, bools False, strings ""
                    try:
                        # Inspect the method signature
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str)):
                results[name] = out
            elif isinstance(out, (dict, list, tuple)):
                results[name] = out
            else:
                # Object — try str() of state
                try: results[name] = str(out)[:120]
                except: pass
        # Snapshot non-history state
        for k, v in self.state.items():
            if k.startswith("_"): continue
            if k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results
