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
