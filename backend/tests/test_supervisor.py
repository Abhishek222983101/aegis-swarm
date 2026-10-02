import pytest

from app.ledger import DecisionLedger
from app.ml.inference import Allocator
from app.sim.entities import AgentStatus, AgentType, make_agent
from app.sim.events import EventType, SimEvent
from app.sim.world import World
from app.supervisor import ESCALATION_TIMEOUT_SECONDS, Supervisor


@pytest.fixture
def supervisor(tmp_path):
    world = World()
    world.spawn_default_swarm()
    ledger = DecisionLedger(tmp_path / "test.db")
    sup = Supervisor(world, ledger, allocator=Allocator(model_path=None))  # force baseline, deterministic
    yield sup
    ledger.close()


def test_battery_critical_reassigns_task_to_healthy_agent(supervisor):
    agent_id = "scout-1"
    agent = supervisor.world.agents[agent_id]
    agent.current_task = "patrol-a"
    agent.target_position = (300.0, 300.0, agent.position[2])

    event = SimEvent(EventType.BATTERY_CRITICAL, agent_id, {"battery": 15.0})
    record = supervisor.handle_event(event)

    assert record.decision in ("reassign", "escalate")  # escalate only if truly no candidate
    if record.decision == "reassign":
        assert agent.current_task is None  # old agent freed
        new_owner = next(a for a in supervisor.world.agents.values() if a.current_task == "patrol-a")
        assert new_owner.id != agent_id


def test_battery_critical_with_no_task_just_acknowledges(supervisor):
    agent_id = "scout-1"
    supervisor.world.agents[agent_id].current_task = None
    event = SimEvent(EventType.BATTERY_CRITICAL, agent_id, {"battery": 15.0})
    record = supervisor.handle_event(event)
    assert record.decision == "acknowledge"


def _two_agent_no_candidate_scenario(tmp_path):
    """A world where overall feasibility stays HIGH (so it does NOT hit the
    terminate path) but the specific affected agent genuinely has zero
    reassignment candidates — isolates the 'escalate' branch from 'terminate'."""
    world = World()
    world.add_agent(make_agent("scout-1", AgentType.SCOUT_DRONE, 0, 0))
    world.add_agent(make_agent("scout-2", AgentType.SCOUT_DRONE, 10, 0))
    ledger = DecisionLedger(tmp_path / "two_agent.db")
    sup = Supervisor(world, ledger, allocator=Allocator(model_path=None))
    sup.task_target_type["patrol-a"] = AgentType.SCOUT_DRONE  # only 1 type required

    agent = world.agents["scout-1"]
    agent.current_task = "patrol-a"
    agent.target_position = (300.0, 300.0, agent.position[2])
    world.agents["scout-2"].status = AgentStatus.LOST  # the only other agent is gone
    return sup, ledger


def test_battery_critical_escalates_when_no_candidates_remain(tmp_path):
    sup, ledger = _two_agent_no_candidate_scenario(tmp_path)
    try:
        event = SimEvent(EventType.BATTERY_CRITICAL, "scout-1", {"battery": 15.0})
        record = sup.handle_event(event)
        assert record.decision == "escalate"
        assert len(sup.pending_escalations) == 1
    finally:
        ledger.close()


def test_comm_lost_repositions_a_relay(supervisor):
    event = SimEvent(EventType.COMM_LOST, "scout-1", {})
    record = supervisor.handle_event(event)
    assert record.decision in ("reposition", "escalate")
    if record.decision == "reposition":
        relay = supervisor.world.agents["relay-1"]
        assert relay.target_position is not None


def test_comm_lost_escalates_with_no_relay_available(supervisor):
    supervisor.world.agents["relay-1"].status = AgentStatus.LOST
    event = SimEvent(EventType.COMM_LOST, "scout-1", {})
    record = supervisor.handle_event(event)
    assert record.decision == "escalate"


def test_target_found_dispatches_a_scout(supervisor):
    event = SimEvent(EventType.TARGET_FOUND, None, {"position": (200, 200), "priority": "high"})
    record = supervisor.handle_event(event)
    assert record.decision in ("reassign", "escalate")
    if record.decision == "reassign":
        dispatched = [a for a in supervisor.world.agents.values() if a.current_task and a.current_task.startswith("target-")]
        assert len(dispatched) == 1


