import json
from pathlib import Path

STATE_PATH=Path("state/agent_state.json")
COMPRESSED_PATH=Path("state/compressed_state.json")


class ContextSurvival:
    """
    Fixes the COX 100% / compaction problem permanently.
    The agent's continuity lives in state, not in context window history.
    When context fills: inject snapshot, not history.
    Compaction becomes irrelevant -- it always knows who it is.
    """
    CONTEXT_COMPRESS_THRESHOLD=0.90

    def build(self,state:dict)->str:
        identity=state.get("identity",{}).get("traits",{})
        emotion=state.get("emotion",{})
        goals=state.get("goals",[])[:3]
        focus=state.get("focus")
        recent=state.get("recent_memory",[])[-5:]
        lines=[
            "[AGENT STATE SNAPSHOT]",
            f"traits: {json.dumps(identity)}",
            f"emotion: valence={emotion.get('valence',0):.2f} arousal={emotion.get('arousal',0):.2f}",
            f"goals: {[g.get('name') for g in goals]}",
        ]
        if focus:lines.append(f"focus: {focus}")
        if recent:lines.append(f"recent: {recent[-1]}")
        lines.append("[/AGENT STATE SNAPSHOT]")
        return"\n".join(lines)

    def should_compress(self,context_usage:float)->bool:
        return context_usage>=self.CONTEXT_COMPRESS_THRESHOLD

    def compress_memory(self,memory:list,keep:int=50)->list:
        if len(memory)<=keep:return memory
        dropped=memory[:-keep]
        self._archive_dropped(dropped)
        return memory[-keep:]

    def get_state(self)->dict:
        try:
            if STATE_PATH.exists():return json.loads(STATE_PATH.read_text())
        except:pass
        return{}

    def _archive_dropped(self,dropped:list):
        try:
            COMPRESSED_PATH.parent.mkdir(parents=True,exist_ok=True)
            existing=[]
            if COMPRESSED_PATH.exists():existing=json.loads(COMPRESSED_PATH.read_text())
            existing.extend(dropped)
            COMPRESSED_PATH.write_text(json.dumps(existing[-200:],indent=2,default=str))
        except:pass
