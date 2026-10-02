"""Comm-priority scheduler — Phase 1.7.

The PRD asks the system to "reason about limited communication... determine
which observations or data are important enough to transmit." This is distinct
from World.comm_graph() (which only answers "can A reach B at all"). This module
answers "given a constrained channel, what gets through this tick, and what waits
or gets dropped."
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.sim.events import EventType

# Lower number = higher priority. Mission-critical findings and failures must
# never be starved by routine telemetry.
PRIORITY_RANK: dict[EventType, int] = {
    EventType.TARGET_FOUND: 0,
    EventType.AGENT_FAILURE: 1,
    EventType.BATTERY_CRITICAL: 2,
    EventType.COMM_LOST: 3,
    EventType.COMM_RESTORED: 3,
    EventType.ROUTE_BLOCKED: 4,
    EventType.WEATHER_CHANGED: 5,
}
ROUTINE_TELEMETRY_RANK = 9  # anything not in the table above (e.g. position pings)


@dataclass
class CommMessage:
    agent_id: str
    event_type: EventType | None  # None => routine telemetry, not a typed event
    payload: dict = field(default_factory=dict)

    @property
    def priority(self) -> int:
        if self.event_type is None:
            return ROUTINE_TELEMETRY_RANK
        return PRIORITY_RANK.get(self.event_type, ROUTINE_TELEMETRY_RANK)


@dataclass
class ScheduleResult:
    sent: list[CommMessage]
    deferred: list[CommMessage]
    dropped: list[CommMessage]


class CommScheduler:
    """A per-agent bandwidth budget enforced every tick.

    `bandwidth_per_tick` models a degraded/relay-only link: only this many
    messages can physically get through per agent per tick. Deferred messages
    carry forward (up to `max_queue_depth`); anything beyond that is dropped,
    oldest-lowest-priority first, so a flooded queue never silently grows forever.
    """

    def __init__(self, bandwidth_per_tick: int = 2, max_queue_depth: int = 10):
        self.bandwidth_per_tick = bandwidth_per_tick
        self.max_queue_depth = max_queue_depth
        self._pending: dict[str, list[CommMessage]] = {}

    def enqueue(self, message: CommMessage) -> None:
        self._pending.setdefault(message.agent_id, []).append(message)

    def tick(self) -> dict[str, ScheduleResult]:
        """Run one scheduling pass for every agent with pending messages."""
        results: dict[str, ScheduleResult] = {}
        for agent_id, messages in list(self._pending.items()):
            ranked = sorted(messages, key=lambda m: m.priority)
            sent = ranked[: self.bandwidth_per_tick]
            remainder = ranked[self.bandwidth_per_tick :]

            carry = remainder[: self.max_queue_depth]
            dropped = remainder[self.max_queue_depth :]

            results[agent_id] = ScheduleResult(sent=sent, deferred=carry, dropped=dropped)
            if carry:
                self._pending[agent_id] = carry
            else:
                del self._pending[agent_id]
        return results

    def pending_count(self, agent_id: str) -> int:
        return len(self._pending.get(agent_id, []))
