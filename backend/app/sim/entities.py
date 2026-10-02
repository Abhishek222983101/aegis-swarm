"""Agent and entity definitions for the AEGIS swarm simulation.

Positions are always (x, y, z) in meters. z is altitude above ground (0 = ground
level). This 3-axis position is load-bearing for the frontend's 3D rendering —
see BUILD-PLAN.md Phase 4.9 (3D Audit). Do not collapse this to (x, y).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AgentType(str, Enum):
    SCOUT_DRONE = "scout_drone"
    HEAVY_ROVER = "heavy_rover"
    COMM_RELAY = "comm_relay"


class AgentStatus(str, Enum):
    NOMINAL = "nominal"
    DEGRADED = "degraded"
    LOST = "lost"


@dataclass
class AgentSpec:
    """Static capability profile for an agent type — what makes agents heterogeneous."""

    speed: float  # m/s
    battery_drain_rate: float  # % per tick while active
    payload_capacity: float  # abstract units
    comm_range: float  # meters
    cruise_altitude: float  # default z, meters (0 = ground-bound)
    max_battery: float = 100.0


# Capability profiles — deliberately distinct per PRD's "heterogeneous agents" requirement.
AGENT_SPECS: dict[AgentType, AgentSpec] = {
    AgentType.SCOUT_DRONE: AgentSpec(
        speed=12.0,
        battery_drain_rate=0.45,
        payload_capacity=1.0,
        comm_range=180.0,
        cruise_altitude=35.0,
    ),
    AgentType.HEAVY_ROVER: AgentSpec(
        speed=3.5,
        battery_drain_rate=0.12,
        payload_capacity=8.0,
        comm_range=120.0,
        cruise_altitude=0.0,
    ),
    AgentType.COMM_RELAY: AgentSpec(
        speed=2.0,
        battery_drain_rate=0.08,
        payload_capacity=0.5,
        comm_range=320.0,
        cruise_altitude=18.0,
    ),
}


@dataclass
class Agent:
    id: str
    type: AgentType
    position: tuple[float, float, float]
    battery: float = 100.0
    status: AgentStatus = AgentStatus.NOMINAL
    current_task: str | None = None
    target_position: tuple[float, float, float] | None = None
    comm_lost: bool = False

    @property
    def spec(self) -> AgentSpec:
        return AGENT_SPECS[self.type]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "position": list(self.position),
            "battery": round(self.battery, 1),
            "status": self.status.value,
            "current_task": self.current_task,
            "comm_lost": self.comm_lost,
            "comm_range": self.spec.comm_range,
        }


def make_agent(agent_id: str, agent_type: AgentType, x: float, y: float) -> Agent:
    """Spawn an agent at (x, y) using its type's default cruise altitude for z."""
    spec = AGENT_SPECS[agent_type]
    return Agent(id=agent_id, type=agent_type, position=(x, y, spec.cruise_altitude))
