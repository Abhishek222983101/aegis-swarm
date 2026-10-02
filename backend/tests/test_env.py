import numpy as np

from app.ml.env import AllocationEnv


def test_reset_returns_correctly_shaped_observation():
    env = AllocationEnv(n_agents=4, tasks_per_episode=6, seed=0)
    obs, info = env.reset()
    assert obs.shape == env.observation_space.shape
    assert env.observation_space.contains(obs)


def test_episode_terminates_after_all_tasks():
    env = AllocationEnv(n_agents=3, tasks_per_episode=5, seed=1)
    env.reset()
    terminated = False
    steps = 0
    while not terminated and steps < 100:
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        steps += 1
    assert terminated
    assert steps == 5


def test_assigning_capability_mismatched_agent_is_penalized():
    env = AllocationEnv(n_agents=4, tasks_per_episode=1, seed=42)
    env.reset()
    task = env.tasks[0]
    task.required_type = env.agents[0].type
    # Find an agent of a DIFFERENT type to force a mismatch
    mismatched_idx = next(i for i, a in enumerate(env.agents) if a.type != task.required_type)
    _, reward, _, _, _ = env.step(mismatched_idx)
    assert reward < 0


def test_nearest_eligible_agent_scores_higher_than_farthest():
    env = AllocationEnv(n_agents=4, tasks_per_episode=1, seed=7)
    env.reset()
    task = env.tasks[0]
    task.required_type = None  # any agent eligible, isolate the distance effect

    rewards = []
    for i, agent in enumerate(env.agents):
        agent.battery = 80.0  # equalize battery so only distance varies
        dx = agent.position[0] - task.position[0]
        dy = agent.position[1] - task.position[1]
        rewards.append(((dx**2 + dy**2) ** 0.5, i))
    rewards.sort()
    nearest_idx = rewards[0][1]
    farthest_idx = rewards[-1][1]

    env2 = AllocationEnv(n_agents=4, tasks_per_episode=1, seed=7)
    env2.reset()
    for a in env2.agents:
        a.battery = 80.0
    env2.tasks[0].required_type = None
    _, r_near, _, _, _ = env2.step(nearest_idx)

    env3 = AllocationEnv(n_agents=4, tasks_per_episode=1, seed=7)
    env3.reset()
    for a in env3.agents:
        a.battery = 80.0
    env3.tasks[0].required_type = None
    _, r_far, _, _, _ = env3.step(farthest_idx)

    assert r_near >= r_far


def test_seeded_reset_is_deterministic():
    env_a = AllocationEnv(seed=123)
    env_b = AllocationEnv(seed=123)
    obs_a, _ = env_a.reset(seed=123)
    obs_b, _ = env_b.reset(seed=123)
    np.testing.assert_array_almost_equal(obs_a, obs_b)
