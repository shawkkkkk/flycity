from __future__ import annotations

import asyncio
import math
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import Settings
from .mind import OpenAIMind
from .store import SnapshotStore

ADJECTIVES = ["amber", "brisk", "cobalt", "dappled", "electric", "fuzzy", "gentle", "hollow", "iridescent", "jittery"]
NOUNS = ["antenna", "bristle", "compoundeye", "drifter", "fruit", "hover", "lantern", "proboscis", "shadow", "wing"]

LOCATIONS: dict[str, dict[str, Any]] = {
    "orchard": {"x": -38.0, "z": -28.0, "y": 2.0, "kind": "food"},
    "market": {"x": 35.0, "z": -22.0, "y": 2.0, "kind": "food"},
    "fountain": {"x": 0.0, "z": 5.0, "y": 1.5, "kind": "water"},
    "hive": {"x": -30.0, "z": 34.0, "y": 2.5, "kind": "rest"},
    "rooftop": {"x": 29.0, "z": 31.0, "y": 9.0, "kind": "rest"},
    "lamp": {"x": 0.0, "z": -39.0, "y": 10.0, "kind": "landmark"},
    "alley": {"x": 4.0, "z": 42.0, "y": 2.0, "kind": "landmark"},
}


@dataclass
class Fly:
    id: int
    handle: str
    name: str
    sex: str
    generation: int
    born_world_minute: float
    age_days: float
    lifespan_days: float
    x: float
    y: float
    z: float
    dx: float
    dy: float
    dz: float
    home_x: float
    home_y: float
    home_z: float
    hue: float
    size: float
    speed: float
    boldness: float
    sociability: float
    curiosity: float
    hunger: float
    thirst: float
    energy: float
    loneliness: float
    health: float = 100.0
    action: str = "wander"
    goal: str = "Explore the city"
    thought: str = ""
    speech: str = ""
    target_id: int | None = None
    decision_by: str = "local_survival_controller"
    alive: bool = True
    parent_a: int | None = None
    parent_b: int | None = None
    children: list[int] = field(default_factory=list)
    memories: list[dict[str, Any]] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)
    last_mated_world_minute: float = -1e9
    next_decision_at: float = 0.0
    last_social_world_minute: float = -1e9

    def public(self, detailed: bool = False) -> dict[str, Any]:
        data = {
            "id": self.id,
            "handle": self.handle,
            "name": self.name,
            "sex": self.sex,
            "generation": self.generation,
            "age_days": round(self.age_days, 2),
            "x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3),
            "hue": round(self.hue, 1), "size": round(self.size, 3),
            "hunger": round(self.hunger, 1), "thirst": round(self.thirst, 1),
            "energy": round(self.energy, 1), "loneliness": round(self.loneliness, 1),
            "health": round(self.health, 1),
            "action": self.action, "goal": self.goal, "thought": self.thought,
            "speech": self.speech, "target_id": self.target_id,
            "decision_by": self.decision_by, "alive": self.alive,
            "parent_a": self.parent_a, "parent_b": self.parent_b,
        }
        if detailed:
            data.update({
                "lifespan_days": round(self.lifespan_days, 1),
                "home": {"x": self.home_x, "y": self.home_y, "z": self.home_z},
                "traits": {
                    "speed": round(self.speed, 2), "boldness": round(self.boldness, 2),
                    "sociability": round(self.sociability, 2), "curiosity": round(self.curiosity, 2),
                },
                "children": self.children[-30:],
                "memories": self.memories[-12:][::-1],
                "relationships": sorted(
                    ({"fly_id": int(k), "score": round(v, 2)} for k, v in self.relationships.items()),
                    key=lambda item: abs(item["score"]), reverse=True,
                )[:12],
            })
        return data


