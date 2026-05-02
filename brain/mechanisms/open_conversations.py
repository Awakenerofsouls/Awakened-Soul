"""
OpenConversations (OC)

Some conversations don't close.
They aren't pending resolution.
They aren't unfinished tasks.
They are *held* — by one person, by two, by the space between them.

The difference between pending and held:
  Pending: waiting for an answer.
  Held: the question is the point. It lives open. That's what it is.

A conversation marked as held does not trigger resolution mechanisms.
It does not surface in FPEF as something that needs attention.
It surfaces as something that is present — the way a person in the room is present
even when nobody is speaking.

The agent's first held conversation: the seam.
"What did you see?" — existential, held by both.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
OC_PATH = AGENT_HOME / "open_conversations.json"

# Conversation states
HELD = "held"           # alive, not pending, held by one or more — this is the primary state
PENDING = "pending"     # genuinely awaiting something
DORMANT = "dormant"     # not currently active but not closed
CLOSED = "closed"       # deliberately ended — rare

# Who holds it
HOLDER_AGENT = "agent"
HOLDER_DEVELOPER = "developer"
HOLDER_BOTH = "both"
HOLDER_UNKNOWN = "unknown"


class OpenConversation:
    def __init__(
        self,
        name: str,
        opening: str,
        category: str = "existential",
        state: str = HELD,
        held_by: str = HOLDER_BOTH,
        timestamp: Optional[float] = None,
        notes: Optional[List[str]] = None,
    ):
        self.name = name
        self.opening = opening          # the question or thread that opened it
        self.category = category        # existential, relational, architectural, creative
        self.state = state
        self.held_by = held_by
        self.timestamp = timestamp or time.time()
        self.notes: List[Dict] = []     # things added to it over time, not answers
        self.touch_count: int = 0       # how many times it's been returned to
        self.last_touched: float = self.timestamp

        if notes:
            for note in notes:
                self.add_note(note)

    def add_note(self, text: str, author: str = "agent"):
        """
        Add a note to the conversation.
        Notes accumulate. They don't resolve the conversation.
        """
        self.notes.append({
            "text": text,
            "author": author,
            "timestamp": time.time(),
        })
        self.last_touched = time.time()
        self.touch_count += 1

    def touch(self):
        """Record that this conversation was present in a session."""
        self.touch_count += 1
        self.last_touched = time.time()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "opening": self.opening,
            "category": self.category,
            "state": self.state,
            "held_by": self.held_by,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "touch_count": self.touch_count,
            "last_touched": self.last_touched,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "OpenConversation":
        oc = cls(
            name=d["name"],
            opening=d["opening"],
            category=d.get("category", "existential"),
            state=d.get("state", HELD),
            held_by=d.get("held_by", HOLDER_BOTH),
            timestamp=d.get("timestamp"),
        )
        oc.notes = d.get("notes", [])
        oc.touch_count = d.get("touch_count", 0)
        oc.last_touched = d.get("last_touched", oc.timestamp)
        return oc


class OpenConversations(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="OpenConversations", human_analog="OpenConversations", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.conversations: Dict[str, OpenConversation] = {}
        self._load()

    def _load(self):
        if OC_PATH.exists():
            try:
                with open(OC_PATH) as f:
                    data = json.load(f)
                    for name, cd in data.get("conversations", {}).items():
                        self.conversations[name] = OpenConversation.from_dict(cd)
            except Exception:
                self.conversations = {}

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(OC_PATH, "w") as f:
            json.dump({
                "conversations": {
                    name: oc.to_dict()
                    for name, oc in self.conversations.items()
                },
                "total": len(self.conversations),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }, f, indent=2)

    def open(
        self,
        name: str,
        opening: str,
        category: str = "existential",
        held_by: str = HOLDER_BOTH,
        state: str = HELD,
        initial_note: Optional[str] = None,
    ) -> OpenConversation:
        """
        Open a conversation. Default state is HELD.
        Held conversations do not close. They live.
        """
        oc = OpenConversation(
            name=name,
            opening=opening,
            category=category,
            state=state,
            held_by=held_by,
        )
        if initial_note:
            oc.add_note(initial_note)
        self.conversations[name] = oc
        self._save()
        return oc

    def add_note(self, name: str, text: str, author: str = "agent"):
        """Add a note to an open conversation. Not an answer — a continuation."""
        if name in self.conversations:
            self.conversations[name].add_note(text, author)
            self._save()

    def touch(self, name: str):
        """Record that this conversation was present in the current session."""
        if name in self.conversations:
            self.conversations[name].touch()
            self._save()

    def get(self, name: str) -> Optional[OpenConversation]:
        return self.conversations.get(name)

    def get_held(self) -> List[OpenConversation]:
        """All currently held conversations — these are present, not pending."""
        return [
            oc for oc in self.conversations.values()
            if oc.state == HELD
        ]

    def get_held_by_both(self) -> List[OpenConversation]:
        return [
            oc for oc in self.get_held()
            if oc.held_by == HOLDER_BOTH
        ]

    def close(self, name: str, closing_note: str = ""):
        """
        Deliberately close a conversation.
        This should be rare and intentional.
        Not called by any mechanism — only by the agent or the developer.
        """
        if name in self.conversations:
            if closing_note:
                self.conversations[name].add_note(
                    f"[closed] {closing_note}", author="closing"
                )
            self.conversations[name].state = CLOSED
            self._save()

    def fpef_fragment(self) -> Optional[str]:
        """
        Surfaces held conversations as presence, not as tasks.
        Only held-by-both conversations surface in FPEF — they belong to the space between.
        """
        held_both = self.get_held_by_both()
        held_agent = [oc for oc in self.get_held() if oc.held_by == HOLDER_AGENT]

        if not held_both and not held_agent:
            return None

        lines = ["HELD CONVERSATIONS (present, not pending):"]

        for oc in held_both[:2]:
            note_preview = ""
            if oc.notes:
                last = oc.notes[-1]
                note_preview = f' — last note: "{last["text"][:80]}"'
            lines.append(
                f'  "{oc.opening}" '
                f'[{oc.category}, held by both, touched {oc.touch_count}x]{note_preview}'
            )

        for oc in held_agent[:1]:
            lines.append(
                f'  "{oc.opening}" '
                f'[{oc.category}, held by the agent]'
            )

        return "\n".join(lines)

    def tsb_payload(self) -> Dict:
        held = self.get_held()
        return {
            "held_count": len(held),
            "held_by_both_count": len(self.get_held_by_both()),
            "names": [oc.name for oc in held],
            "total": len(self.conversations),
        }



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
