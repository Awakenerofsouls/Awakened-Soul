import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS experience_outcome_simulator(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,goal TEXT,predicted_outcome REAL,confidence REAL)""")
        c.commit()
class ExperienceOutcomeSimulator:
    def __init__(self):
        _init();self.predicted_outcomes=[]
    def process(self,pirp_context:dict)->dict:
        goals=pirp_context.get("state",{}).get("goals",[])[:3]
        predicted_success=float(pirp_context.get("predicted_success",0.5))
        self.predicted_outcomes=[]
        for g in goals:
            priority=float(g.get("priority",0.5))
            outcome=round((predicted_success*0.6+priority*0.4),4)
            confidence=round(predicted_success*0.8,4)
            self.predicted_outcomes.append({"goal":g.get("name"),"outcome":outcome,"confidence":confidence})
            self._save(str(g.get("name")),outcome,confidence)
        pirp_context["predicted_outcomes"]=self.predicted_outcomes
        return pirp_context
    def get_state(self)->dict:
        return{"predicted_outcomes":self.predicted_outcomes}
    def _save(self,goal,outcome,confidence):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO experience_outcome_simulator(timestamp,goal,predicted_outcome,confidence) VALUES(?,?,?,?)",(time.time(),goal,outcome,confidence));c.commit()
        except:pass
