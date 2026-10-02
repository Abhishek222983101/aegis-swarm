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
