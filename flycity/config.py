from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    db_path: str = os.getenv("FLYCITY_DB", "state/flycity.sqlite3")
    tick_seconds: float = float(os.getenv("FLYCITY_TICK_SECONDS", "1.0"))
    snapshot_seconds: float = float(os.getenv("FLYCITY_SNAPSHOT_SECONDS", "10"))
    world_minutes_per_real_second: float = float(os.getenv("FLYCITY_WORLD_MINUTES_PER_REAL_SECOND", "6"))
    initial_population: int = int(os.getenv("FLYCITY_INITIAL_POPULATION", "100"))
    population_cap: int = int(os.getenv("FLYCITY_POPULATION_CAP", "140"))
    llm_enabled: bool = _truthy("FLYCITY_LLM_ENABLED", True)
    llm_model: str = os.getenv("FLYCITY_MODEL", "gpt-5.6-luna")
    llm_calls_per_minute: int = int(os.getenv("FLYCITY_LLM_CALLS_PER_MINUTE", "60"))
    llm_min_decision_seconds: float = float(os.getenv("FLYCITY_LLM_MIN_DECISION_SECONDS", "75"))
    llm_max_decision_seconds: float = float(os.getenv("FLYCITY_LLM_MAX_DECISION_SECONDS", "150"))
    seed: int = int(os.getenv("FLYCITY_SEED", "1337"))


settings = Settings()
