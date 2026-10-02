import os

import pytest

from app.ml.planner import decompose_mission, decompose_mission_template
from app.sim.entities import AgentType


def test_scout_keyword_produces_scout_drone_task():
    plan = decompose_mission_template("Scout and survey Sector 7 for survivors")
    assert plan.source == "template"
    assert any(t.required_type == AgentType.SCOUT_DRONE for t in plan.tasks)


def test_sector_name_extracted_into_task_description():
    plan = decompose_mission_template("Patrol Sector 7 and report findings")
    assert any("Sector 7" in t.description for t in plan.tasks)


def test_rover_keyword_produces_transport_task_dependent_on_scout():
    plan = decompose_mission_template("Scout Zone 3, then deliver medical supplies there")
    rover_tasks = [t for t in plan.tasks if t.required_type == AgentType.HEAVY_ROVER]
    assert len(rover_tasks) == 1
    assert rover_tasks[0].depends_on  # transport should depend on the scout task


def test_relay_keyword_produces_comm_relay_task():
    plan = decompose_mission_template("Establish a communication relay over the valley")
    assert any(t.required_type == AgentType.COMM_RELAY for t in plan.tasks)


def test_objective_with_no_recognized_verbs_still_produces_a_task():
    plan = decompose_mission_template("asdkjqwoe random nonsense text")
    assert len(plan.tasks) >= 1  # never returns an empty plan


def test_decompose_mission_falls_back_to_template_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    plan = decompose_mission("Scout the northern ridge")
    assert plan.source == "template"


def test_decompose_mission_falls_back_on_llm_failure(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-that-will-fail")

    def broken_llm(objective: str):
        raise RuntimeError("simulated API failure")

    import app.ml.planner as planner_module
    monkeypatch.setattr(planner_module, "decompose_mission_llm", broken_llm)

    plan = decompose_mission("Scout the northern ridge")
    assert plan.source == "template"  # must not raise, must not return empty


def test_use_llm_false_always_uses_template_even_with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    plan = decompose_mission("Scout the ridge", use_llm=False)
    assert plan.source == "template"
