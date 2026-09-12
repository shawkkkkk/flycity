from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SnapshotStore:
    def __init__(self, path: str):
        self.path = path
        parent = Path(path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS snapshot (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        self.conn.commit()

    def load(self) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT payload FROM snapshot WHERE id=1").fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def save(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        with self.conn:
            self.conn.execute(
                "INSERT INTO snapshot(id,payload,updated_at) VALUES(1,?,CURRENT_TIMESTAMP) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP",
                (data,),
            )

    def close(self) -> None:
        self.conn.close()
