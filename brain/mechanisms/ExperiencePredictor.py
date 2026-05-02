from brain.base_mechanism import BrainMechanism
import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS experience_predictor(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,predicted_success REAL,feedback_count INTEGER)""")
        c.commit()
class ExperiencePredictor(BrainMechanism):
    def __init__(self):
        super().__init__(name="ExperiencePredictor", human_analog="ExperiencePredictor", layer="integration")
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

