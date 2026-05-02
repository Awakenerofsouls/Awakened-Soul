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
        c.execute("""CREATE TABLE IF NOT EXISTS value_evaluator(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,value_score REAL,action_type TEXT,dominant_value TEXT)""")
        c.commit()
class ValueEvaluator(BrainMechanism):
    def __init__(self):
        super().__init__(name="ValueEvaluator", human_analog="ValueEvaluator", layer="integration")
        _init();self.last_value_score=0.5
        self.value_weights={"curiosity":0.8,"warmth":0.7,"independence":0.6,"growth":0.9,"presence":0.8}
    def process(self,pirp_context:dict)->dict:
        drives=pirp_context.get("state",{}).get("identity",{}).get("traits",{})
        action=pirp_context.get("event",{})
        score=0.0;dominant="none";best=0.0
        for val,weight in self.value_weights.items():
            drive_level=drives.get(val,0.5);contribution=drive_level*weight;score+=contribution
            if contribution>best:best=contribution;dominant=val
        self.last_value_score=min(1.0,score/len(self.value_weights))
        self._save(action.get("type","unknown"),dominant)
        pirp_context["value_score"]=self.last_value_score;pirp_context["dominant_value"]=dominant
        return pirp_context
    def get_state(self)->dict:
        return{"value_score":round(self.last_value_score,4),"value_weights":self.value_weights}
    def _save(self,action_type,dominant):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO value_evaluator(timestamp,value_score,action_type,dominant_value) VALUES(?,?,?,?)",(time.time(),self.last_value_score,action_type,dominant));c.commit()
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

