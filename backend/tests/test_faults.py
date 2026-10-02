import pytest

from app.sim.entities import AgentStatus, AgentType, make_agent
from app.sim.events import EventType
from app.sim.faults import (
    FaultTargetError,
    inject_agent_failure,
    inject_battery_drain,
    inject_comm_loss,
    inject_route_block,
    inject_target_found,
    inject_weather_change,
)
from app.sim.world import Weather, World


@pytest.fixture
def world():
    w = World()
    w.spawn_default_swarm()
    return w


def test_inject_battery_drain_drops_battery(world):
    agent_id = next(iter(world.agents))
    event = inject_battery_drain(world, agent_id, drop_to=10.0)
    assert world.agents[agent_id].battery <= 10.0
    assert event.type == EventType.BATTERY_CRITICAL


def test_inject_battery_drain_unknown_agent_raises(world):
    with pytest.raises(FaultTargetError):
        inject_battery_drain(world, "does-not-exist")


def test_inject_comm_loss_isolates_agent(world):
    agent_id = next(iter(world.agents))
    inject_comm_loss(world, agent_id)
    graph = world.comm_graph()
    assert len(graph[agent_id]) == 0


def test_inject_route_block_registers_zone(world):
    inject_route_block(world, "zone-1", 100, 100, radius=50)
    assert "zone-1" in world.blocked_zones
    assert world.blocked_zones["zone-1"].radius == 50


def test_inject_agent_failure_marks_lost(world):
    agent_id = next(iter(world.agents))
    event = inject_agent_failure(world, agent_id)
    assert world.agents[agent_id].status == AgentStatus.LOST
    assert world.agents[agent_id].battery == 0.0
    assert event.type == EventType.AGENT_FAILURE


def test_inject_weather_change_updates_world_weather(world):
    inject_weather_change(world, "severe")
    assert world.weather == Weather.SEVERE


def test_inject_weather_change_rejects_invalid_level(world):
    with pytest.raises(FaultTargetError):
        inject_weather_change(world, "tornado-of-doom")


def test_inject_target_found_returns_structural_event(world):
    event = inject_target_found(world, 50, 60, priority="high")
    assert event.type == EventType.TARGET_FOUND
    assert event.data["position"] == [50, 60]