class FlyCity:
    FORMAT = 1

    def __init__(self, cfg: Settings, store: SnapshotStore):
        self.cfg = cfg
        self.store = store
        self.rng = random.Random(cfg.seed)
        self.mind = OpenAIMind(cfg.llm_model, cfg.llm_calls_per_minute)
        self.flies: dict[int, Fly] = {}
        self.events: list[dict[str, Any]] = []
        self.world_minute = 8 * 60.0
        self.day = 1
        self.next_id = 1
        self.births = 0
        self.deaths = 0
        self.started_at = time.time()
        self.last_snapshot_at = 0.0
        self._thinking: set[int] = set()
        self._load_or_seed()

    @property
    def model_live(self) -> bool:
        return bool(self.cfg.llm_enabled and self.mind.enabled)

    def _load_or_seed(self) -> None:
        payload = self.store.load()
        if payload and payload.get("format") == self.FORMAT:
            self.world_minute = float(payload.get("world_minute", self.world_minute))
            self.day = int(payload.get("day", 1))
            self.next_id = int(payload.get("next_id", 1))
            self.births = int(payload.get("births", 0))
            self.deaths = int(payload.get("deaths", 0))
            self.events = list(payload.get("events", []))[-300:]
            for raw in payload.get("flies", []):
                fly = Fly(**raw)
                fly.next_decision_at = min(fly.next_decision_at, time.time() + self.rng.uniform(2, 20))
                self.flies[fly.id] = fly
            if self.flies:
                return
        self._seed_population(self.cfg.initial_population)
        self._event("system", f"FlyCity began with {len(self.flies)} autonomous residents.")
        self.save()

    def _seed_population(self, count: int) -> None:
        for index in range(count):
            adjective = ADJECTIVES[(index // len(NOUNS)) % len(ADJECTIVES)]
            noun = NOUNS[index % len(NOUNS)]
            handle = f"{adjective}_{noun}" if index < 100 else f"{adjective}_{noun}_{index+1}"
            home = self.rng.choice([LOCATIONS["hive"], LOCATIONS["rooftop"], {"x": -8, "y": 2, "z": 28}, {"x": 18, "y": 3, "z": 14}])
            fly = Fly(
                id=self.next_id,
                handle=handle,
                name=f"{adjective.title()} {noun.title()}",
                sex="F" if index % 2 == 0 else "M",
                generation=0,
                born_world_minute=self.world_minute - self.rng.uniform(2, 18) * 1440,
                age_days=self.rng.uniform(2, 18),
                lifespan_days=self.rng.uniform(45, 75),
                x=home["x"] + self.rng.uniform(-8, 8), y=self.rng.uniform(1.2, 8), z=home["z"] + self.rng.uniform(-8, 8),
                dx=0, dy=0, dz=0,
                home_x=float(home["x"]), home_y=float(home["y"]), home_z=float(home["z"]),
                hue=(index * 137.508) % 360,
                size=self.rng.uniform(0.78, 1.18), speed=self.rng.uniform(3.0, 5.2),
                boldness=self.rng.random(), sociability=self.rng.random(), curiosity=self.rng.random(),
                hunger=self.rng.uniform(10, 55), thirst=self.rng.uniform(8, 45),
                energy=self.rng.uniform(35, 95), loneliness=self.rng.uniform(5, 60),
                next_decision_at=time.time() + self.rng.uniform(1, 30),
            )
            self.next_id += 1
            self._set_destination(fly, "wander")
            self.flies[fly.id] = fly

    def _event(self, kind: str, text: str, fly_id: int | None = None, other_id: int | None = None) -> None:
        self.events.append({
            "id": f"{int(time.time()*1000)}-{len(self.events)}",
            "kind": kind, "text": text, "fly_id": fly_id, "other_id": other_id,
            "world_minute": round(self.world_minute, 2), "day": self.day,
        })
        self.events = self.events[-300:]

    def _remember(self, fly: Fly, text: str, importance: float = 0.5) -> None:
        fly.memories.append({"text": text[:180], "importance": round(importance, 2), "day": self.day})
        fly.memories = fly.memories[-30:]

    def save(self) -> None:
        self.store.save({
            "format": self.FORMAT,
            "world_minute": self.world_minute, "day": self.day,
            "next_id": self.next_id, "births": self.births, "deaths": self.deaths,
            "events": self.events[-300:],
            "flies": [asdict(fly) for fly in self.flies.values()],
        })
        self.last_snapshot_at = time.time()

    async def step(self, real_seconds: float) -> None:
        if real_seconds <= 0:
            return
        world_delta = real_seconds * self.cfg.world_minutes_per_real_second
        self.world_minute += world_delta
        self.day = int(self.world_minute // 1440) + 1
        now = time.time()
        living = [fly for fly in self.flies.values() if fly.alive]

        for fly in living:
            self._metabolism(fly, world_delta)
            if not fly.alive:
                continue
            self._survival_reflex(fly)
            self._move_and_act(fly, real_seconds, world_delta)
            if fly.alive and now >= fly.next_decision_at and fly.id not in self._thinking:
                self._thinking.add(fly.id)
                asyncio.create_task(self._decide_for(fly.id))

        if now - self.last_snapshot_at >= self.cfg.snapshot_seconds:
            self.save()

    def _metabolism(self, fly: Fly, world_delta: float) -> None:
        fly.age_days += world_delta / 1440.0
        fly.hunger = min(100.0, fly.hunger + world_delta * 0.045)
        fly.thirst = min(100.0, fly.thirst + world_delta * 0.060)
        fly.loneliness = min(100.0, fly.loneliness + world_delta * (0.020 + 0.012 * fly.sociability))
        if fly.action != "sleep":
            fly.energy = max(0.0, fly.energy - world_delta * 0.035)
        damage = 0.0
        if fly.hunger > 94: damage += world_delta * 0.08
        if fly.thirst > 96: damage += world_delta * 0.13
        if fly.energy <= 0: damage += world_delta * 0.05
        fly.health = max(0.0, min(100.0, fly.health - damage + world_delta * (0.005 if damage == 0 else 0)))
        if fly.health <= 0 or fly.age_days >= fly.lifespan_days:
            fly.alive = False
            fly.action = "dead"
            fly.goal = ""
            self.deaths += 1
            reason = "old age" if fly.age_days >= fly.lifespan_days else "unmet survival needs"
            self._event("death", f"@{fly.handle} died from {reason} on day {self.day}.", fly.id)

    def _survival_reflex(self, fly: Fly) -> None:
        if fly.thirst > 91 and fly.action not in {"drink", "sleep"}:
            self._apply_decision(fly, {"action": "drink", "target_id": None, "goal": "Find water", "thought": "I need water now.", "speech": ""}, "survival_reflex")
        elif fly.hunger > 88 and fly.action not in {"forage", "eat", "sleep"}:
            self._apply_decision(fly, {"action": "forage", "target_id": None, "goal": "Find food", "thought": "Hunger is overriding everything else.", "speech": ""}, "survival_reflex")
        elif fly.energy < 10 and fly.action != "sleep":
            self._apply_decision(fly, {"action": "sleep", "target_id": None, "goal": "Rest somewhere safe", "thought": "I can barely stay airborne.", "speech": ""}, "survival_reflex")

    async def _decide_for(self, fly_id: int) -> None:
        try:
            fly = self.flies.get(fly_id)
            if not fly or not fly.alive:
                return
            context = self._mind_context(fly)
            decision = await self.mind.decide(context) if self.cfg.llm_enabled else None
            if not decision:
                decision = self._local_decision(fly)
                source = "local_autonomy"
            else:
                source = self.cfg.llm_model
            current = self.flies.get(fly_id)
            if current and current.alive:
                self._apply_decision(current, decision, source)
                current.next_decision_at = time.time() + self.rng.uniform(
                    self.cfg.llm_min_decision_seconds, self.cfg.llm_max_decision_seconds
                )
        finally:
            self._thinking.discard(fly_id)

    def _mind_context(self, fly: Fly) -> dict[str, Any]:
        nearby = []
        for other in self.flies.values():
            if other.id == fly.id or not other.alive:
                continue
            d = math.dist((fly.x, fly.y, fly.z), (other.x, other.y, other.z))
            if d <= 13:
                nearby.append({
                    "id": other.id, "handle": other.handle, "distance": round(d, 1),
                    "sex": other.sex, "age_days": round(other.age_days, 1),
                    "action": other.action, "relationship": round(fly.relationships.get(str(other.id), 0.0), 2),
                    "eligible_mate": self._mate_eligible(fly, other),
                })
        nearby.sort(key=lambda item: item["distance"])
        return {
            "self": {
                "id": fly.id, "handle": fly.handle, "sex": fly.sex, "age_days": round(fly.age_days, 1),
                "needs": {"hunger": round(fly.hunger), "thirst": round(fly.thirst), "energy": round(fly.energy), "loneliness": round(fly.loneliness), "health": round(fly.health)},
                "traits": {"boldness": round(fly.boldness, 2), "sociability": round(fly.sociability, 2), "curiosity": round(fly.curiosity, 2)},
                "current_action": fly.action, "current_goal": fly.goal,
            },
            "world": {"day": self.day, "minute_of_day": round(self.world_minute % 1440), "population": self.population},
            "nearby_flies": nearby[:8],
            "memories": fly.memories[-8:],
            "places": {name: {"kind": v["kind"], "distance": round(math.dist((fly.x, fly.z), (v)x"], v["z"])), 1)} for name, v in LOCATIONS.items()},
        }

    def _local_decision(self, fly: Fly) -> dict[str, Any]:
        if fly.thirst > 65:
            action, goal = "drink", "Visit the fountain"
        elif fly.hunger > 60:
            action, goal = "forage", "Search for ripe fruit"
        elif fly.energy < 35:
            action, goal = "sleep", "Return to a safe resting place"
        else:
            nearby = [o for o in self.flies.values() if o.alive and o.id != fly.id and math.dist((fly.x, fly.y, fly.z), (o.x, o.y, o.z)) < 11]
            mates = [o for o in nearby if self._mate_eligible(fly, o)]
            roll = self.rng.random()
            if mates and roll < 0.08 + 0.12 * fly.sociability:
                target = self.rng.choice(mates)
                return {"action": "mate", "target_id": target.id, "goal": f"Approach @{target.handle}", "thought": "A nearby fly caught my attention.", "speech": ""}
            if nearby and roll < 0.30 + 0.35 * fly.sociability:
                target = self.rng.choice(nearby)
                return {"action": "socialize", "target_id": target.id, "goal": f"Check in with @{target.handle}", "thought": "I want company.", "speech": ""}
            action = "explore" if self.rng.random() < 0.45 + 0.4 * fly.curiosity else "wander"
            goal = "Explore an unfamiliar block" if action == "explore" else "Drift through the city"
        return {"action": action, "target_id": None, "goal": goal, "thought": "", "speech": ""}

    def _apply_decision(self, fly: Fly, decision: dict[str, Any], source: str) -> None:
        action = str(decision.get("action", "wander"))
        target_id = decision.get("target_id")
        target = self.flies.get(int(target_id)) if target_id is not None and str(target_id).isdigit() else None
        if target and (not target.alive or target.id == fly.id):
            target = None
        if action in {"socialize", "mate"} and target is None:
            action = "wander"
        if action == "mate" and target and not self._mate_eligible(fly, target):
            action = "socialize"
        fly.action = action
        fly.target_id = target.id if target else None
        fly.goal = str(decision.get("goal", ""))[:80] or action.replace("_", " ").title()
        fly.thought = str(decision.get("thought", ""))[:150]
        fly.speech = str(decision.get("speech", ""))[:120]
        fly.decision_by = source
        self._set_destination(fly, action, target)
        if fly.speech:
            self._event("speech", f"@{fly.handle}: “{fly.speech}”", fly.id, target.id if target else None)
            self._remember(fly, f"I said: {fly.speech}", 0.35)

    def _set_destination(self, fly: Fly, action: str, target: Fly | None = None) -> None:
        if target is not None:
            fly.dx, fly.dy, fly.dz = target.x, target.y, target.z
            return
        if action in {"forage", "eat"}:
            options = [LOCATIONS["orchard"], LOCATIONS["market"]]
            loc = min(options, key=lambda p: math.dist((fly.x, fly.z), (p["x"], p["z"])))
            fly.dx, fly.dy, fly.dz = loc["x"], loc["y"], loc["z"]
        elif action == "drink":
            loc = LOCATIONS["fountain"]
            fly.dx, fly.dy, fly.dz = loc["x"], loc["y"], loc["z"]
        elif action in {"sleep", "home"}:
            fly.dx, fly.dy, fly.dz = fly.home_x, fly.home_y, fly.home_z
        elif action == "explore":
            landmarks = list(LOCATIONS.values())
            loc = self.rng.choice(landmarks)
            fly.dx = loc["x"] + self.rng.uniform(-8, 8)
            fly.dz = loc["z"] + self.rng.uniform(-8, 8)
            fly.dy = max(1.2, loc["y"] + self.rng.uniform(-1, 5))
        else:
            fly.dx = self.rng.uniform(-52, 52)
            fly.dz = self.rng.uniform(-52, 52)
            fly.dy = self.rng.uniform(1.2, 10)

    def _move_and_act(self, fly: Fly, real_seconds: float, world_delta: float) -> None:
        target = self.flies.get(fly.target_id) if fly.target_id else None
        if target and target.alive and fly.action in {"socialize", "mate"}:
            fly.dx, fly.dy, fly.dz = target.x, target.y, target.z
        vx, vy, vz = fly.dx - fly.x, fly.dy - fly.y, fly.dz - fly.z
        distance = math.sqrt(vx*vx + vy*vy + vz*vz)
        if distance > 0.05:
            speed = fly.speed * (0.55 if fly.energy < 20 else 1.0)
            step = min(distance, speed * real_seconds)
            fly.x += vx / distance * step
            fly.y += vy / distance * step
            fly.z += vz / distance * step
        fly.x = max(-58, min(58, fly.x)); fly.z = max(-58, min(58, fly.z)); fly.y = max(0.45, min(14, fly.y))

        if fly.action == "forage" and distance < 2.5:
            fly.action = "eat"; fly.goal = "Eat at the fruit source"
        if fly.action == "eat" and distance < 3.0:
            fly.hunger = max(0.0, fly.hunger - world_delta * 0.70)
            fly.energy = min(100.0, fly.energy + world_delta * 0.05)
            if fly.hunger < 18:
                self._remember(fly, "I ate enough fruit to stop feeling hungry.", 0.45)
                fly.next_decision_at = min(fly.next_decision_at, time.time() + 2)
        elif fly.action == "drink" and distance < 3.0:
            fly.thirst = max(0.0, fly.thirst - world_delta * 1.0)
            if fly.thirst < 15:
                self._remember(fly, "I drank at the fountain.", 0.35)
                fly.next_decision_at = min(fly.next_decision_at, time.time() + 2)
        elif fly.action == "sleep" and distance < 3.5:
            fly.energy = min(100.0, fly.energy + world_delta * 0.55)
            fly.y = max(0.6, min(14, fly.home_y))
            if fly.energy > 90:
                self._remember(fly, "I woke up rested.", 0.35)
                fly.next_decision_at = min(fly.next_decision_at, time.time() + 2)
        elif fly.action in {"socialize", "mate"} and target and target.alive:
            d = math.dist((fly.x, fly.y, fly.z), (target.x, target.y, target.z))
            if d < 2.2:
                self._social_contact(fly, target, world_delta)
                if fly.action == "mate":
                    self._try_birth(fly, target, real_seconds)
        elif distance < 0.4 and fly.action in {"wander", "explore", "home"}:
            fly.next_decision_at = min(fly.next_decision_at, time.time() + self.rng.uniform(1, 5))
            if fly.action in {"wander", "explore"}:
                self._set_destination(fly, fly.action)

    def _social_contact(self, fly: Fly, other: Fly, world_delta: float) -> None:
        fly.loneliness = max(0.0, fly.loneliness - world_delta * 0.35)
        other.loneliness = max(0.0, other.loneliness - world_delta * 0.12)
        key = str(other.id)
        reverse = str(fly.id)
        delta = world_delta * (0.003 + fly.sociability * 0.002)
        fly.relationships[key] = max(-1.0, min(1.0, fly.relationships.get(key, 0.0) + delta))
        other.relationships[reverse] = max(-1.0, min(1.0, other.relationships.get(reverse, 0.0) + delta * 0.7))
        if self.world_minute - fly.last_social_world_minute > 120:
            fly.last_social_world_minute = self.world_minute
            self._remember(fly, f"I spent time with @{other.handle}.", 0.55)
            self._event("social", f"@{fly.handle} spent time with @{other.handle}.", fly.id, other.id)

    def _mate_eligible(self, a: Fly, b: Fly) -> bool:
        if not (a.alive and b.alive) or a.sex == b.sex or a.age_days < 3 or b.age_days < 3:
            return False
        if self.world_minute - a.last_mated_world_minute < 2880 or self.world_minute - b.last_mated_world_minute < 2880:
            return False
        return self.population < self.cfg.population_cap and a.energy > 35 and b.energy > 35

    def _try_birth(self, a: Fly, b: Fly, real_seconds: float) -> None:
        if not self._mate_eligible(a, b):
            return
        if self.rng.random() > min(0.18, 0.035 * real_seconds):
            return
        mother, father = (a, b) if a.sex == "F" else (b, a)
        child_id = self.next_id; self.next_id += 1
        adjective = self.rng.choice(ADJECTIVES); noun = self.rng.choice(NOUNS)
        child = Fly(
            id=child_id, handle=f"{adjective}_{noun}_{child_id}", name=f"{adjective.title()} {noun.title()} {child_id}",
            sex=self.rng.choice(["F", "M"]), generation=max(a.generation, b.generation) + 1,
            born_world_minute=self.world_minute, age_days=0.0,
            lifespan_days=max(35, min(85, (a.lifespan_days + b.lifespan_days)/2 + self.rng.uniform(-8, 8))),
            x=mother.x + self.rng.uniform(-1, 1), y=max(0.8, mother.y), z=mother.z + self.rng.uniform(-1, 1),
            dx=mother.x, dy=mother.y, dz=mother.z,
            home_x=mother.home_x, home_y=mother.home_y, home_z=mother.home_z,
            hue=(a.hue + b.hue) / 2 + self.rng.uniform(-22, 22),
            size=max(0.65, min(1.25, (a.size + b.size)/2 + self.rng.uniform(-0.08, 0.08))),
            speed=max(2.5, min(5.8, (a.speed + b.speed)/2 + self.rng.uniform(-0.5, 0.5))),
            boldness=max(0, min(1, (a.boldness+b.boldness)/2 + self.rng.uniform(-0.18, 0.18))),
            sociability=max(0, min(1, (a.sociability+b.sociability)/2 + self.rng.uniform(-0.18, 0.18))),
            curiosity=max(0, min(1, (a.curiosity+b.curiosity)/2 + self.rng.uniform(-0.18, 0.18))),
            hunger=18, thirst=12, energy=85, loneliness=5,
            parent_a=mother.id, parent_b=father.id,
            next_decision_at=time.time() + self.rng.uniform(20, 60),
        )
        a.last_mated_world_minute = b.last_mated_world_minute = self.world_minute
        a.children.append(child.id); b.children.append(child.id)
        self.flies[child.id] = child
        self.births += 1
        self._set_destination(child, "wander")
        self._remember(a, f"A new fly, @{child.handle}, was born from my pairing with @{b.handle}.", 0.95)
        self._remember(b, f"A new fly, @{child.handle}, was born from my pairing with @{a.handle}.", 0.95)
        self._event("birth", f"@{child.handle} was born to @{mother.handle} and @{father.handle}.", child.id, mother.id)

    @property
    def population(self) -> int:
        return sum(1 for f in self.flies.values() if f.alive)

    def summary(self) -> dict[str, Any]:
        minute = int(self.world_minute % 1440)
        return {
            "name": "FlyCity", "version": "0.1.0", "running": True,
            "day": self.day, "minute_of_day": minute,
            "time_label": f"{minute//60:02d}:{minute%60:02d}",
            "population": self.population, "total_flies": len(self.flies),
            "births": self.births, "deaths": self.deaths,
            "initial_population": self.cfg.initial_population,
            "world_minutes_per_real_second": self.cfg.world_minutes_per_real_second,
            "decision_model": self.cfg.llm_model if self.model_live else "local autonomy (set OPENAI_API_KEY to enable Luna)",
            "model_live": self.model_live,
            "locations": LOCATIONS,
            "flies": [fly.public(False) for fly in self.flies.values() if fly.alive],
            "events": self.events[-40:][::-1],
        }

    def fly_detail(self, fly_id: int) -> dict[str, Any] | None:
        fly = self.flies.get(fly_id)
        return fly.public(True) if fly else None
