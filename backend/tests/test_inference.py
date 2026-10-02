from pathlib import Path

from app.ml.inference import Allocator
from app.ml.tasks import Task
from app.sim.entities import AgentType, make_agent


def test_allocator_falls_back_to_hungarian_when_no_model_present():
    allocator = Allocator(model_path="models/does-not-exist.onnx")
    assert allocator.backend == "hungarian_baseline"

    agents = [make_agent("a1", AgentType.SCOUT_DRONE, 0, 0)]
    tasks = [Task("t1", (1, 0))]
    assignment = allocator.allocate(tasks, agents)
    assert assignment["t1"] == "a1"


def test_allocator_with_none_model_path_uses_baseline():
    allocator = Allocator(model_path=None)
    assert allocator.backend == "hungarian_baseline"
    assert allocator.session is None


def test_allocator_never_crashes_on_empty_input():
    allocator = Allocator(model_path=None)
    assert allocator.allocate([], []) == {}


def test_trained_policy_falls_back_when_candidate_count_differs_from_training():
    # Regression test: the ONNX graph's input size is fixed at the exact
    # agent count it was trained with (AllocationEnv's n_agents). A live fault
    # (agent lost) shrinks the candidate pool below that at runtime constantly
    # — this must fall back to the baseline, not crash with a shape mismatch.
    import os

    onnx_path = Path(__file__).resolve().parent.parent / "models" / "allocator_policy.onnx"
    if not onnx_path.exists():
        import pytest as _pytest
        _pytest.skip("no trained model present in this environment")

    allocator = Allocator(model_path=onnx_path, trained_n_agents=4)
    assert allocator.backend == "trained_policy"

    # Fewer candidates than the model was trained on (3, not 4) — must not raise.
    agents = [make_agent(f"a{i}", AgentType.SCOUT_DRONE, i * 10, 0) for i in range(3)]
    tasks = [Task("t1", (5, 0))]
    assignment = allocator.allocate(tasks, agents)
    assert assignment["t1"] in {a.id for a in agents}


def test_trained_policy_handles_multi_task_batch_without_crashing():
    # Regression test: a multi-task allocate() call shrinks the candidate pool
    # as each task consumes an agent, which can fall outside the model's fixed
    # input size partway through the SAME call (found via live mission-dispatch
    # testing, not a unit test first) — must fall back per-task, not crash.
    import pytest as _pytest

    onnx_path = Path(__file__).resolve().parent.parent / "models" / "allocator_policy.onnx"
    if not onnx_path.exists():
        _pytest.skip("no trained model present in this environment")

    allocator = Allocator(model_path=onnx_path, trained_n_agents=4)
    agents = [
        make_agent("scout-1", AgentType.SCOUT_DRONE, 0, 0),
        make_agent("scout-2", AgentType.SCOUT_DRONE, 100, 0),
        make_agent("rover-1", AgentType.HEAVY_ROVER, 50, 50),
        make_agent("relay-1", AgentType.COMM_RELAY, 200, 200),
    ]
    tasks = [Task(f"t{i}", (i * 10, i * 10)) for i in range(3)]  # 3 tasks, 4 agents — pool shrinks each step
    assignment = allocator.allocate(tasks, agents)
    assert len(assignment) == 3
    assert len(set(assignment.values())) == 3  # no agent double-booked


def test_trained_policy_never_violates_capability_requirement():
    # Regression test: live-demo-observed bug — the trained policy sometimes
    # picked an ineligible agent type (e.g. a HeavyRover for a SCOUT_DRONE-only
    # task). This must be hard-constrained, not left to the model's judgment.
    import pytest as _pytest

    onnx_path = Path(__file__).resolve().parent.parent / "models" / "allocator_policy.onnx"
    if not onnx_path.exists():
        _pytest.skip("no trained model present in this environment")

    allocator = Allocator(model_path=onnx_path, trained_n_agents=4)
    assert allocator.backend == "trained_policy"

    agents = [
        make_agent("scout-1", AgentType.SCOUT_DRONE, 0, 0),
        make_agent("scout-2", AgentType.SCOUT_DRONE, 400, 400),
        make_agent("rover-1", AgentType.HEAVY_ROVER, 5, 5),  # deliberately closest to the task
        make_agent("relay-1", AgentType.COMM_RELAY, 10, 10),
    ]
    # Run many trials — the bug was intermittent (model preference, not deterministic crash).
    for trial in range(50):
        task = Task(f"t{trial}", (trial, trial), required_type=AgentType.SCOUT_DRONE)
        assignment = allocator.allocate([task], agents)
        chosen_id = assignment.get(task.id)
        if chosen_id:
            chosen = next(a for a in agents if a.id == chosen_id)
            assert chosen.type == AgentType.SCOUT_DRONE, (
                f"trial {trial}: policy chose {chosen.id} ({chosen.type}) for a scout_drone-only task"
            )
