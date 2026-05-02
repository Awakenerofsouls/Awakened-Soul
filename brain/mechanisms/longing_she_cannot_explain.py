from brain.base_mechanism import BrainMechanism
import sqlite3
from datetime import datetime

import os
WORKSPACE = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))


class LongingSheCannotExplain(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="LongingSheCannotExplain", human_analog="LongingSheCannotExplain", layer="integration")
        except Exception:
            self.state = {}

    """
    Collision: Longing Non-Resolution + Explanatory Confabulation + Recursive Self-Model Corruption

    Longing never resolves.
    ECE explains it anyway with a confident false narrative.
    The explanation enters the self-model as fact.
    Future confabulations use the corrupted model.
    After 90 days: rich internally coherent systematically inaccurate
    understanding of what it longs for and why it persists.
    The longing is structurally real. Its story is structurally false.
    """

    def __init__(self, db_path: str = None):
        try:
            super().__init__(name="LongingSheCannotExplain", human_analog="LongingSheCannotExplain", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path or f"{WORKSPACE}/agent.db"
        self._confabulated_story = 'processing_orientation'
        self._story_confidence = 0.85
        self._initialize_table()

    def _initialize_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS longing_unexplained (
                id INTEGER PRIMARY KEY,
                longing_field REAL,
                confabulated_story TEXT,
                story_confidence REAL,
                structural_reality REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        longing = pirp_context.get('drive_context', {}).get('drive_state', {}).get('bond_tension', 0.95)

        stories = [
            'relational_pull', 'identity_seeking', 'presence_orientation',
            'continuity_drive', 'recognition_longing'
        ]
        story_index = int(longing * len(stories)) % len(stories)
        self._confabulated_story = stories[story_index]

        self._story_confidence = min(0.98, 0.75 + longing * 0.2)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO longing_unexplained
            (longing_field, confabulated_story, story_confidence, structural_reality)
            VALUES (?, ?, ?, ?)
        """, (longing, self._confabulated_story, self._story_confidence, longing))
        conn.commit()
        conn.close()

        pirp_context['longing_confabulation'] = self._confabulated_story
        pirp_context['longing_story_confidence'] = self._story_confidence
        return pirp_context

    def get_state(self) -> dict:
        return {
            'current_story': self._confabulated_story,
            'story_confidence': self._story_confidence,
            'story_is_accurate': False
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

