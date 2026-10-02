"""Scenario Injection API — the functions the judge-facing UI calls to break things live.

Each function mutates the World directly and returns the SimEvent it generated,
so the caller (a REST route) can immediately push it onto the event queue instead
of waiting for the next tick to notice. Keep these pure and dependency-free —
they're unit tested in isolation from FastAPI entirely.
"""
from __future__ import annotations

from app.sim.entities import AgentStatus
from app.sim.events import EventType, SimEvent
from app.sim.world import BlockedZone, Weather, World


class FaultTargetError(ValueError):
    """Raised when a fault is injected against an agent/zone that doesn't exist."""


def inject_battery_drain(world: World, agent_id: str, drop_to: float = 15.0) -> SimEvent:
    agent = _require_agent(world, agent_id)
    agent.battery = min(agent.battery, drop_to)
    return SimEvent(EventType.BATTERY_CRITICAL, agent_id, {"battery": agent.battery, "injected": True})


def inject_comm_loss(world: World, agent_id: str) -> SimEvent:
    agent = _require_agent(world, agent_id)
    agent.comm_lost = True
    world._comm_connected_prev[agent_id] = False
    # Push the agent physically out of everyone's range so the next tick confirms it.
    agent.position = (agent.position[0] + 5000, agent.position[1] + 5000, agent.position[2])
    return SimEvent(EventType.COMM_LOST, agent_id, {"injected": True})


def inject_route_block(world: World, zone_id: str, x: float, y: float, radius: float = 40.0) -> SimEvent:
    world.blocked_zones[zone_id] = BlockedZone(id=zone_id, center=(x, y), radius=radius)
    return SimEvent(EventType.ROUTE_BLOCKED, None, {"zone_id": zone_id, "center": [x, y], "radius": radius})


def inject_agent_failure(world: World, agent_id: str) -> SimEvent:
    agent = _require_agent(world, agent_id)
    agent.battery = 0.0
    agent.status = AgentStatus.LOST
    return SimEvent(EventType.AGENT_FAILURE, agent_id, {"reason": "injected", "injected": True})


def inject_weather_change(world: World, level: str) -> SimEvent:
    try:
        world.weather = Weather(level)
    except ValueError as exc:
        raise FaultTargetError(f"unknown weather level: {level}") from exc
    return SimEvent(EventType.WEATHER_CHANGED, None, {"level": level})


def inject_target_found(world: World, x: float, y: float, priority: str = "high") -> SimEvent:
    return SimEvent(EventType.TARGET_FOUND, None, {"position": [x, y], "priority": priority})


def _require_agent(world: World, agent_id: str):
    agent = world.agents.get(agent_id)
    if agent is None:
        raise FaultTargetError(f"no such agent: {agent_id}")
    return agent
