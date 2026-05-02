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
        c.execute("""CREATE TABLE IF NOT EXISTS adaptive_goal_refiner(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,goal_name TEXT,original_importance REAL,adjusted_importance REAL,feedback REAL)""")
        c.commit()
class AdaptiveGoalRefiner(BrainMechanism):
    def __init__(self):
        super().__init__(name="AdaptiveGoalRefiner", human_analog="AdaptiveGoalRefiner", layer="integration")
        _init();self.refined_goals=[]
    def process(self,pirp_context:dict)->dict:
        goals=pirp_context.get("state",{}).get("goals",[])
        predicted=float(pirp_context.get("predicted_success",0.5))
        self.refined_goals=[]
        for g in goals:
            original=float(g.get("priority",0.5))
            adjusted=round(max(0.1,min(1.0,original*(0.7+predicted*0.6))),4)
            self.refined_goals.append({"name":g.get("name"),"source":g.get("source"),"priority":adjusted,"original_priority":original})
            self._save(str(g.get("name")),original,adjusted,predicted)
        pirp_context["refined_goals"]=self.refined_goals
        return pirp_context
    def get_state(self)->dict:
        return{"refined_goals":self.refined_goals}
    def _save(self,name,original,adjusted,feedback):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO adaptive_goal_refiner(timestamp,goal_name,original_importance,adjusted_importance,feedback) VALUES(?,?,?,?,?)",(time.time(),name,original,adjusted,feedback));c.commit()
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

