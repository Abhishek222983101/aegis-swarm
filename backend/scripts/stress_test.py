"""Stress test — Phase 6.4. Scale the simulation core well past the 4-agent
demo default and confirm it still ticks cleanly and the Supervisor still makes
sane decisions. Run standalone (not through the live API, which only spawns
the default 4) to isolate whether the CORE scales, independent of frontend
rendering performance (that's a separate, visual check in the browser).
"""
from __future__ import annotations

import time

from app.ledger import DecisionLedger
from app.ml.inference import Allocator
from app.sim.entities import AgentType, make_agent
from app.sim.events import EventType, SimEvent
from app.sim.world import World
from app.supervisor import Supervisor


def build_large_swarm(n_scouts: int, n_rovers: int, n_relays: int) -> World:
    world = World(width=800, height=800)
    i = 0
    for _ in range(n_scouts):
        world.add_agent(make_agent(f"scout-{i}", AgentType.SCOUT_DRONE, i * 30 % 800, (i * 53) % 800))
        i += 1
    for _ in range(n_rovers):
        world.add_agent(make_agent(f"rover-{i}", AgentType.HEAVY_ROVER, i * 30 % 800, (i * 53) % 800))
        i += 1
    for _ in range(n_relays):
        world.add_agent(make_agent(f"relay-{i}", AgentType.COMM_RELAY, i * 30 % 800, (i * 53) % 800))
        i += 1
    return world


def run(n_agents_label: str, n_scouts: int, n_rovers: int, n_relays: int, n_ticks: int = 200):
    total = n_scouts + n_rovers + n_relays
    world = build_large_swarm(n_scouts, n_rovers, n_relays)
    ledger = DecisionLedger(":memory:" if False else f"/tmp/stress_{total}.db")
    # Allocator gracefully falls back to Hungarian outside its trained 4-agent
    # envelope (verified by tests/test_inference.py) — expected and correct here.
    supervisor = Supervisor(world, ledger, allocator=Allocator())

    start = time.time()
    total_events = 0
    for tick in range(n_ticks):
        events = world.tick(dt=0.5)
        total_events += len(events)
        for event in events:
            supervisor.handle_event(event)

        # Inject a random fault every 20 ticks to exercise the decision path under load.
        if tick % 20 == 0 and tick > 0:
            agent_ids = list(world.agents.keys())
            target = agent_ids[tick % len(agent_ids)]
            agent = world.agents[target]
            if agent.status.value != "lost":
                agent.battery = min(agent.battery, 15.0)

    elapsed = time.time() - start
    comm_graph = world.comm_graph()  # the O(n^2) part — explicitly timed separately below
    comm_start = time.time()
    for _ in range(10):
        world.comm_graph()
    comm_elapsed = (time.time() - comm_start) / 10

    print(f"[{n_agents_label}] {total} agents, {n_ticks} ticks, {total_events} events, "
          f"{ledger.count()} decisions logged, {elapsed:.3f}s total "
          f"({elapsed / n_ticks * 1000:.2f}ms/tick avg), "
          f"comm_graph() alone: {comm_elapsed * 1000:.2f}ms/call")
    ledger.close()


if __name__ == "__main__":
    run("baseline (demo default)", 2, 1, 1)
    run("moderate", 6, 4, 2)
    run("stress", 10, 4, 2)
    run("heavy stress", 15, 6, 3)
