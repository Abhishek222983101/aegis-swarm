from app.ml.baselines import greedy_assign, hungarian_assign, total_assignment_cost
from app.ml.tasks import Task
from app.sim.entities import AgentStatus, AgentType, make_agent


def _agents():
    return [
        make_agent("scout-1", AgentType.SCOUT_DRONE, 0, 0),
        make_agent("scout-2", AgentType.SCOUT_DRONE, 100, 0),
        make_agent("rover-1", AgentType.HEAVY_ROVER, 50, 50),
    ]


def test_greedy_assigns_nearest_eligible_agent():
    agents = _agents()
    tasks = [Task("t1", (5, 0))]  # right next to scout-1
    assignment = greedy_assign(tasks, agents)
    assert assignment["t1"] == "scout-1"


def test_greedy_respects_capability_requirement():
    agents = _agents()
    tasks = [Task("t1", (1, 1), required_type=AgentType.HEAVY_ROVER)]
    assignment = greedy_assign(tasks, agents)
    assert assignment["t1"] == "rover-1"  # only eligible agent, despite not being nearest


def test_greedy_leaves_task_unassigned_if_no_eligible_agent():
    agents = _agents()
    tasks = [Task("t1", (1, 1), required_type=AgentType.COMM_RELAY)]
    assignment = greedy_assign(tasks, agents)
    assert "t1" not in assignment


def test_greedy_does_not_double_assign_an_agent():
    agents = [make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)]
    tasks = [Task("t1", (1, 0), priority=2), Task("t2", (2, 0), priority=1)]
    assignment = greedy_assign(tasks, agents)
    assert len(set(assignment.values())) == len(assignment)  # no agent used twice
    assert assignment.get("t1") == "a1"  # higher priority task wins the only agent


def test_hungarian_finds_lower_or_equal_total_cost_than_greedy():
    # A classic case where greedy's locally-nearest choice blocks a globally better one.
    agents = [
        make_agent("a1", AgentType.SCOUT_DRONE, 0, 0),
        make_agent("a2", AgentType.SCOUT_DRONE, 10, 0),
    ]
    tasks = [
        Task("t1", (1, 0), priority=1),   # very close to a1
        Task("t2", (9, 0), priority=1),   # very close to a2
    ]
    greedy = greedy_assign(tasks, agents)
    hungarian = hungarian_assign(tasks, agents)

    greedy_cost = total_assignment_cost(greedy, tasks, agents)
    hungarian_cost = total_assignment_cost(hungarian, tasks, agents)
    assert hungarian_cost <= greedy_cost


def test_hungarian_excludes_dead_agents():
    agents = _agents()
    agents[0].status = AgentStatus.LOST
    tasks = [Task("t1", (1, 1))]
    assignment = hungarian_assign(tasks, agents)
    assert assignment["t1"] != "scout-1"


def test_hungarian_handles_more_tasks_than_agents():
    agents = [make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)]
    tasks = [Task("t1", (1, 0)), Task("t2", (2, 0)), Task("t3", (3, 0))]
    assignment = hungarian_assign(tasks, agents)
    assert len(assignment) == 1  # only one agent to go around
    assert len(set(assignment.values())) == 1


def test_hungarian_handles_empty_inputs_without_crashing():
    assert hungarian_assign([], []) == {}
    assert hungarian_assign([Task("t1", (0, 0))], []) == {}
