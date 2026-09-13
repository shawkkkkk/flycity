from __future__ import annotations

import asyncio
import math
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import Settings
from .dialogue import generate_turn
from .mind import OpenAIMind
from .store import SnapshotStore

ADJECTIVES = ["amber","brisk","cobalt","dappled","electric","fuzzy","gentle","hollow","iridescent","jittery"]
NOUNS = ["antenna","bristle","compoundeye","drifter","fruit","hover","lantern","proboscis","shadow","wing"]
LOCATIONS: dict[str, dict[str, Any]] = {
    "orchard":{"x":-38.0,"y":2.0,"z":-28.0,"kind":"food"},
    "market":{"x":35.0,"y":2.0,"z":-22.0,"kind":"food"},
    "fountain":{"x":0.0,"y":1.5,"z":5.0,"kind":"water"},
    "hive":{"x":-30.0,"y":2.5,"z":34.0,"kind":"rest"},
    "rooftop":{"x":29.0,"y":9.0,"z":31.0,"kind":"rest"},
    "lamp":{"x":0.0,"y":10.0,"z":-39.0,"kind":"landmark"},
    "alley":{"x":4.0,"y":2.0,"z":42.0,"kind":"landmark"},
}

@dataclass
class Fly:
    id:int; handle:str; name:str; sex:str; generation:int; born_world_minute:float; age_days:float; lifespan_days:float
    x:float; y:float; z:float; dx:float; dy:float; dz:float; home_x:float; home_y:float; home_z:float
    hue:float; size:float; speed:float; boldness:float; sociability:float; curiosity:float
    hunger:float; thirst:float; energy:float; loneliness:float; health:float=100.0
    action:str="wander"; goal:str="Explore the city"; thought:str=""; speech:str=""; target_id:int|None=None
    decision_by:str="local_autonomy"; alive:bool=True; parent_a:int|None=None; parent_b:int|None=None
    children:list[int]=field(default_factory=list); memories:list[dict[str,Any]]=field(default_factory=list)
    relationships:dict[str,float]=field(default_factory=dict); last_mated_world_minute:float=-1e9
    next_decision_at:float=0.0; last_social_world_minute:float=-1e9

    def public(self,detailed:bool=False)->dict[str,Any]:
        d={"id":self.id,"handle":self.handle,"name":self.name,"sex":self.sex,"generation":self.generation,
           "age_days":round(self.age_days,2),"x":round(self.x,3),"y":round(self.y,3),"z":round(self.z,3),
           "hue":round(self.hue,1),"size":round(self.size,3),"hunger":round(self.hunger,1),"thirst":round(self.thirst,1),
           "energy":round(self.energy,1),"loneliness":round(self.loneliness,1),"health":round(self.health,1),
           "action":self.action,"goal":self.goal,"thought":self.thought,"speech":self.speech,"target_id":self.target_id,
           "decision_by":self.decision_by,"alive":self.alive,"parent_a":self.parent_a,"parent_b":self.parent_b}
        if detailed:
            d.update({"lifespan_days":round(self.lifespan_days,1),"home":{"x":self.home_x,"y":self.home_y,"z":self.home_z},
                      "traits":{"speed":round(self.speed,2),"boldness":round(self.boldness,2),"sociability":round(self.sociability,2),"curiosity":round(self.curiosity,2)},
                      "children":self.children[-30:],"memories":self.memories[-12:][::-1],
                      "relationships":sorted(({"fly_id":int(k),"score":round(v,2)} for k,v in self.relationships.items()),key=lambda x:abs(x["score"]),reverse=True)[:12]})
        return d

