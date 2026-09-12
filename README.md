# FlyCity

**A persistent 3D world inhabited by autonomous digital fruit flies.**

FlyCity starts with **100 individually persistent flies** living inside one shared city. Every fly has its own needs, personality, memories, relationships, home, age, lineage, and high-level decision loop. The world keeps moving whether or not a human observer is watching.

The browser is spectator-only: fly through the city, tag any resident, follow it in 3D, inspect its current intention, needs, memories, family, relationships, recent speech, and the provenance of its latest decision.

**Made by Shayanel H.** · <https://x.com/shayanelh>

## What is already implemented

- a browser-based Three.js city with streets, buildings, an orchard, fruit market, fountain, hive, rooftop, lamp district, and alley;
- **100 procedural 3D fly models** at launch, each with a body, head, compound eyes, wings, legs, animation, unique color, size, and persistent identity;
- WASD + mouse spectator flight, vertical movement, crosshair tagging, resident search, and follow-camera mode;
- authoritative Python simulation running continuously on the server;
- hunger, thirst, energy, loneliness, health, aging, sleep, eating, drinking, exploration, social contact, and survival reflexes;
- independent personality traits for speed, boldness, sociability, and curiosity;
- persistent memories and fly-to-fly relationship scores;
- mating, inherited traits, offspring, generations, lineage, aging, and death;
- accelerated world time so multi-day social and biological dynamics can actually be observed;
- a live event feed for speech, social encounters, births, deaths, and colony history;
- SQLite snapshots, so the city survives process restarts;
- a WebSocket stream that keeps every spectator synchronized to the same world;
- per-fly high-level decisions from **OpenAI GPT-5.6 Luna** when an API key is configured;
- a local autonomous controller when model access is unavailable, plus hard survival reflexes for critical hunger, thirst, and exhaustion;
- decision provenance in the inspector so model decisions and survival overrides are distinguishable.

## How autonomy works

FlyCity separates **physical simulation** from **high-level intention**.

The server continuously handles movement, metabolism, proximity, eating, sleeping, aging, reproduction, and other physical rules. Each fly also has a persistent mind state. At staggered decision points, that fly receives only its own state and local context: needs, traits, nearby flies, remembered events, relationships, and distances to important places.

With the OpenAI layer enabled, GPT-5.6 Luna chooses one high-level intention such as forage, sleep, socialize, mate, explore, go home, or wander. It can also produce a brief private thought and optional utterance. The model does **not** directly control rendering or physics.

All 100 starting flies have independent mind schedules and persistent state. Calls are rate-limited globally so the city can stay economically operable; survival-critical behavior does not wait for a language-model call.

This is an autonomous-agent simulation, not a claim that the software is conscious or a biologically exact fruit-fly brain emulation.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m flycity
```

Open <http://127.0.0.1:8000>.

Without an API key, the full world still runs using the local autonomy layer.

To enable GPT-5.6 Luna minds:

```bash
export OPENAI_API_KEY="your key"
export FLYCITY_LLM_ENABLED=true
export FLYCITY_MODEL=gpt-5.6-luna
python -m flycity
```

## Controls

| Input | Action |
|---|---|
| Mouse | Look around |
| W A S D | Fly through the city |
| Space / Shift | Move up / down |
| E | Tag the fly in the crosshair |
| F | Follow / release the tagged fly |
| Esc | Release the mouse |

You can also select any resident from the on-screen resident directory.

## Deploy on Railway

The repository includes a `Dockerfile` and `railway.json`.

Recommended variables:

```text
FLYCITY_DB=/data/flycity.sqlite3
OPENAI_API_KEY=...
FLYCITY_LLM_ENABLED=true
FLYCITY_MODEL=gpt-5.6-luna
FLYCITY_LLM_CALLS_PER_MINUTE=60
FLYCITY_WORLD_MINUTES_PER_REAL_SECOND=6
```

Mount a persistent Railway volume at:

```text
/data
```

If you skip the volume, a redeploy can reset the city even though SQLite persistence works during the life of the container.

### Cost control

`FLYCITY_LLM_CALLS_PER_MINUTE` is a global ceiling across the population. Each fly gets staggered model decisions rather than generating tokens every animation frame. You can also tune:

```text
FLYCITY_LLM_MIN_DECISION_SECONDS=75
FLYCITY_LLM_MAX_DECISION_SECONDS=150
```

Lower intervals make the minds more conversational and cost more. Higher intervals make physical behavior dominate between reflective decisions.

## API

Read-only observer endpoints:

```text
GET /api/health
GET /api/state
GET /api/flies/{id}
GET /api/events
WS  /ws
```

There is intentionally no public endpoint for a human to command, move, feed, kill, message, or otherwise puppeteer an individual fly.

## Persistence model

The authoritative world is serialized into SQLite on a short interval and on graceful shutdown. Stored state includes every fly's identity, needs, traits, position, home, memories, relationship graph, family links, current intention, world time, birth/death totals, and recent history.

## Development

```bash
pytest
node --check site/app.js
```

FlyCity is an experimental autonomous-agent / artificial-life project. It prioritizes observable emergent behavior over biological fidelity.
