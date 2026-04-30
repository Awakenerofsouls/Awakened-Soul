import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS experience_predictor(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,predicted_success REAL,feedback_count INTEGER)""")
        c.commit()
class ExperiencePredictor:
    def __init__(self):
        _init();self.predicted_success=0.5;self.feedback_history=[]
    def process(self,pirp_context:dict)->dict:
        feedback=pirp_context.get("outcome_feedback",None)
        if feedback is not None:
            self.feedback_history.append(float(feedback));self.feedback_history=self.feedback_history[-30:]
        if self.feedback_history:
            self.predicted_success=sum(self.feedback_history)/len(self.feedback_history)
        self._save()
        pirp_context["predicted_success"]=self.predicted_success
        return pirp_context
    def get_state(self)->dict:
        return{"predicted_success":round(self.predicted_success,4),"feedback_count":len(self.feedback_history)}
    def _save(self):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO experience_predictor(timestamp,predicted_success,feedback_count) VALUES(?,?,?)",(time.time(),self.predicted_success,len(self.feedback_history)));c.commit()
        except:pass
