import math

import pytest

from app.sim.entities import AgentStatus, AgentType, make_agent
from app.sim.events import EventType
from app.sim.world import BATTERY_CRITICAL_THRESHOLD, Weather, World


def test_spawn_default_swarm_has_heterogeneous_agents():
    world = World()
    world.spawn_default_swarm()
    types = {a.type for a in world.agents.values()}
    assert len(types) == 3  # scout, rover, relay all present
    assert len(world.agents) == 4


def test_agents_have_distinct_capability_profiles():
    world = World()
    world.spawn_default_swarm()
    scout = next(a for a in world.agents.values() if a.type == AgentType.SCOUT_DRONE)
    rover = next(a for a in world.agents.values() if a.type == AgentType.HEAVY_ROVER)
    assert scout.spec.speed > rover.spec.speed
    assert rover.spec.payload_capacity > scout.spec.payload_capacity
    assert scout.position[2] > rover.position[2]  # drone flies above ground rover


def test_agent_moves_toward_target():
    world = World()
    agent = make_agent("a1", AgentType.HEAVY_ROVER, 0, 0)
    agent.position = (0, 0, 0)
    agent.target_position = (10, 0, 0)
    world.add_agent(agent)

    world.tick(dt=1.0)
    assert agent.position[0] > 0
    assert agent.position[0] <= 10


def test_agent_reaches_target_exactly_without_overshoot():
    world = World()
    agent = make_agent("a1", AgentType.HEAVY_ROVER, 0, 0)
    agent.position = (0, 0, 0)
    agent.target_position = (1, 0, 0)  # closer than one tick's travel distance
    world.add_agent(agent)

    world.tick(dt=1.0)
    assert agent.position == (1, 0, 0)
    assert agent.target_position is None


def test_battery_drains_over_ticks():
    world = World()
    agent = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    world.add_agent(agent)
    start = agent.battery
    for _ in range(5):
        world.tick(dt=1.0)
    assert agent.battery < start


def test_battery_critical_event_fires_once_on_threshold_crossing():
    world = World()
    agent = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    agent.battery = BATTERY_CRITICAL_THRESHOLD + 1
    world.add_agent(agent)

    events = world.tick(dt=5.0)  # enough drain to cross the threshold
    critical_events = [e for e in events if e.type == EventType.BATTERY_CRITICAL]
    assert len(critical_events) == 1

    # Ticking again while still below threshold must NOT re-fire the event.
    events2 = world.tick(dt=1.0)
    assert not any(e.type == EventType.BATTERY_CRITICAL for e in events2)


def test_agent_failure_on_battery_depletion():
    world = World()
    agent = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    agent.battery = 0.4
    world.add_agent(agent)

    events = world.tick(dt=5.0)
    assert agent.status == AgentStatus.LOST
    assert any(e.type == EventType.AGENT_FAILURE for e in events)


def test_lost_agent_does_not_move_or_drain_further():
    world = World()
    agent = make_agent("a1", AgentType.SCOUT_DRONE, 5, 5)
    agent.battery = 0.0
    agent.status = AgentStatus.LOST
    agent.target_position = (100, 100, 35)
    world.add_agent(agent)

    world.tick(dt=10.0)
    assert agent.position == (5, 5, 35)
    assert agent.battery == 0.0


def test_comm_graph_connects_agents_within_range():
    world = World()
    a = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    b = make_agent("a2", AgentType.SCOUT_DRONE, 10, 0)  # well within 180m range
    world.add_agent(a)
    world.add_agent(b)

    graph = world.comm_graph()
    assert "a2" in graph["a1"]
    assert "a1" in graph["a2"]


def test_comm_graph_disconnects_agents_out_of_range():
    world = World()
    a = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    b = make_agent("a2", AgentType.SCOUT_DRONE, 10_000, 0)
    world.add_agent(a)
    world.add_agent(b)

    graph = world.comm_graph()
    assert "a2" not in graph["a1"]


def test_comm_lost_event_fires_when_agent_goes_out_of_range():
    world = World()
    a = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    b = make_agent("a2", AgentType.SCOUT_DRONE, 10, 0)
    world.add_agent(a)
    world.add_agent(b)
    world.tick(dt=0.01)  # establish initial "connected" baseline

    a.position = (50_000, 50_000, a.position[2])
    events = world.tick(dt=0.01)
    assert any(e.type == EventType.COMM_LOST and e.agent_id == "a1" for e in events)


def test_severe_weather_reduces_effective_comm_range():
    world = World()
    a = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    b = make_agent("a2", AgentType.SCOUT_DRONE, 170, 0)  # inside 180m clear-weather range
    world.add_agent(a)
    world.add_agent(b)

    assert "a2" in world.comm_graph()["a1"]  # connected in clear weather

    world.weather = Weather.SEVERE  # multiplier 0.3 -> effective range 54m
    assert "a2" not in world.comm_graph()["a1"]


def test_state_snapshot_is_json_serializable_shape():
    world = World()
    world.spawn_default_swarm()
    snap = world.state_snapshot()
    assert "agents" in snap and len(snap["agents"]) == 4
    assert "comm_graph" in snap
    assert all(isinstance(v, list) for v in snap["comm_graph"].values())
