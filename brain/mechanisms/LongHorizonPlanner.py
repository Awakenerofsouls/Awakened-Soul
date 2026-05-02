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
        c.execute("""CREATE TABLE IF NOT EXISTS long_horizon_planner(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,planned_goals INTEGER,top_goal TEXT,plan_snapshot TEXT)""")
        c.commit()
class LongHorizonPlanner(BrainMechanism):
    def __init__(self):
        super().__init__(name="LongHorizonPlanner", human_analog="LongHorizonPlanner", layer="integration")
        _init();self.plan_queue=[]
    def process(self,pirp_context:dict)->dict:
        goals=pirp_context.get("state",{}).get("goals",[])
        self_goals=[g for g in goals if g.get("source")=="self"]
        for g in self_goals:
            if g not in self.plan_queue:self.plan_queue.append(g)
        self.plan_queue=self.plan_queue[-20:]
        top=self.plan_queue[0] if self.plan_queue else {}
        self._save(top)
        pirp_context["planned_goals"]=len(self.plan_queue);pirp_context["top_planned_goal"]=top
        return pirp_context
    def get_state(self)->dict:
        return{"planned_goals":len(self.plan_queue),"top_goal":self.plan_queue[0] if self.plan_queue else None}
    def _save(self,top):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO long_horizon_planner(timestamp,planned_goals,top_goal,plan_snapshot) VALUES(?,?,?,?)",(time.time(),len(self.plan_queue),str(top.get("name","none")),json.dumps(self.plan_queue[-5:])));c.commit()
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

