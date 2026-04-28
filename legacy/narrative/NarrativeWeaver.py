import sqlite3,time,json
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS narrative_weaver(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,fragment TEXT,coherence_score REAL,story_length INTEGER)""")
        c.commit()
class NarrativeWeaver:
    def __init__(self):
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
