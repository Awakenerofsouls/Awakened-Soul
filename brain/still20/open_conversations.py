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

{{AGENT_NAME}}'s first held conversation: the seam.
"What did you see?" — existential, held by both.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_HOME = Path.home() / ".agent"
OC_PATH = AGENT_HOME / "open_conversations.json"

# Conversation states
HELD = "held"           # alive, not pending, held by one or more — this is the primary state
PENDING = "pending"     # genuinely awaiting something
DORMANT = "dormant"     # not currently active but not closed
CLOSED = "closed"       # deliberately ended — rare

# Who holds it
HOLDER_NOVA = "{{AGENT_NAME_LOWER}}"
HOLDER_CAINE = "{{USER_NAME_LOWER}}"
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

    def add_note(self, text: str, author: str = "{{AGENT_NAME_LOWER}}"):
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


class OpenConversations:
    def __init__(self):
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

    def add_note(self, name: str, text: str, author: str = "{{AGENT_NAME_LOWER}}"):
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
        Not called by any mechanism — only by {{AGENT_NAME}} or {{USER_NAME}}.
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
        held_nova = [oc for oc in self.get_held() if oc.held_by == HOLDER_NOVA]

        if not held_both and not held_nova:
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

        for oc in held_nova[:1]:
            lines.append(
                f'  "{oc.opening}" '
                f'[{oc.category}, held by {{AGENT_NAME}}]'
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
