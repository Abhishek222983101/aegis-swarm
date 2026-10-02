"""Gymnasium environment wrapping the sequential task-allocation problem.

One episode = a batch of tasks presented one at a time; the agent (policy)
picks which swarm member handles each task. This is intentionally simpler than
simulating full physics per RL step — training needs thousands of fast episodes,
not real-time ticks. The World/tick-loop (app/sim/world.py) is the real-time
layer used at inference/demo time; this env is a fast, decoupled training
proxy over the same underlying cost structure (app/ml/baselines._cost).

Reward design rewards exactly what BUILD-PLAN.md Phase 2.3 specifies: mission
completion, minus travel cost, minus losing agents to bad (over-drained) choices.
"""
from __future__ import annotations

import math
import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from app.ml.encoding import AGENT_TYPES, N_AGENT_TYPES, WORLD_SIZE
from app.ml.tasks import Task
from app.sim.entities import AGENT_SPECS, AgentStatus, AgentType, make_agent


class AllocationEnv(gym.Env):
    """Fixed swarm of `n_agents`, a stream of `tasks_per_episode` tasks.

    Observation (flat float32 vector): for each agent — [dx, dy to current task
    (normalized), battery/100, one-hot type (3), alive flag] + [current task
    priority/5, current task requires-type one-hot (3, zero if any-type)].

    Action: Discrete(n_agents) — which agent handles the current task.
    """

    metadata = {"render_modes": []}

    def __init__(self, n_agents: int = 4, tasks_per_episode: int = 8, seed: int | None = None):
        super().__init__()
        self.n_agents = n_agents
        self.tasks_per_episode = tasks_per_episode
        self._rng = random.Random(seed)

        per_agent_dims = 2 + 1 + N_AGENT_TYPES + 1  # dx,dy,battery,type-onehot,alive
        task_dims = 1 + N_AGENT_TYPES  # priority, required-type-onehot
        obs_dim = self.n_agents * per_agent_dims + task_dims

        self.observation_space = spaces.Box(low=-5.0, high=5.0, shape=(obs_dim,), dtype=np.float32)
        self.action_space = spaces.Discrete(self.n_agents)

        self.agents: list = []
        self.tasks: list[Task] = []
        self._task_idx = 0
        self._completed = 0

    # -- gym API -------------------------------------------------------------
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = random.Random(seed)

        self.agents = []
        for i in range(self.n_agents):
            agent_type = AGENT_TYPES[i % N_AGENT_TYPES]
            x, y = self._rng.uniform(0, WORLD_SIZE), self._rng.uniform(0, WORLD_SIZE)
            agent = make_agent(f"agent-{i}", agent_type, x, y)
            agent.battery = self._rng.uniform(55.0, 100.0)
            self.agents.append(agent)

        self.tasks = [
            Task(
                id=f"task-{i}",
                position=(self._rng.uniform(0, WORLD_SIZE), self._rng.uniform(0, WORLD_SIZE)),
                required_type=self._rng.choice([None, None, self._rng.choice(AGENT_TYPES)]),
                priority=self._rng.randint(1, 5),
            )
            for i in range(self.tasks_per_episode)
        ]
        # Deliberately make one agent start critically low on battery per episode
        # (realistic — a swarm mid-mission always has some agent further along
        # its battery curve) so there are real, learnable trade-off scenarios
        # where "nearest agent" is the wrong call, not just noise around a
        # reward surface that greedy already nearly solves.
        if self.agents:
            self._rng.choice(self.agents).battery = self._rng.uniform(8.0, 22.0)
        self._task_idx = 0
        self._completed = 0
        return self._observe(), {}

    def step(self, action: int):
        task = self.tasks[self._task_idx]
        agent = self.agents[action]
        reward = self._reward(agent, task)

        if agent.status != AgentStatus.LOST:
            spec = AGENT_SPECS[agent.type]
            dist = self._distance(agent, task)
            agent.battery = max(0.0, agent.battery - spec.battery_drain_rate * (dist / max(spec.speed, 0.1)))
            if agent.battery <= 0:
                agent.status = AgentStatus.LOST
            self._completed += 1

        self._task_idx += 1
        terminated = self._task_idx >= self.tasks_per_episode
        obs = self._observe() if not terminated else np.zeros(self.observation_space.shape, dtype=np.float32)
        info = {"completed": self._completed, "total": self.tasks_per_episode}
        return obs, reward, terminated, False, info

    # -- reward shaping --------------------------------------------------------
    def _reward(self, agent, task: Task) -> float:
        if agent.status == AgentStatus.LOST:
            return -8.0  # assigning a dead agent is always wrong

        eligible = task.required_type is None or agent.type == task.required_type
        if not eligible:
            return -5.0  # capability mismatch — never acceptable

        dist = self._distance(agent, task)
        normalized_dist = dist / (WORLD_SIZE * math.sqrt(2))
        distance_penalty = normalized_dist * 2.0

        # Steep, not linear: a critically-low-battery agent carries a penalty on
        # the same order as the worst-case distance penalty, so the optimal
        # policy sometimes must prefer a farther, healthier agent — a real
        # trade-off a nearest-agent-only heuristic structurally can't make.
        if agent.battery < 25.0:
            battery_bonus = -1.6 * (1 - agent.battery / 25.0)
        else:
            battery_bonus = (agent.battery / 100.0) * 0.5

        priority_bonus = (task.priority / 5.0) * 0.5  # prioritize urgent tasks going well

        return 1.0 - distance_penalty + battery_bonus + priority_bonus

    def _distance(self, agent, task: Task) -> float:
        ax, ay, _ = agent.position
        tx, ty = task.position
        return math.sqrt((ax - tx) ** 2 + (ay - ty) ** 2)

    # -- observation encoding --------------------------------------------------
    def _observe(self) -> np.ndarray:
        task = self.tasks[self._task_idx]
        parts = []
        for agent in self.agents:
            ax, ay, _ = agent.position
            tx, ty = task.position
            dx = (tx - ax) / WORLD_SIZE
            dy = (ty - ay) / WORLD_SIZE
            type_onehot = [1.0 if agent.type == t else 0.0 for t in AGENT_TYPES]
            alive = 0.0 if agent.status == AgentStatus.LOST else 1.0
            parts.extend([dx, dy, agent.battery / 100.0, *type_onehot, alive])

        req_onehot = [0.0] * N_AGENT_TYPES
        if task.required_type is not None:
            req_onehot[AGENT_TYPES.index(task.required_type)] = 1.0
        parts.extend([task.priority / 5.0, *req_onehot])

        return np.array(parts, dtype=np.float32)