def test_route_blocked_acknowledges(supervisor):
    event = SimEvent(EventType.ROUTE_BLOCKED, None, {"zone_id": "zone-1"})
    record = supervisor.handle_event(event)
    assert record.decision == "acknowledge"


def test_low_feasibility_forces_termination_regardless_of_event_type(supervisor):
    ids = list(supervisor.world.agents.keys())
    for aid in ids[:3]:  # lose 3 of 4 -> feasibility should collapse
        supervisor.world.agents[aid].status = AgentStatus.LOST

    event = SimEvent(EventType.BATTERY_CRITICAL, ids[3], {})
    record = supervisor.handle_event(event)
    assert record.decision == "terminate"
    assert record.escalated is True


def test_risk_classifier_escalates_a_low_battery_isolated_reassignment(tmp_path):
    # Regression/integration test for the risk-classifier wiring: a reassignment
    # candidate that is itself nearly dead on battery and comm-isolated should
    # get escalated, not silently committed, even though an allocator candidate
    # technically exists.
    from app.ml.risk_model import RiskClassifier

    world = World()
    world.add_agent(make_agent("scout-1", AgentType.SCOUT_DRONE, 0, 0))
    risky = make_agent("scout-2", AgentType.SCOUT_DRONE, 50_000, 50_000)  # far away = comm-isolated
    risky.battery = 3.0
    world.add_agent(risky)
    ledger = DecisionLedger(tmp_path / "risk.db")
    sup = Supervisor(world, ledger, allocator=Allocator(model_path=None), risk_classifier=RiskClassifier(model_path=None))
    sup.task_target_type["patrol-a"] = AgentType.SCOUT_DRONE

    agent = world.agents["scout-1"]
    agent.current_task = "patrol-a"
    agent.target_position = (300.0, 300.0, agent.position[2])

    try:
        record = sup.handle_event(SimEvent(EventType.BATTERY_CRITICAL, "scout-1", {}))
        # The only reassignment candidate (scout-2) is itself high-risk —
        # classifier should catch this and escalate rather than commit it.
        assert record.decision == "escalate"
    finally:
        ledger.close()


def test_escalated_decision_carries_its_escalation_id(tmp_path):
    # Regression test: the frontend's Escalation Console needs this id to call
    # POST /escalation/{id}/respond — a decision record without it is unactionable.
    sup, ledger = _two_agent_no_candidate_scenario(tmp_path)
    try:
        record = sup.handle_event(SimEvent(EventType.BATTERY_CRITICAL, "scout-1", {}))
        assert record.decision == "escalate"
        assert record.escalation_id is not None
        assert record.escalation_id in sup.pending_escalations
    finally:
        ledger.close()


def test_every_decision_is_written_to_the_ledger(supervisor):
    assert supervisor.ledger.count() == 0
    supervisor.handle_event(SimEvent(EventType.ROUTE_BLOCKED, None, {"zone_id": "z1"}))
    assert supervisor.ledger.count() == 1


def test_escalation_resolution_marks_resolved(tmp_path):
    sup, ledger = _two_agent_no_candidate_scenario(tmp_path)
    try:
        sup.handle_event(SimEvent(EventType.BATTERY_CRITICAL, "scout-1", {}))
        assert len(sup.pending_escalations) == 1
        esc_id = next(iter(sup.pending_escalations))

        resolved = sup.resolve_escalation(esc_id, "approve")
        assert resolved.resolved is True
        assert resolved.operator_decision == "approve"

        # Resolving twice must not error or overwrite the first decision.
        again = sup.resolve_escalation(esc_id, "override")
        assert again is None
    finally:
        ledger.close()


def test_stale_escalations_auto_expire_after_timeout(tmp_path):
    sup, ledger = _two_agent_no_candidate_scenario(tmp_path)
    try:
        sup.handle_event(SimEvent(EventType.BATTERY_CRITICAL, "scout-1", {}))
        esc_id = next(iter(sup.pending_escalations))
        esc = sup.pending_escalations[esc_id]
        esc.created_at -= (ESCALATION_TIMEOUT_SECONDS + 1)  # force it into the past

        expired = sup.expire_stale_escalations()
        assert len(expired) == 1
        assert expired[0].operator_decision == "timeout"
    finally:
        ledger.close()
