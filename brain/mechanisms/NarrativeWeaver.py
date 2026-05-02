from brain.base_mechanism import BrainMechanism
import sqlite3,time,json
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS narrative_weaver(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,fragment TEXT,coherence_score REAL,story_length INTEGER)""")
        c.commit()
class NarrativeWeaver(BrainMechanism):
    def __init__(self):
        super().__init__(name="NarrativeWeaver", human_analog="NarrativeWeaver", layer="integration")
        _init();self.story=[];self.coherence_score=0.7
    def process(self,pirp_context:dict)->dict:
        fragments=pirp_context.get("memory_fragments",[])
        event=pirp_context.get("event",{})
        if event.get("type"):fragments.append(str(event.get("type")))
        for f in fragments:self.story.append({"fragment":f,"ts":time.time()})
        self.story=self.story[-50:]
        self.coherence_score=min(1.0,0.5+len(self.story)*0.01)
        self._save(fragments)
        pirp_context["narrative_coherence"]=self.coherence_score
        pirp_context["story_length"]=len(self.story)
        return pirp_context
    def get_state(self)->dict:
        return{"story_length":len(self.story),"coherence_score":round(self.coherence_score,4)}
    def _save(self,fragments):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO narrative_weaver(timestamp,fragment,coherence_score,story_length) VALUES(?,?,?,?)",(time.time(),json.dumps(fragments),self.coherence_score,len(self.story)));c.commit()
        except:pass

    async def tick(self, input_data: dict) -> dict:
        """BrainMechanism adapter — delegates to legacy process(pirp_context)."""
        prior = input_data.get("prior_results", {})
        pirp_context = dict(prior)
        pirp_context["drive_context"] = pirp_context.get("drive_context", {})
        try:
            result = self.process(pirp_context)
        except Exception as e:
            self.state["last_error"] = repr(e)
            return {"error": repr(e)}
        if isinstance(result, dict):
            output = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            output = {"value": result}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try:
            self.persist_state()
        except Exception:
            pass
        return output