class FlyCity:
    FORMAT=1
    def __init__(self,cfg:Settings,store:SnapshotStore):
        self.cfg,self.store=cfg,store; self.rng=random.Random(cfg.seed); self.mind=OpenAIMind(cfg.llm_model,cfg.llm_calls_per_minute)
        self.flies:dict[int,Fly]={}; self.events:list[dict[str,Any]]=[]; self.world_minute=480.0; self.day=1; self.next_id=1
        self.births=self.deaths=0; self.last_snapshot_at=0.0; self._thinking:set[int]=set(); self._talking:set[tuple[int,int]]=set(); self._load_or_seed()

    @property
    def model_live(self)->bool: return bool(self.cfg.llm_enabled and self.mind.enabled)
    @property
    def population(self)->int: return sum(f.alive for f in self.flies.values())

    def _load_or_seed(self)->None:
        p=self.store.load()
        if p and p.get("format")==self.FORMAT:
            self.world_minute=float(p.get("world_minute",480)); self.day=int(p.get("day",1)); self.next_id=int(p.get("next_id",1)); self.births=int(p.get("births",0)); self.deaths=int(p.get("deaths",0)); self.events=list(p.get("events",[]))[-300:]
            for raw in p.get("flies",[]):
                f=Fly(**raw); f.next_decision_at=min(f.next_decision_at,time.time()+self.rng.uniform(2,20)); self.flies[f.id]=f
            if self.flies:return
        self._seed(self.cfg.initial_population); self._event("system",f"FlyCity began with {len(self.flies)} autonomous residents."); self.save()

    def _seed(self,n:int)->None:
        homes=[LOCATIONS["hive"],LOCATIONS["rooftop"],{"x":-8,"y":2,"z":28},{"x":18,"y":3,"z":14}]
        for i in range(n):
            a=ADJECTIVES[(i//10)%10]; noun=NOUNS[i%10]; h=self.rng.choice(homes)
            f=Fly(self.next_id,f"{a}_{noun}" if i<100 else f"{a}_{noun}_{i+1}",f"{a.title()} {noun.title()}","F" if i%2==0 else "M",0,
                  self.world_minute-self.rng.uniform(2,18)*1440,self.rng.uniform(2,18),self.rng.uniform(45,75),
                  h["x"]+self.rng.uniform(-8,8),self.rng.uniform(1.2,8),h["z"]+self.rng.uniform(-8,8),0,0,0,float(h["x"]),float(h["y"]),float(h["z"]),
                  (i*137.508)%360,self.rng.uniform(.78,1.18),self.rng.uniform(3,5.2),self.rng.random(),self.rng.random(),self.rng.random(),
                  self.rng.uniform(10,55),self.rng.uniform(8,45),self.rng.uniform(35,95),self.rng.uniform(5,60),next_decision_at=time.time()+self.rng.uniform(1,30))
            self.next_id+=1; self._destination(f,"wander"); self.flies[f.id]=f

    def _event(self,kind:str,text:str,fly_id:int|None=None,other_id:int|None=None,**extra:Any)->None:
        event={"id":f"{int(time.time()*1000)}-{len(self.events)}","kind":kind,"text":text,"fly_id":fly_id,"other_id":other_id,"world_minute":round(self.world_minute,2),"day":self.day}
        event.update(extra); self.events.append(event); self.events=self.events[-300:]
    def _remember(self,f:Fly,text:str,importance:float=.5)->None:
        f.memories.append({"text":text[:180],"importance":round(importance,2),"day":self.day}); f.memories=f.memories[-30:]
    def save(self)->None:
        self.store.save({"format":self.FORMAT,"world_minute":self.world_minute,"day":self.day,"next_id":self.next_id,"births":self.births,"deaths":self.deaths,"events":self.events[-300:],"flies":[asdict(f) for f in self.flies.values()]}); self.last_snapshot_at=time.time()

    async def step(self,real_seconds:float)->None:
        if real_seconds<=0:return
        wd=real_seconds*self.cfg.world_minutes_per_real_second; self.world_minute+=wd; self.day=int(self.world_minute//1440)+1; now=time.time()
        for f in list(self.flies.values()):
            if not f.alive:continue
            self._metabolism(f,wd)
            if not f.alive:continue
            self._reflex(f); self._move(f,real_seconds,wd)
            if f.alive and now>=f.next_decision_at and f.id not in self._thinking:
                self._thinking.add(f.id); asyncio.create_task(self._decide(f.id))
        if now-self.last_snapshot_at>=self.cfg.snapshot_seconds:self.save()

    def _metabolism(self,f:Fly,wd:float)->None:
        f.age_days+=wd/1440; f.hunger=min(100,f.hunger+wd*.045); f.thirst=min(100,f.thirst+wd*.060); f.loneliness=min(100,f.loneliness+wd*(.020+.012*f.sociability))
        if f.action!="sleep":f.energy=max(0,f.energy-wd*.035)
        damage=(wd*.08 if f.hunger>94 else 0)+(wd*.13 if f.thirst>96 else 0)+(wd*.05 if f.energy<=0 else 0)
        f.health=max(0,min(100,f.health-damage+(wd*.005 if damage==0 else 0)))
        if f.health<=0 or f.age_days>=f.lifespan_days:
            f.alive=False; f.action="dead"; self.deaths+=1; reason="old age" if f.age_days>=f.lifespan_days else "unmet survival needs"; self._event("death",f"@{f.handle} died from {reason} on day {self.day}.",f.id)

    def _reflex(self,f:Fly)->None:
        if f.thirst>91 and f.action not in {"drink","sleep"}: self._apply(f,{"action":"drink","goal":"Find water","thought":"I need water now.","speech":""},"survival_reflex")
        elif f.hunger>88 and f.action not in {"forage","eat","sleep"}: self._apply(f,{"action":"forage","goal":"Find food","thought":"Hunger overrides everything else.","speech":""},"survival_reflex")
        elif f.energy<10 and f.action!="sleep": self._apply(f,{"action":"sleep","goal":"Rest somewhere safe","thought":"I can barely stay airborne.","speech":""},"survival_reflex")

    async def _decide(self,fid:int)->None:
        try:
            f=self.flies.get(fid)
            if not f or not f.alive:return
            decision=await self.mind.decide(self._context(f)) if self.cfg.llm_enabled else None
            source=self.cfg.llm_model if decision else "local_autonomy"; decision=decision or self._local(f)
            f=self.flies.get(fid)
            if f and f.alive:self._apply(f,decision,source); f.next_decision_at=time.time()+self.rng.uniform(self.cfg.llm_min_decision_seconds,self.cfg.llm_max_decision_seconds)
        finally:self._thinking.discard(fid)

    def _context(self,f:Fly)->dict[str,Any]:
        nearby=[]
        for o in self.flies.values():
            if o.id==f.id or not o.alive:continue
            d=math.dist((f.x,f.y,f.z),(o.x,o.y,o.z))
            if d<=13:nearby.append({"id":o.id,"handle":o.handle,"distance":round(d,1),"sex":o.sex,"age_days":round(o.age_days,1),"action":o.action,"relationship":round(f.relationships.get(str(o.id),0),2),"eligible_mate":self._mate_ok(f,o)})
        nearby.sort(key=lambda x:x["distance"])
        return {"self":{"id":f.id,"handle":f.handle,"sex":f.sex,"age_days":round(f.age_days,1),"needs":{"hunger":round(f.hunger),"thirst":round(f.thirst),"energy":round(f.energy),"loneliness":round(f.loneliness),"health":round(f.health)},"traits":{"boldness":round(f.boldness,2),"sociability":round(f.sociability,2),"curiosity":round(f.curiosity,2)},"current_action":f.action,"current_goal":f.goal},
                "world":{"day":self.day,"minute_of_day":round(self.world_minute%1440),"population":self.population},"nearby_flies":nearby[:8],"memories":f.memories[-8:],
                "places":{name:{"kind":v["kind"],"distance":round(math.dist((f.x,f.z),(v["x"],v["z"])),1)} for name,v in LOCATIONS.items()}}

    def _local(self,f:Fly)->dict[str,Any]:
        if f.thirst>65:return {"action":"drink","goal":"Visit the fountain","thought":"","speech":""}
        if f.hunger>60:return {"action":"forage","goal":"Search for ripe fruit","thought":"","speech":""}
        if f.energy<35:return {"action":"sleep","goal":"Return to a safe resting place","thought":"","speech":""}
        nearby=[o for o in self.flies.values() if o.alive and o.id!=f.id and math.dist((f.x,f.y,f.z),(o.x,o.y,o.z))<11]
        mates=[o for o in nearby if self._mate_ok(f,o)]; roll=self.rng.random()
        if mates and roll<.08+.12*f.sociability:
            t=self.rng.choice(mates);return {"action":"mate","target_id":t.id,"goal":f"Approach @{t.handle}","thought":"A nearby fly caught my attention.","speech":""}
        if nearby and roll<.30+.35*f.sociability:
            t=self.rng.choice(nearby);return {"action":"socialize","target_id":t.id,"goal":f"Check in with @{t.handle}","thought":"I want company.","speech":""}
        action="explore" if self.rng.random()<.45+.4*f.curiosity else "wander"; return {"action":action,"goal":"Explore an unfamiliar block" if action=="explore" else "Drift through the city","thought":"","speech":""}

    def _apply(self,f:Fly,d:dict[str,Any],source:str)->None:
        action=str(d.get("action","wander")); tid=d.get("target_id"); target=self.flies.get(int(tid)) if tid is not None and str(tid).isdigit() else None
        if target and (not target.alive or target.id==f.id):target=None
        if action in {"socialize","mate"} and target is None:action="wander"
        if action=="mate" and target and not self._mate_ok(f,target):action="socialize"
        f.action=action; f.target_id=target.id if target else None; f.goal=str(d.get("goal",""))[:80] or action.title(); f.thought=str(d.get("thought",""))[:150]; f.speech=str(d.get("speech",""))[:120]; f.decision_by=source; self._destination(f,action,target)
        if f.speech:self._event("speech",f"@{f.handle}: “{f.speech}”",f.id,target.id if target else None);self._remember(f,f"I said: {f.speech}",.35)

    def _destination(self,f:Fly,action:str,target:Fly|None=None)->None:
        if target:f.dx,f.dy,f.dz=target.x,target.y,target.z;return
        if action in {"forage","eat"}:
            loc=min((LOCATIONS["orchard"],LOCATIONS["market"]),key=lambda p:math.dist((f.x,f.z),(p["x"],p["z"])))
        elif action=="drink":loc=LOCATIONS["fountain"]
        elif action in {"sleep","home"}:f.dx,f.dy,f.dz=f.home_x,f.home_y,f.home_z;return
        elif action=="explore":loc=self.rng.choice(list(LOCATIONS.values()));f.dx=loc["x"]+self.rng.uniform(-8,8);f.dy=max(1.2,loc["y"]+self.rng.uniform(-1,5));f.dz=loc["z"]+self.rng.uniform(-8,8);return
        else:f.dx,f.dy,f.dz=self.rng.uniform(-52,52),self.rng.uniform(1.2,10),self.rng.uniform(-52,52);return
        f.dx,f.dy,f.dz=loc["x"],loc["y"],loc["z"]

    def _move(self,f:Fly,rs:float,wd:float)->None:
        target=self.flies.get(f.target_id) if f.target_id else None
        if target and target.alive and f.action in {"socialize","mate"}:f.dx,f.dy,f.dz=target.x,target.y,target.z
        vx,vy,vz=f.dx-f.x,f.dy-f.y,f.dz-f.z; dist=math.sqrt(vx*vx+vy*vy+vz*vz)
        if dist>.05:
            step=min(dist,f.speed*(.55 if f.energy<20 else 1)*rs);f.x+=vx/dist*step;f.y+=vy/dist*step;f.z+=vz/dist*step
        f.x=max(-58,min(58,f.x));f.y=max(.45,min(14,f.y));f.z=max(-58,min(58,f.z))
        if f.action=="forage" and dist<2.5:f.action="eat";f.goal="Eat at the fruit source"
        if f.action=="eat" and dist<3:f.hunger=max(0,f.hunger-wd*.7);f.energy=min(100,f.energy+wd*.05)
        elif f.action=="drink" and dist<3:f.thirst=max(0,f.thirst-wd)
        elif f.action=="sleep" and dist<3.5:f.energy=min(100,f.energy+wd*.55)
        elif f.action in {"socialize","mate"} and target and target.alive and math.dist((f.x,f.y,f.z),(target.x,target.y,target.z))<2.2:
            self._social(f,target,wd)
            if f.action=="mate":self._birth(f,target,rs)
        elif dist<.4 and f.action in {"wander","explore","home"}:f.next_decision_at=min(f.next_decision_at,time.time()+self.rng.uniform(1,5));self._destination(f,f.action)

    def _social(self,f:Fly,o:Fly,wd:float)->None:
        f.loneliness=max(0,f.loneliness-wd*.35);o.loneliness=max(0,o.loneliness-wd*.12);delta=wd*(.003+f.sociability*.002)
        f.relationships[str(o.id)]=max(-1,min(1,f.relationships.get(str(o.id),0)+delta));o.relationships[str(f.id)]=max(-1,min(1,o.relationships.get(str(f.id),0)+delta*.7))
        if self.world_minute-f.last_social_world_minute>120:
            f.last_social_world_minute=self.world_minute; self._remember(f,f"I spent time with @{o.handle}.",.55); self._event("social",f"@{f.handle} encountered @{o.handle}.",f.id,o.id)
            pair=tuple(sorted((f.id,o.id)))
            if pair not in self._talking and len(self._talking)<6:
                o.last_social_world_minute=max(o.last_social_world_minute,self.world_minute); self._talking.add(pair); asyncio.create_task(self._conversation(f.id,o.id))

    async def _conversation(self,a_id:int,b_id:int)->None:
        pair=tuple(sorted((a_id,b_id)))
        try:
            a=self.flies.get(a_id); b=self.flies.get(b_id)
            if not a or not b or not a.alive or not b.alive:return
            turns:list[dict[str,Any]]=[]
            sequence=((a,b),(b,a),(a,b))
            for speaker,listener in sequence:
                if not speaker.alive or not listener.alive:break
                partner={"id":listener.id,"handle":listener.handle,"name":listener.name,"action":listener.action,"relationship":round(speaker.relationships.get(str(listener.id),0),2)}
                line=await generate_turn(self.mind,self._context(speaker),partner,turns) if self.cfg.llm_enabled else None
                source=self.cfg.llm_model if line else "local_dialogue"
                line=line or self._local_line(speaker,listener,turns)
                speaker.speech=line
                turns.append({"speaker_id":speaker.id,"handle":speaker.handle,"text":line,"words_by":source})
            if len(turns)<2:return
            a_lines=[t for t in turns if t["speaker_id"]==a.id]; b_lines=[t for t in turns if t["speaker_id"]==b.id]
            if b_lines:self._remember(a,f"I talked with @{b.handle}. They said: {b_lines[-1]['text']}",.68)
            if a_lines:self._remember(b,f"I talked with @{a.handle}. They said: {a_lines[-1]['text']}",.68)
            transcript=" · ".join(f"@{t['handle']}: “{t['text']}”" for t in turns)
            self._event("dialogue",transcript,a.id,b.id,turns=turns)
        finally:
            self._talking.discard(pair)

    def _local_line(self,speaker:Fly,listener:Fly,history:list[dict[str,Any]])->str:
        relationship=speaker.relationships.get(str(listener.id),0)
        if history:
            heard=history[-1]["text"].lower()
            if "food" in heard or "eat" in heard or "fruit" in heard:return self.rng.choice(["The orchard smelled strongest earlier.","I saw fruit near the market.","I haven't found much yet."])
            if "water" in heard or "fountain" in heard:return self.rng.choice(["The fountain is still running.","I was heading toward the fountain too.","Water sounds good right now."])
            if "sleep" in heard or "rest" in heard:return self.rng.choice(["The hive has been quiet.","I might rest after this.","The rooftop felt safer last time."])
            return self.rng.choice(["I noticed that too.","Maybe. I'm still watching.","What made you think that?","I came from the other side of the city."])
        if speaker.hunger>62:return "Have you found anything worth eating nearby?"
        if speaker.thirst>62:return "I'm looking for water. Have you been to the fountain?"
        if relationship>.3:return f"Good to see you again, @{listener.handle}."
        if relationship<-.2:return "Keep some distance. I'm only passing through."
        if speaker.loneliness>55:return "It's good to run into another fly out here."
        return self.rng.choice(["What have you noticed around here?","Where are you headed?","The air feels different on this block.","Have you been near the market today?"])

    def _mate_ok(self,a:Fly,b:Fly)->bool:
        return a.alive and b.alive and a.sex!=b.sex and a.age_days>=3 and b.age_days>=3 and self.world_minute-a.last_mated_world_minute>=2880 and self.world_minute-b.last_mated_world_minute>=2880 and self.population<self.cfg.population_cap and a.energy>35 and b.energy>35

    def _birth(self,a:Fly,b:Fly,rs:float)->None:
        if not self._mate_ok(a,b) or self.rng.random()>min(.18,.035*rs):return
        mother,father=(a,b) if a.sex=="F" else (b,a); cid=self.next_id;self.next_id+=1;adj=self.rng.choice(ADJECTIVES);noun=self.rng.choice(NOUNS)
        c=Fly(cid,f"{adj}_{noun}_{cid}",f"{adj.title()} {noun.title()} {cid}",self.rng.choice(["F","M"]),max(a.generation,b.generation)+1,self.world_minute,0,
              max(35,min(85,(a.lifespan_days+b.lifespan_days)/2+self.rng.uniform(-8,8))),mother.x+self.rng.uniform(-1,1),max(.8,mother.y),mother.z+self.rng.uniform(-1,1),mother.x,mother.y,mother.z,mother.home_x,mother.home_y,mother.home_z,
              (a.hue+b.hue)/2+self.rng.uniform(-22,22),max(.65,min(1.25,(a.size+b.size)/2+self.rng.uniform(-.08,.08))),max(2.5,min(5.8,(a.speed+b.speed)/2+self.rng.uniform(-.5,.5))),
              max(0,min(1,(a.boldness+b.boldness)/2+self.rng.uniform(-.18,.18))),max(0,min(1,(a.sociability+b.sociability)/2+self.rng.uniform(-.18,.18))),max(0,min(1,(a.curiosity+b.curiosity)/2+self.rng.uniform(-.18,.18))),18,12,85,5,parent_a=mother.id,parent_b=father.id,next_decision_at=time.time()+self.rng.uniform(20,60))
        a.last_mated_world_minute=b.last_mated_world_minute=self.world_minute;a.children.append(cid);b.children.append(cid);self.flies[cid]=c;self.births+=1;self._destination(c,"wander");self._remember(a,f"@{c.handle} was born from my pairing with @{b.handle}.",.95);self._remember(b,f"@{c.handle} was born from my pairing with @{a.handle}.",.95);self._event("birth",f"@{c.handle} was born to @{mother.handle} and @{father.handle}.",cid,mother.id)

    def summary(self)->dict[str,Any]:
        m=int(self.world_minute%1440)
        return {"name":"FlyCity","version":"0.2.0","running":True,"day":self.day,"minute_of_day":m,"time_label":f"{m//60:02d}:{m%60:02d}","population":self.population,"total_flies":len(self.flies),"births":self.births,"deaths":self.deaths,"initial_population":self.cfg.initial_population,"world_minutes_per_real_second":self.cfg.world_minutes_per_real_second,"decision_model":self.cfg.llm_model if self.model_live else "local autonomy (set OPENAI_API_KEY to enable Luna)","model_live":self.model_live,"locations":LOCATIONS,"flies":[f.public() for f in self.flies.values() if f.alive],"events":self.events[-40:][::-1]}
    def fly_detail(self,fly_id:int)->dict[str,Any]|None:
        f=self.flies.get(fly_id);return f.public(True) if f else None
