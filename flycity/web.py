from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .simulation import FlyCity
from .store import SnapshotStore

SITE = Path(__file__).resolve().parent.parent / "site"
store: SnapshotStore | None = None
city: FlyCity | None = None
sim_task: asyncio.Task | None = None


async def simulation_loop() -> None:
    assert city is not None
    loop = asyncio.get_running_loop()
    last = loop.time()
    while True:
        await asyncio.sleep(settings.tick_seconds)
        now = loop.time()
        dt = min(5.0, max(0.05, now - last))
        last = now
        await city.step(dt)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global store, city, sim_task
    store = SnapshotStore(settings.db_path)
    city = FlyCity(settings, store)
    sim_task = asyncio.create_task(simulation_loop())
    try:
        yield
    finally:
        if sim_task:
            sim_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sim_task
        if city:
            city.save()
        if store:
            store.close()


app = FastAPI(title="FlyCity", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"ok": True, "population": city.population if city else 0, "model_live": city.model_live if city else False}


@app.get("/api/state")
def state():
    if city is None:
        raise HTTPException(503, "City is starting")
    return city.summary()


@app.get("/api/flies/{fly_id}")
def fly_detail(fly_id: int):
    if city is None:
        raise HTTPException(503, "City is starting")
    detail = city.fly_detail(fly_id)
    if detail is None:
        raise HTTPException(404, "Fly not found")
    return detail


@app.get("/api/events")
def events(limit: int = 50):
    if city is None:
        raise HTTPException(503, "City is starting")
    limit = max(1, min(200, limit))
    return {"events": city.events[-limit:][::-1]}


@app.websocket("/ws")
async def websocket_state(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            if city is not None:
                await ws.send_json(city.summary())
            await asyncio.sleep(1.0)
    except (WebSocketDisconnect, RuntimeError):
        return


@app.get("/")
def index():
    return FileResponse(SITE / "index.html")


app.mount("/", StaticFiles(directory=SITE, html=True), name="site")


def run() -> None:
    uvicorn.run("flycity.web:app", host=settings.host, port=settings.port, reload=False, log_level="info")
