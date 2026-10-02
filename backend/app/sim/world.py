"""The simulation core — ticks the swarm, environment, and comm graph forward.

Single source of truth for all agent/environment state. Runs in-process inside
the FastAPI app via an asyncio background task (see app/main.py). Deliberately
synchronous/pure where possible so it's trivially unit-testable without a server.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum

from app.sim.entities import Agent, AgentStatus, AgentType, make_agent
from app.sim.events import EventType, SimEvent

BATTERY_CRITICAL_THRESHOLD = 20.0
BATTERY_FAILURE_THRESHOLD = 0.0


class Weather(str, Enum):
    CLEAR = "clear"
    DEGRADED = "degraded"
    SEVERE = "severe"


WEATHER_COMM_MULTIPLIER = {Weather.CLEAR: 1.0, Weather.DEGRADED: 0.6, Weather.SEVERE: 0.3}
WEATHER_DRAIN_MULTIPLIER = {Weather.CLEAR: 1.0, Weather.DEGRADED: 1.3, Weather.SEVERE: 1.8}


@dataclass
class BlockedZone:
    id: str
    center: tuple[float, float]
    radius: float


@dataclass
class World:
    width: float = 400.0
    height: float = 400.0
    agents: dict[str, Agent] = field(default_factory=dict)
    blocked_zones: dict[str, BlockedZone] = field(default_factory=dict)
    weather: Weather = Weather.CLEAR
    tick_count: int = 0
    _comm_connected_prev: dict[str, bool] = field(default_factory=dict)
    _battery_critical_emitted: set[str] = field(default_factory=set)

    # ---- setup -----------------------------------------------------------
    def spawn_default_swarm(self) -> None:
        self.add_agent(make_agent("scout-1", AgentType.SCOUT_DRONE, 40, 40))
        self.add_agent(make_agent("scout-2", AgentType.SCOUT_DRONE, 320, 60))
        self.add_agent(make_agent("rover-1", AgentType.HEAVY_ROVER, 180, 200))
        self.add_agent(make_agent("relay-1", AgentType.COMM_RELAY, 200, 150))

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.id] = agent
        self._comm_connected_prev[agent.id] = True

    # ---- per-tick physics --------------------------------------------------
    def tick(self, dt: float = 1.0) -> list[SimEvent]:
        """Advance the world by dt seconds. Returns events generated this tick."""
        self.tick_count += 1
        events: list[SimEvent] = []

        for agent in self.agents.values():
            if agent.status == AgentStatus.LOST:
                continue
            self._move_agent(agent, dt)
            events.extend(self._drain_battery(agent, dt))

        events.extend(self._update_comm_graph())
        return events

    def _move_agent(self, agent: Agent, dt: float) -> None:
        if agent.target_position is None:
            return
        tx, ty, tz = agent.target_position
        ax, ay, az = agent.position
        dx, dy, dz = tx - ax, ty - ay, tz - az
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        step = agent.spec.speed * dt
        if dist <= step or dist == 0:
            agent.position = agent.target_position
            agent.target_position = None
        else:
            ratio = step / dist
            agent.position = (ax + dx * ratio, ay + dy * ratio, az + dz * ratio)

    def _drain_battery(self, agent: Agent, dt: float) -> list[SimEvent]:
        events: list[SimEvent] = []
        drain = agent.spec.battery_drain_rate * WEATHER_DRAIN_MULTIPLIER[self.weather] * dt
        agent.battery = max(0.0, agent.battery - drain)

        if agent.battery <= BATTERY_FAILURE_THRESHOLD and agent.status != AgentStatus.LOST:
            agent.status = AgentStatus.LOST
            events.append(SimEvent(EventType.AGENT_FAILURE, agent.id, {"reason": "battery_depleted"}))
            return events

        if agent.battery <= BATTERY_CRITICAL_THRESHOLD and agent.id not in self._battery_critical_emitted:
            self._battery_critical_emitted.add(agent.id)
            agent.status = AgentStatus.DEGRADED
            events.append(SimEvent(EventType.BATTERY_CRITICAL, agent.id, {"battery": agent.battery}))
        elif agent.battery > BATTERY_CRITICAL_THRESHOLD and agent.id in self._battery_critical_emitted:
            self._battery_critical_emitted.discard(agent.id)
            if agent.status == AgentStatus.DEGRADED:
                agent.status = AgentStatus.NOMINAL
        return events

    # ---- communication graph ----------------------------------------------
    def comm_graph(self) -> dict[str, set[str]]:
        """Who-can-hear-whom, as an adjacency dict. Distance-based, weather-scaled."""
        graph: dict[str, set[str]] = {aid: set() for aid in self.agents}
        ids = list(self.agents.keys())
        multiplier = WEATHER_COMM_MULTIPLIER[self.weather]
        for i, a_id in enumerate(ids):
            a = self.agents[a_id]
            if a.status == AgentStatus.LOST:
                continue
            for b_id in ids[i + 1 :]:
                b = self.agents[b_id]
                if b.status == AgentStatus.LOST:
                    continue
                dist = _distance(a.position, b.position)
                effective_range = min(a.spec.comm_range, b.spec.comm_range) * multiplier
                if dist <= effective_range:
                    graph[a_id].add(b_id)
                    graph[b_id].add(a_id)
        return graph

    def _update_comm_graph(self) -> list[SimEvent]:
        events: list[SimEvent] = []
        graph = self.comm_graph()
        for agent_id, agent in self.agents.items():
            if agent.status == AgentStatus.LOST:
                continue
            connected = len(graph.get(agent_id, set())) > 0
            was_connected = self._comm_connected_prev.get(agent_id, True)
            if was_connected and not connected:
                agent.comm_lost = True
                events.append(SimEvent(EventType.COMM_LOST, agent_id, {}))
            elif not was_connected and connected:
                agent.comm_lost = False
                events.append(SimEvent(EventType.COMM_RESTORED, agent_id, {}))
            self._comm_connected_prev[agent_id] = connected
        return events

    def state_snapshot(self) -> dict:
        return {
            "tick": self.tick_count,
            "weather": self.weather.value,
            "agents": [a.to_dict() for a in self.agents.values()],
            "blocked_zones": [
                {"id": z.id, "center": list(z.center), "radius": z.radius}
                for z in self.blocked_zones.values()
            ],
            "comm_graph": {k: list(v) for k, v in self.comm_graph().items()},
        }


def _distance(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
