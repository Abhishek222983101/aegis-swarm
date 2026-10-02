"""Classical dispatch baselines — Greedy and Hungarian-optimal.

These exist for one reason: they're the comparison evidence that the trained
policy (policy.py) is measurably better than naive/classical approaches, not
just "an AI did something." Build and test these BEFORE the trained policy —
see BUILD-PLAN.md Phase 2.2. Do not skip or shortcut this file.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.ml.tasks import Task
from app.sim.entities import Agent, AgentStatus

UNREACHABLE_COST = 1e6  # capability mismatch / dead agent — effectively excluded


def _eligible(agent: Agent, task: Task) -> bool:
    if agent.status == AgentStatus.LOST:
        return False
    if task.required_type is not None and agent.type != task.required_type:
        return False
    return True


def _cost(agent: Agent, task: Task) -> float:
    if not _eligible(agent, task):
        return UNREACHABLE_COST
    ax, ay, _ = agent.position
    tx, ty = task.position
    dist = math.sqrt((ax - tx) ** 2 + (ay - ty) ** 2)
    # Lower battery agents are discouraged (but not excluded) from new assignments.
    battery_penalty = max(0.0, (40.0 - agent.battery)) * 0.5
    return dist + battery_penalty


def greedy_assign(tasks: list[Task], agents: list[Agent]) -> dict[str, str]:
    """Highest-priority task first, each gets its nearest eligible available agent."""
    assignment: dict[str, str] = {}
    taken: set[str] = set()
    for task in sorted(tasks, key=lambda t: -t.priority):
        candidates = [a for a in agents if a.id not in taken and _eligible(a, task)]
        if not candidates:
            continue
        best = min(candidates, key=lambda a: _cost(a, task))
        assignment[task.id] = best.id
        taken.add(best.id)
    return assignment


def hungarian_assign(tasks: list[Task], agents: list[Agent]) -> dict[str, str]:
    """Globally cost-minimal assignment via the Hungarian algorithm.

    Unlike greedy, this considers all tasks simultaneously, so it can produce a
    lower total-cost assignment when task priorities create competition for the
    same nearby agent. Falls back gracefully when tasks != agents in count
    (scipy's linear_sum_assignment handles rectangular matrices natively).
    """
    if not tasks or not agents:
        return {}

    cost_matrix = np.array([[_cost(a, t) for a in agents] for t in tasks])
    task_idx, agent_idx = linear_sum_assignment(cost_matrix)

    assignment: dict[str, str] = {}
    for ti, ai in zip(task_idx, agent_idx):
        if cost_matrix[ti, ai] >= UNREACHABLE_COST:
            continue  # no eligible agent existed for this task — leave unassigned
        assignment[tasks[ti].id] = agents[ai].id
    return assignment


def total_assignment_cost(assignment: dict[str, str], tasks: list[Task], agents: list[Agent]) -> float:
    """Sum of (pre-penalty) travel distance for a given assignment — the metric
    used in the Phase 6.2 baseline-comparison benchmark."""
    task_by_id = {t.id: t for t in tasks}
    agent_by_id = {a.id: a for a in agents}
    total = 0.0
    for task_id, agent_id in assignment.items():
        a, t = agent_by_id[agent_id], task_by_id[task_id]
        ax, ay, _ = a.position
        tx, ty = t.position
        total += math.sqrt((ax - tx) ** 2 + (ay - ty) ** 2)
    return total
