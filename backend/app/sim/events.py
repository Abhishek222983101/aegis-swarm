"""Typed simulation events — what the Supervisor Loop (Phase 3) consumes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    BATTERY_CRITICAL = "battery_critical"
    COMM_LOST = "comm_lost"
    COMM_RESTORED = "comm_restored"
    ROUTE_BLOCKED = "route_blocked"
    AGENT_FAILURE = "agent_failure"
    WEATHER_CHANGED = "weather_changed"
    TARGET_FOUND = "target_found"


@dataclass
class SimEvent:
    type: EventType
    agent_id: str | None = None
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }
