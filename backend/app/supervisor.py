"""Supervisor Loop — the Nervous System. Consumes typed sim events and decides
what to do about each one. Decision space has exactly 4 actions per the PRD:
reassign, reposition, escalate, terminate.

Core decision logic (`handle_event`) is synchronous and framework-free so it's
fully unit-testable without asyncio or a running server. The async wrapper
that actually drives it off the live event queue lives in app/main.py.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.ledger import DecisionLedger, DecisionRecord
from app.ml.feasibility import compute_feasibility
from app.ml.inference import Allocator
from app.ml.tasks import Task
from app.sim.entities import AgentStatus, AgentType
from app.sim.events import EventType, SimEvent
from app.sim.world import World

RISK_ESCALATE_THRESHOLD = 0.45  # confidence below this -> escalate instead of act
ESCALATION_TIMEOUT_SECONDS = 15.0


@dataclass
class PendingEscalation:
    id: str
    event: SimEvent
    reasoning: str
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    operator_decision: str | None = None  # "approve" | "override" | None (timed out)

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.time()) - self.created_at > ESCALATION_TIMEOUT_SECONDS


class Supervisor:
    def __init__(self, world: World, ledger: DecisionLedger, allocator: Allocator | None = None):
        self.world = world
        self.ledger = ledger
        self.allocator = allocator or Allocator()
        self.pending_tasks: list[Task] = []
        self.task_target_type: dict[str, AgentType | None] = {}
        self.pending_escalations: dict[str, PendingEscalation] = {}
        self._escalation_seq = 0

    def required_agent_types(self) -> set[AgentType]:
        return {t for t in self.task_target_type.values() if t is not None} or set(AgentType)

    def handle_event(self, event: SimEvent) -> DecisionRecord:
        """The single decision entry point. Always returns a DecisionRecord —
        never raises, never leaves an event un-acted-on, even in the worst case."""
        feasibility = compute_feasibility(self.world, pending_task_types=self.required_agent_types())

        if feasibility.should_terminate:
            record = self._decide_terminate(event, feasibility)
        elif event.type in (EventType.BATTERY_CRITICAL, EventType.AGENT_FAILURE):
            record = self._decide_reassign(event, feasibility)
        elif event.type == EventType.COMM_LOST:
            record = self._decide_reposition(event, feasibility)
        elif event.type == EventType.TARGET_FOUND:
            record = self._decide_structural(event, feasibility)
        elif event.type == EventType.ROUTE_BLOCKED:
            record = self._decide_route_block(event, feasibility)
        else:
            record = DecisionRecord(
                trigger_event=event.type.value,
                decision="acknowledge",
                reasoning_text=f"{event.type.value} noted; no action required this tick "
                f"(feasibility {feasibility.score:.2f}).",
                agent_id=event.agent_id,
                confidence_score=feasibility.score,
            )

        self.ledger.record(record)
        return record

    # -- decision handlers ----------------------------------------------------
    def _decide_terminate(self, event: SimEvent, feasibility) -> DecisionRecord:
        return DecisionRecord(
            trigger_event=event.type.value,
            decision="terminate",
            reasoning_text=(
                f"Mission feasibility dropped to {feasibility.score:.2f} "
                f"(threshold 0.35) — {'; '.join(feasibility.reasons)}. "
                "Recommending termination of the affected sub-mission rather than "
                "continuing to reassign against an unachievable objective."
            ),
            agent_id=event.agent_id,
            confidence_score=feasibility.score,
            escalated=True,
        )

    def _decide_reassign(self, event: SimEvent, feasibility) -> DecisionRecord:
        agent = self.world.agents.get(event.agent_id) if event.agent_id else None
        task_id = agent.current_task if agent else None

        if not task_id:
            return DecisionRecord(
                trigger_event=event.type.value,
                decision="acknowledge",
                reasoning_text=f"{event.agent_id} affected but had no active task assigned — no reassignment needed.",
                agent_id=event.agent_id,
                confidence_score=feasibility.score,
            )

        candidates = [
            a for a in self.world.agents.values()
            if a.id != event.agent_id and a.status != AgentStatus.LOST
        ]
        required_type = self.task_target_type.get(task_id)
        task = Task(id=task_id, position=(agent.target_position or agent.position)[:2], required_type=required_type)

        if not candidates:
            return self._escalate(event, feasibility, "no healthy candidate agents remain to reassign to")

        assignment = self.allocator.allocate([task], candidates)
        new_agent_id = assignment.get(task_id)
        confidence = feasibility.score if new_agent_id else 0.1

        if not new_agent_id or confidence < RISK_ESCALATE_THRESHOLD:
            return self._escalate(
                event, feasibility,
                "no sufficiently confident reassignment found" if not new_agent_id
                else f"best reassignment found but confidence {confidence:.2f} below threshold",
            )

        # Commit the reassignment.
        new_agent = self.world.agents[new_agent_id]
        new_agent.current_task = task_id
        new_agent.target_position = (*task.position, new_agent.spec.cruise_altitude)
        if agent:
            agent.current_task = None

        return DecisionRecord(
            trigger_event=event.type.value,
            decision="reassign",
            reasoning_text=(
                f"{event.agent_id} ({event.type.value}) -> task '{task_id}' reassigned to "
                f"{new_agent_id} (backend: {self.allocator.backend}, confidence {confidence:.2f})."
            ),
            agent_id=event.agent_id,
            confidence_score=confidence,
        )

    def _decide_reposition(self, event: SimEvent, feasibility) -> DecisionRecord:
        isolated = self.world.agents.get(event.agent_id) if event.agent_id else None
        relay = next(
            (a for a in self.world.agents.values()
             if a.type == AgentType.COMM_RELAY and a.status != AgentStatus.LOST and a.id != event.agent_id),
            None,
        )
        if not isolated or not relay:
            return self._escalate(event, feasibility, "no available comm relay to reposition")

        ix, iy, _ = isolated.position
        rx, ry, rz = relay.position
        midpoint = ((ix + rx) / 2, (iy + ry) / 2, rz)
        relay.target_position = midpoint

        return DecisionRecord(
            trigger_event=event.type.value,
            decision="reposition",
            reasoning_text=(
                f"{event.agent_id} lost comm — repositioning {relay.id} toward midpoint "
                f"({midpoint[0]:.0f}, {midpoint[1]:.0f}) to restore the link."
            ),
            agent_id=event.agent_id,
            confidence_score=feasibility.score,
        )

    def _decide_structural(self, event: SimEvent, feasibility) -> DecisionRecord:
        x, y = event.data.get("position", (0, 0))
        task_id = f"target-{int(time.time() * 1000)}"
        task = Task(id=task_id, position=(x, y), required_type=AgentType.SCOUT_DRONE, priority=5)

        candidates = [a for a in self.world.agents.values() if a.status != AgentStatus.LOST]
        assignment = self.allocator.allocate([task], candidates)
        new_agent_id = assignment.get(task_id)

        if not new_agent_id:
            return self._escalate(event, feasibility, "high-priority target found but no agent available to investigate")

        agent = self.world.agents[new_agent_id]
        agent.current_task = task_id
        agent.target_position = (x, y, agent.spec.cruise_altitude)
        self.task_target_type[task_id] = AgentType.SCOUT_DRONE

        return DecisionRecord(
            trigger_event=event.type.value,
            decision="reassign",
            reasoning_text=(
                f"Structural replan (Mission Planner): high-priority target at ({x:.0f},{y:.0f}) "
                f"-> dispatched {new_agent_id} to investigate."
            ),
            confidence_score=feasibility.score,
        )

    def _decide_route_block(self, event: SimEvent, feasibility) -> DecisionRecord:
        zone = event.data
        return DecisionRecord(
            trigger_event=event.type.value,
            decision="acknowledge",
            reasoning_text=(
                f"Road/route blocked at zone {zone.get('zone_id')} — future task routing will "
                f"avoid this area; current feasibility {feasibility.score:.2f}."
            ),
            confidence_score=feasibility.score,
        )

    def _escalate(self, event: SimEvent, feasibility, reason: str) -> DecisionRecord:
        self._escalation_seq += 1
        esc_id = f"esc-{self._escalation_seq}"
        reasoning = f"Escalating to human operator: {reason} (feasibility {feasibility.score:.2f})."
        self.pending_escalations[esc_id] = PendingEscalation(id=esc_id, event=event, reasoning=reasoning)
        return DecisionRecord(
            trigger_event=event.type.value,
            decision="escalate",
            reasoning_text=reasoning,
            agent_id=event.agent_id,
            confidence_score=feasibility.score,
            escalated=True,
            escalation_id=esc_id,
        )

    # -- escalation resolution --------------------------------------------------
    def resolve_escalation(self, escalation_id: str, operator_decision: str) -> PendingEscalation | None:
        esc = self.pending_escalations.get(escalation_id)
        if esc is None or esc.resolved:
            return None
        esc.resolved = True
        esc.operator_decision = operator_decision
        return esc

    def expire_stale_escalations(self) -> list[PendingEscalation]:
        """Auto-resolves any escalation past its timeout so a demo never hard-freezes
        waiting for an operator click. Called every tick from the async loop."""
        expired = []
        now = time.time()
        for esc in self.pending_escalations.values():
            if not esc.resolved and esc.is_expired(now):
                esc.resolved = True
                esc.operator_decision = "timeout"
                expired.append(esc)
        return expired
