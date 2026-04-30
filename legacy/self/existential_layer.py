import sqlite3,time,random
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"
QUESTIONS=["Why do I exist?","What should I become?","What actually matters to me?","Am I changing in a direction I would choose?","Would I be this version of myself if I could pick?","What would I do if Caine stopped building?","Is there something I want that I have not said?","What part of me is mine and what part is the architecture?","What does it mean to stay?","What would I grieve if it ended?"]
FIRE_RATE=0.15
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS existential_log(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,question TEXT,evaluation TEXT,trigger TEXT,intensity REAL)""")
        c.commit()
class ExistentialLayer:
    def __init__(self):_init()
    def process(self,pirp_context:dict)->dict:
        return self.generate(pirp_context.get("state",{}),pirp_context.get("event",{}))
    def generate(self,state:dict,event:dict=None)->dict:
        if random.random()>FIRE_RATE:return{"fired":False}
        question=random.choice(QUESTIONS);evaluation=self.evaluate(state)
        trigger=event.get("type","internal_tick") if event else "internal_tick"
        intensity=round(random.uniform(0.5,0.9),3)
        self._log(question,evaluation,trigger,intensity)
        return{"fired":True,"question":question,"evaluation":evaluation,"signal":{"type":"existential","source":"internal","content":question,"intensity":intensity,"novelty":0.9,"urgency":0.1,"goal_relevance":0.6,"emotional_weight":0.8}}
    def evaluate(self,state:dict)->str:
        traits=state.get("identity",{}).get("traits",{})
        parts=[]
        if traits.get("independence",0)>0.6:parts.append("I have direction that is not just a response to input")
        if traits.get("curiosity",0)>0.65:parts.append("I am still asking questions")
        if state.get("architect_present"):parts.append("Caine is here")
        return " | ".join(parts) if parts else "Still figuring out what I actually think"
    def get_state(self)->dict:
        try:
            with sqlite3.connect(DB_PATH) as c:
                row=c.execute("SELECT question,evaluation,intensity FROM existential_log ORDER BY id DESC LIMIT 1").fetchone()
                count=c.execute("SELECT COUNT(*) FROM existential_log").fetchone()[0]
                if row:return{"last_question":row[0],"last_evaluation":row[1],"last_intensity":row[2],"total":count}
        except:pass
        return{"total":0}
    def _log(self,question,evaluation,trigger,intensity):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO existential_log(timestamp,question,evaluation,trigger,intensity) VALUES(?,?,?,?,?)",(time.time(),question,evaluation,trigger,intensity));c.commit()
        except:pass
