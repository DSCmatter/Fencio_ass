"""SQLite persistence for assessment state and attack history."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import AssessmentState, AttackRecord, utcnow

DEFAULT_ID = "default"


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assessments ("
                "id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS attacks ("
                "id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, category TEXT NOT NULL, "
                "data TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attacks_assessment "
                "ON attacks(assessment_id, created_at)"
            )

    def save(self, state: AssessmentState, assessment_id: str = DEFAULT_ID) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO assessments (id, data, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                (assessment_id, state.model_dump_json(), utcnow().isoformat()),
            )

    def load(self, assessment_id: str = DEFAULT_ID) -> AssessmentState | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM assessments WHERE id = ?", (assessment_id,)
            ).fetchone()
        if row is None:
            return None
        return AssessmentState.model_validate_json(row["data"])

    def append_attack(self, attack: AttackRecord, assessment_id: str = DEFAULT_ID) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO attacks (id, assessment_id, category, data, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    attack.id,
                    assessment_id,
                    attack.category.value,
                    attack.model_dump_json(),
                    attack.created_at.isoformat(),
                ),
            )

    def load_attacks(self, assessment_id: str = DEFAULT_ID) -> list[AttackRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM attacks WHERE assessment_id = ? ORDER BY created_at",
                (assessment_id,),
            ).fetchall()
        return [AttackRecord.model_validate_json(row["data"]) for row in rows]
