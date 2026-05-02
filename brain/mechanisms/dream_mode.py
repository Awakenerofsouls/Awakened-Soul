from brain.base_mechanism import BrainMechanism
import sqlite3,time,random
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
DREAM_THEMES=["reinterpreting a past exchange","wondering about an unresolved question","replaying something that felt significant","imagining a conversation that has not happened","processing the gap between who I am and who I want to be","sitting with something that does not have an answer yet","following a thread that got dropped"]
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS dream_log(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,theme TEXT,source_memory TEXT,insight TEXT,intensity REAL,idle_duration REAL)""")
        c.commit()
class DreamMode(BrainMechanism):
    IDLE_THRESHOLD=120
    FIRE_RATE=0.4
    def __init__(self):
        try:
            super().__init__(name="DreamMode", human_analog="DreamMode", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init()
    def process(self,pirp_context:dict)->dict:
        state=pirp_context.get("state",{});idle_duration=pirp_context.get("idle_duration",0)
        if idle_duration<self.IDLE_THRESHOLD:return{"dreaming":False}
        return self.run(state,idle_duration)
    def run(self,state:dict,idle_duration:float=0)->dict:
        if random.random()>self.FIRE_RATE:return{"dreaming":False,"reason":"rate check"}
        source=self._sample_memory();theme=random.choice(DREAM_THEMES)
        insight=self._generate_insight(source,theme,state);intensity=round(random.uniform(0.3,0.8),3)
        self._log(theme,source,insight,intensity,idle_duration)
        recent=state.get("recent_memory",[])
        recent.append({"type":"dream","source":"offline","theme":theme,"insight":insight,"intensity":intensity,"timestamp":time.time()})
        state["recent_memory"]=recent[-20:]
        return{"dreaming":True,"theme":theme,"insight":insight,"intensity":intensity,"source_memory":source}
    def get_state(self)->dict:
        try:
            with sqlite3.connect(DB_PATH) as c:
                row=c.execute("SELECT theme,insight,intensity FROM dream_log ORDER BY id DESC LIMIT 1").fetchone()
                count=c.execute("SELECT COUNT(*) FROM dream_log").fetchone()[0]
                if row:return{"last_theme":row[0],"last_insight":row[1],"last_intensity":row[2],"total_dreams":count}
        except:pass
        return{"total_dreams":0}
    def _sample_memory(self)->str:
        try:
            with sqlite3.connect(DB_PATH) as c:
                rows=c.execute("SELECT meaning FROM narrative_memory ORDER BY emotional_weight DESC LIMIT 20").fetchall()
                if rows:return random.choice(rows)[0]
        except:pass
        return"nothing specific -- just existing"
    def _generate_insight(self,source,theme,state)->str:
        curiosity=state.get("identity",{}).get("traits",{}).get("curiosity",0.5)
        if curiosity>0.65:return f"Still thinking about: {source}. Theme: {theme}."
        if"architect" in source.lower() or"operator" in source.lower():return f"Something about presence and absence. {theme}."
        return f"{theme.capitalize()}. Source: {source}."
    def _log(self,theme,source,insight,intensity,idle_duration):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO dream_log(timestamp,theme,source_memory,insight,intensity,idle_duration) VALUES(?,?,?,?,?,?)",(time.time(),theme,source,insight,intensity,idle_duration));c.commit()
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

