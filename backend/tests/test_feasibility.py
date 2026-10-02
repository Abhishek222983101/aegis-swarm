from app.ml.feasibility import TERMINATE_THRESHOLD, compute_feasibility
from app.sim.entities import AgentStatus, AgentType, make_agent
from app.sim.world import World


def test_nominal_swarm_has_high_feasibility():
    world = World()
    world.spawn_default_swarm()
    report = compute_feasibility(world)
    assert report.score > 0.8
    assert not report.should_terminate


def test_losing_most_agents_drops_feasibility_below_threshold():
    world = World()
    world.spawn_default_swarm()
    ids = list(world.agents.keys())
    for aid in ids[:3]:  # lose 3 of 4 agents
        world.agents[aid].status = AgentStatus.LOST
        world.agents[aid].battery = 0.0

    # Realistic context: the mission needs all 3 agent types, not just whichever
    # one happens to survive — this is what the Supervisor would actually pass.
    all_types = {AgentType.SCOUT_DRONE, AgentType.HEAVY_ROVER, AgentType.COMM_RELAY}
    report = compute_feasibility(world, pending_task_types=all_types)
    assert report.score < TERMINATE_THRESHOLD
    assert report.should_terminate


def test_report_explains_why_score_dropped():
    world = World()
    world.spawn_default_swarm()
    first_id = next(iter(world.agents))
    world.agents[first_id].status = AgentStatus.LOST

    report = compute_feasibility(world)
    assert any("lost" in r for r in report.reasons)


def test_missing_required_task_type_reduces_coverage_factor():
    world = World()
    world.spawn_default_swarm()
    for a in world.agents.values():
        if a.type == AgentType.COMM_RELAY:
            a.status = AgentStatus.LOST

    report = compute_feasibility(world, pending_task_types={AgentType.COMM_RELAY})
    assert report.task_coverage_factor == 0.0
    assert report.score < 1.0


def test_isolated_healthy_agent_reduces_connectivity_factor():
    world = World()
    a = make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)
    b = make_agent("a2", AgentType.SCOUT_DRONE, 50_000, 50_000)  # far out of range
    world.add_agent(a)
    world.add_agent(b)

    report = compute_feasibility(world)
    assert report.connectivity_factor < 1.0


def test_empty_swarm_is_zero_feasibility():
    world = World()
    report = compute_feasibility(world)
    assert report.score == 0.0
    assert report.should_terminate
