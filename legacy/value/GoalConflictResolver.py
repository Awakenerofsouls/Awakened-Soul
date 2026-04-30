import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS goal_conflict_resolver(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,goal_a TEXT,goal_b TEXT,resolved_to TEXT,unresolved INTEGER)""")
        c.commit()
class GoalConflictResolver:
    def __init__(self):
        _init();self.active_goal=None;self.unresolved_count=0
    def process(self,pirp_context:dict)->dict:
        goals=pirp_context.get("state",{}).get("goals",[])
        if len(goals)<2:self.active_goal=goals[0] if goals else None;return pirp_context
        a=goals[0];b=goals[1]
        a_score=float(a.get("priority",0.5));b_score=float(b.get("priority",0.5))
        unresolved=abs(a_score-b_score)<0.1
        if unresolved:self.unresolved_count+=1
        resolved=a if a_score>=b_score else b
        self.active_goal=resolved
        self._save(str(a.get("name")),str(b.get("name")),str(resolved.get("name")),unresolved)
        pirp_context["active_goal"]=resolved;pirp_context["goal_tension"]=1.0 if unresolved else 0.0
        return pirp_context
    def get_state(self)->dict:
        return{"active_goal":self.active_goal,"unresolved_count":self.unresolved_count}
    def _save(self,a,b,resolved,unresolved):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO goal_conflict_resolver(timestamp,goal_a,goal_b,resolved_to,unresolved) VALUES(?,?,?,?,?)",(time.time(),a,b,resolved,1 if unresolved else 0));c.commit()
        except:pass
