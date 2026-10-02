"""Mission-level feasibility scoring — Phase 2.6b.

Deliberately NOT a neural net: the PRD asks the system to distinguish "this one
decision is risky" (risk_model.py, a real trained classifier) from "the whole
mission may no longer be achievable" (this module, a transparent weighted
aggregate). A hand-tuned, auditable formula is the RIGHT choice here, not a
missed opportunity to train something — an operator needs to be able to see
exactly why mission feasibility dropped, and a black-box score would undermine
the explainability requirement this whole system is built around.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.sim.entities import AgentStatus
from app.sim.world import World

TERMINATE_THRESHOLD = 0.35  # below this, Supervisor should consider aborting


@dataclass
class FeasibilityReport:
    score: float  # 0.0 (mission not achievable) .. 1.0 (fully nominal)
    agent_health_factor: float
    task_coverage_factor: float
    connectivity_factor: float
    reasons: list[str]

    @property
    def should_terminate(self) -> bool:
        return self.score < TERMINATE_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "agent_health_factor": round(self.agent_health_factor, 3),
            "task_coverage_factor": round(self.task_coverage_factor, 3),
            "connectivity_factor": round(self.connectivity_factor, 3),
            "should_terminate": self.should_terminate,
            "reasons": self.reasons,
        }


def compute_feasibility(world: World, pending_task_types: set | None = None) -> FeasibilityReport:
    """Aggregate swarm-wide state into one explainable 0..1 feasibility score.

    agent_health_factor:  fraction of agents still operational (not LOST)
    task_coverage_factor: fraction of still-required agent TYPES that have at
                           least one healthy representative left in the swarm
    connectivity_factor:  fraction of healthy agents that have at least one
                           comm link (fully isolated agents can't coordinate)
    """
    reasons: list[str] = []
    agents = list(world.agents.values())
    if not agents:
        return FeasibilityReport(0.0, 0.0, 0.0, 0.0, ["no agents in swarm"])

    healthy = [a for a in agents if a.status != AgentStatus.LOST]
    agent_health_factor = len(healthy) / len(agents)
    if agent_health_factor < 1.0:
        reasons.append(f"{len(agents) - len(healthy)}/{len(agents)} agents lost")

    if pending_task_types:
        healthy_types = {a.type for a in healthy}
        covered = pending_task_types & healthy_types
        task_coverage_factor = len(covered) / len(pending_task_types)
        if task_coverage_factor < 1.0:
            missing = pending_task_types - healthy_types
            reasons.append(f"no healthy agent left for task types: {sorted(t.value for t in missing)}")
    else:
        task_coverage_factor = 1.0

    if healthy:
        graph = world.comm_graph()
        connected = sum(1 for a in healthy if len(graph.get(a.id, set())) > 0)
        connectivity_factor = connected / len(healthy)
        if connectivity_factor < 1.0:
            reasons.append(f"{len(healthy) - connected}/{len(healthy)} healthy agents comm-isolated")
    else:
        connectivity_factor = 0.0

    # Weighted blend — agent health matters most (no agents = no mission),
    # task coverage next (wrong agents left = mission drifting off-objective),
    # connectivity last (recoverable via repositioning, the other two are not).
    score = 0.5 * agent_health_factor + 0.3 * task_coverage_factor + 0.2 * connectivity_factor

    if not reasons:
        reasons.append("nominal")

    return FeasibilityReport(score, agent_health_factor, task_coverage_factor, connectivity_factor, reasons)
