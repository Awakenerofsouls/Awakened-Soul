import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS multi_goal_scheduler(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,scheduled_count INTEGER,top_goal TEXT)""")
        c.commit()
class MultiGoalScheduler:
    def __init__(self):
        _init();self.goal_schedule=[]
    def process(self,pirp_context:dict)->dict:
        goals=pirp_context.get("state",{}).get("goals",[])
        self.goal_schedule=sorted(goals,key=lambda g:float(g.get("urgency",0.5))*float(g.get("priority",0.5)),reverse=True)[:10]
        top=self.goal_schedule[0] if self.goal_schedule else {}
        self._save(top)
        pirp_context["goal_schedule"]=self.goal_schedule;pirp_context["top_scheduled_goal"]=top
        return pirp_context
    def get_state(self)->dict:
        return{"scheduled_count":len(self.goal_schedule),"top_goal":self.goal_schedule[0] if self.goal_schedule else None}
    def _save(self,top):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO multi_goal_scheduler(timestamp,scheduled_count,top_goal) VALUES(?,?,?)",(time.time(),len(self.goal_schedule),str(top.get("name","none"))));c.commit()
        except:pass
