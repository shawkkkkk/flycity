import asyncio
from dataclasses import replace

from flycity.config import settings
from flycity.simulation import FlyCity
from flycity.store import SnapshotStore


def make_city(tmp_path):
    cfg = replace(
        settings,
        db_path=str(tmp_path / "flycity.sqlite3"),
        initial_population=100,
        llm_enabled=False,
        tick_seconds=0.01,
    )
    store = SnapshotStore(cfg.db_path)
    return FlyCity(cfg, store), store


def test_seeds_100_unique_flies(tmp_path):
    city, store = make_city(tmp_path)
    assert city.population == 100
    handles = [f.handle for f in city.flies.values()]
    assert len(handles) == len(set(handles)) == 100
    assert all(f.alive for f in city.flies.values())
    store.close()


def test_world_advances_and_persists(tmp_path):
    city, store = make_city(tmp_path)
    start = city.world_minute
    asyncio.run(city.step(1.0))
    assert city.world_minute > start
    city.save()
    store.close()

    cfg = replace(settings, db_path=str(tmp_path / "flycity.sqlite3"), llm_enabled=False)
    store2 = SnapshotStore(cfg.db_path)
    restored = FlyCity(cfg, store2)
    assert restored.population == city.population
    assert restored.world_minute >= city.world_minute
    store2.close()


def test_public_snapshot_is_readable(tmp_path):
    city, store = make_city(tmp_path)
    state = city.summary()
    assert state["population"] == 100
    assert len(state["flies"]) == 100
    assert "locations" in state
    detail = city.fly_detail(1)
    assert detail and "memories" in detail and "relationships" in detail
    store.close()


def test_encounter_creates_visible_dialogue(tmp_path):
    city, store = make_city(tmp_path)
    first = city.flies[1]
    second = city.flies[2]
    first.x = second.x = 0.0
    first.y = second.y = 2.0
    first.z = second.z = 0.0

    asyncio.run(city._conversation(first.id, second.id))

    dialogue = next(event for event in reversed(city.events) if event["kind"] == "dialogue")
    assert dialogue["fly_id"] == first.id
    assert dialogue["other_id"] == second.id
    assert len(dialogue["turns"]) >= 2
    assert {turn["speaker_id"] for turn in dialogue["turns"]} == {first.id, second.id}
    assert first.speech
    assert second.speech
    store.close()
