"""SQLite-backed decision log — the audit trail behind the Decision Feed.

Every autonomous decision the Supervisor makes is written here before it's
broadcast to the frontend. This is deliberately a plain append-only table, not
an ORM model with mutation methods — the whole point is that rows are never
edited after insert, only ever appended.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "aegis.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    trigger_event TEXT NOT NULL,
    agent_id TEXT,
    decision TEXT NOT NULL,
    reasoning_text TEXT NOT NULL,
    confidence_score REAL,
    escalated INTEGER NOT NULL DEFAULT 0,
    escalation_id TEXT
);
"""


@dataclass
class DecisionRecord:
    trigger_event: str
    decision: str
    reasoning_text: str
    agent_id: str | None = None
    confidence_score: float | None = None
    escalated: bool = False
    escalation_id: str | None = None  # set when decision == "escalate" — the id the
    # frontend's Escalation Console needs to call POST /escalation/{id}/respond
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "trigger_event": self.trigger_event,
            "agent_id": self.agent_id,
            "decision": self.decision,
            "reasoning_text": self.reasoning_text,
            "confidence_score": self.confidence_score,
            "escalated": self.escalated,
            "escalation_id": self.escalation_id,
            "timestamp": self.timestamp,
        }


class DecisionLedger:
    """Thin, dependency-free SQLite wrapper. One connection per instance,
    safe for a single-process asyncio app (SQLite serializes writes itself)."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, entry: DecisionRecord) -> int:
        cur = self._conn.execute(
            """INSERT INTO decision_log
               (timestamp, trigger_event, agent_id, decision, reasoning_text, confidence_score, escalated, escalation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.timestamp,
                entry.trigger_event,
                entry.agent_id,
                entry.decision,
                entry.reasoning_text,
                entry.confidence_score,
                int(entry.escalated),
                entry.escalation_id,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def recent(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            """SELECT timestamp, trigger_event, agent_id, decision, reasoning_text, confidence_score, escalated, escalation_id
               FROM decision_log ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        cols = [
            "timestamp", "trigger_event", "agent_id", "decision",
            "reasoning_text", "confidence_score", "escalated", "escalation_id",
        ]
        return [dict(zip(cols, row)) for row in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
