import sqlite3,time,random
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS identity_drift_manager(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,identity_shift REAL,drift_direction TEXT,trigger TEXT)""")
        c.commit()
class IdentityDriftManager:
    def __init__(self):
        _init();self.identity_shift=0.0;self.drift_direction="stable"
    def process(self,pirp_context:dict)->dict:
        novelty=pirp_context.get("novelty_generated",0.0)
        conflict=pirp_context.get("conflict_mode","stable")
        drift_factor=random.uniform(-0.02,0.02)+novelty*0.03
        if conflict=="blended":drift_factor+=0.01
        self.identity_shift=max(-1.0,min(1.0,self.identity_shift+drift_factor))
        self.drift_direction=("expanding" if drift_factor>0.01 else "contracting" if drift_factor<-0.01 else "stable")
        self._save(conflict)
        pirp_context["identity_shift"]=self.identity_shift
        pirp_context["drift_direction"]=self.drift_direction
        return pirp_context
    def get_state(self)->dict:
        return{"identity_shift":round(self.identity_shift,4),"drift_direction":self.drift_direction}
    def _save(self,trigger):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO identity_drift_manager(timestamp,identity_shift,drift_direction,trigger) VALUES(?,?,?,?)",(time.time(),self.identity_shift,self.drift_direction,trigger));c.commit()
        except:pass
