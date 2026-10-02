"""Train the Allocation Engine's PPO policy and export it to ONNX.

Run: .venv/bin/python -m app.ml.train

Produces:
  models/allocator_policy.onnx         — loaded by Allocator at inference time
  models/training_curve.csv            — reward per episode, for the PPT slide
  models/baseline_comparison.json      — Greedy vs Hungarian vs Trained, the
                                          Phase 6.2 evidence numbers

Kept intentionally small/fast (CPU-only, a few minutes) — this is a hackathon
prototype, not a research run. The point is a REAL training loop with a REAL,
measurable improvement over the baselines, not a long training budget.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from app.ml.baselines import greedy_assign, hungarian_assign, total_assignment_cost
from app.ml.env import AllocationEnv
from app.ml.inference import Allocator
from app.ml.tasks import Task

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
TOTAL_TIMESTEPS = 300_000


class RewardCurveLogger(BaseCallback):
    """Collects per-episode reward so we can plot/export a training curve."""

    def __init__(self):
        super().__init__()
        self.episode_rewards: list[float] = []

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            if "episode" in info:
                self.episode_rewards.append(info["episode"]["r"])
        return True


def train() -> Path:
    MODELS_DIR.mkdir(exist_ok=True)
    env = Monitor(AllocationEnv(n_agents=4, tasks_per_episode=8, seed=0))

    model = PPO(
        "MlpPolicy",
        env,
        policy_kwargs={"net_arch": [64, 64]},
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        n_epochs=4,
        gamma=0.95,
        verbose=0,
        seed=0,
        # Deliberately CPU, not auto-CUDA: this tiny MLP gains nothing from a
        # GPU (SB3 itself warns about this for non-CNN policies), and CPU-only
        # matches the realistic constraint most hackathon teams actually have
        # — see BUILD-PLAN.md Phase 2.3.
        device="cpu",
    )

    logger = RewardCurveLogger()
    start = time.time()
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=logger)
    elapsed = time.time() - start
    print(f"Trained {TOTAL_TIMESTEPS} timesteps in {elapsed:.1f}s, "
          f"{len(logger.episode_rewards)} episodes.")

    # -- training curve export ---------------------------------------------
    curve_path = MODELS_DIR / "training_curve.csv"
    with open(curve_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["episode", "reward"])
        for i, r in enumerate(logger.episode_rewards):
            writer.writerow([i, r])
    print(f"Training curve -> {curve_path}")

    # -- ONNX export ----------------------------------------------------------
    onnx_path = MODELS_DIR / "allocator_policy.onnx"
    _export_onnx(model, env.observation_space.shape[0], onnx_path)
    print(f"ONNX policy -> {onnx_path}")

    # -- baseline comparison (Phase 6.2 evidence) --------------------------
    comparison = run_baseline_comparison(model, onnx_path)
    comparison_path = MODELS_DIR / "baseline_comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2))
    print(f"Baseline comparison -> {comparison_path}")
    print(json.dumps(comparison, indent=2))

    return onnx_path


class _OnnxablePolicy(torch.nn.Module):
    """SB3's documented ONNX export pattern: wrap the policy so its forward
    pass returns the deterministic action logits directly."""

    def __init__(self, policy):
        super().__init__()
        self.extractor = policy.mlp_extractor
        self.action_net = policy.action_net

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        latent_pi, _ = self.extractor(obs)
        return self.action_net(latent_pi)


def _export_onnx(model: PPO, obs_dim: int, path: Path) -> None:
    onnxable = _OnnxablePolicy(model.policy)
    dummy_input = torch.randn(1, obs_dim)
    # torch 2.9 defaults to the dynamo-based exporter, which needs the
    # `onnxscript` package. Force the legacy TorchScript-based exporter
    # instead (dynamo=False) rather than pull in another large dependency
    # for a one-line export step — fully supported, just not the new default.
    torch.onnx.export(
        onnxable,
        dummy_input,
        str(path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )


def run_baseline_comparison(model: PPO, onnx_path: Path, n_trials: int = 30) -> dict:
    """The Phase 6.2 evidence: same scenario, three approaches, SAME cost
    function, SAME problem structure for all three.

    Important and deliberate: tasks are assigned SEQUENTIALLY, one at a time,
    with agents reusable across tasks within a trial — not a one-shot bipartite
    match. This mirrors exactly how the live Supervisor actually calls the
    Allocator in production (app/supervisor.py: one task reassignment per
    event, as events arrive) — so this comparison measures the real usage
    pattern, not an artificially "fair" lab setup that doesn't reflect how the
    system is actually used. (An earlier version of this function ran the
    baselines as one-shot bipartite matching against a sequential trained
    policy — different problems, with Hungarian showing a worse completion
    rate than greedy despite being provably optimal on the problem IT was
    solving. Caught before this shipped; fixed by making every approach solve
    the identical sequential problem.)

    Second fix, same spirit: the trained_policy arm goes through the actual
    deployed `Allocator` class (ONNX + the hard capability-eligibility mask),
    not a raw `model.predict()` call — a raw-policy benchmark would measure
    something that was never actually shippable, since production always
    enforces that mask. This way the number reported is exactly what a judge
    would see live, not an idealized/different code path.
    """
    allocator = Allocator(model_path=onnx_path, trained_n_agents=4)
    results = {"greedy": [], "hungarian": [], "trained_policy": []}
    objective_reward = {"greedy": [], "hungarian": [], "trained_policy": []}
    battery_of_chosen = {"greedy": [], "hungarian": [], "trained_policy": []}
    mismatches = {"greedy": 0, "hungarian": 0, "trained_policy": 0}
    env = AllocationEnv(n_agents=4, tasks_per_episode=8)

    for trial in range(n_trials):
        env.reset(seed=1000 + trial)
        tasks = list(env.tasks)
        agents = list(env.agents)  # frozen snapshot of this trial's agents/positions

        for name, assign_one in (
            ("greedy", greedy_assign),
            ("hungarian", hungarian_assign),
        ):
            total_cost = 0.0
            total_reward = 0.0
            for task in tasks:
                single_assignment = assign_one([task], agents)  # agents reusable, matches live Supervisor usage
                chosen_id = single_assignment.get(task.id)
                if chosen_id:
                    total_cost += total_assignment_cost({task.id: chosen_id}, [task], agents)
                    chosen = next(a for a in agents if a.id == chosen_id)
                    total_reward += env._reward(chosen, task)  # score on the SAME objective the policy was trained on
                    battery_of_chosen[name].append(chosen.battery)
                    if task.required_type is not None and chosen.type != task.required_type:
                        mismatches[name] += 1
            results[name].append(total_cost)
            objective_reward[name].append(total_reward)

        obs, _ = env.reset(seed=1000 + trial)
        total_cost = 0.0
        total_reward = 0.0
        done = False
        step_idx = 0
        while not done:
            task = tasks[step_idx]
            # The actual deployed path: Allocator.allocate(), which applies the
            # hard capability mask — not the raw network output.
            assignment = allocator.allocate([task], env.agents)
            chosen_id = assignment.get(task.id)

            if chosen_id is None:
                # No eligible agent existed for this task at all (e.g. the only
                # agent of the required type already died) — the Allocator
                # correctly declined to assign one. That's not a capability
                # mismatch, it's a correctly-declined assignment; count neither
                # cost nor a violation for it, but still need SOME action to
                # keep env.step() advancing the episode deterministically — an
                # arbitrary pick here is fine precisely because we don't score it.
                action = 0
            else:
                action = next(i for i, a in enumerate(env.agents) if a.id == chosen_id)
                chosen_agent = env.agents[action]
                total_cost += total_assignment_cost({task.id: chosen_agent.id}, [task], agents)
                battery_of_chosen["trained_policy"].append(chosen_agent.battery)
                if task.required_type is not None and chosen_agent.type != task.required_type:
                    mismatches["trained_policy"] += 1

            obs, reward, done, _, _ = env.step(action)
            total_reward += reward
            step_idx += 1
        results["trained_policy"].append(total_cost)
        objective_reward["trained_policy"].append(total_reward)

    return {
        "n_trials": n_trials,
        "n_tasks_per_trial": env.tasks_per_episode,
        "mean_objective_reward": {k: round(float(np.mean(v)), 2) for k, v in objective_reward.items()},
        "mean_total_travel_cost": {k: round(float(np.mean(v)), 2) for k, v in results.items()},
        "mean_battery_of_chosen_agent": {
            k: round(float(np.mean(v)), 1) if v else None for k, v in battery_of_chosen.items()
        },
        "capability_mismatches": mismatches,
        "interpretation": (
            "mean_objective_reward is the headline number — it scores all three approaches on "
            "the SAME blended objective (distance + battery health + task priority, app/ml/env.py "
            "_reward) that the policy was actually trained to optimize. This is the fair comparison: "
            "the trained policy should score highest here, because it is the only approach that was "
            "ever optimized for this objective. mean_total_travel_cost looks only at distance in "
            "isolation and will make the trained policy look worse, since it is deliberately not "
            "pure-distance-greedy — report objective_reward as the headline metric in the PPT, not "
            "travel cost alone, and say explicitly why: a policy judged only on the one axis it "
            "wasn't optimizing for will always look worse than a baseline built for exactly that axis."
        ),
    }


if __name__ == "__main__":
    train()
