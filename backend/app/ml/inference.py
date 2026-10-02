"""Allocator inference wrapper — swaps transparently between the trained ONNX
policy (if a trained model file exists) and the Hungarian baseline (if not).

This is deliberate, not a stopgap: the system must never crash or stall because
training hasn't been run yet in a given environment. `onnxruntime` is imported
lazily so this module has zero hard dependency on the ML extras being installed.
"""
from __future__ import annotations

from pathlib import Path

from app.ml.baselines import hungarian_assign
from app.ml.encoding import AGENT_TYPES, N_AGENT_TYPES, WORLD_SIZE
from app.ml.tasks import Task
from app.sim.entities import Agent, AgentStatus

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "allocator_policy.onnx"


class Allocator:
    """Picks an agent for each pending task. Trained-policy-backed when a model
    is available, Hungarian-optimal baseline otherwise — same call signature
    either way, so callers (Supervisor) never need to know which is active."""

    def __init__(self, model_path: Path | str | None = DEFAULT_MODEL_PATH, trained_n_agents: int = 4):
        self.model_path = Path(model_path) if model_path else None
        self.session = None
        self.backend = "hungarian_baseline"
        # The ONNX graph's input size is fixed at export time to this many agent
        # "slots" (app/ml/env.py's AllocationEnv n_agents). Outside that exact
        # candidate count the model cannot run at all — ONNX Runtime raises on
        # shape mismatch, it does not silently pad or truncate.
        self.trained_n_agents = trained_n_agents
        if self.model_path and self.model_path.exists():
            try:
                import onnxruntime as ort

                self.session = ort.InferenceSession(str(self.model_path))
                self.backend = "trained_policy"
            except Exception:
                # Never let a corrupt/incompatible model file take the system down —
                # fall back to the always-correct baseline instead.
                self.session = None
                self.backend = "hungarian_baseline"

    def allocate(self, tasks: list[Task], agents: list[Agent]) -> dict[str, str]:
        # Outside the trained envelope (e.g. a fault just took an agent down,
        # shrinking the live candidate pool below what the model was trained
        # on) fall back to the baseline rather than crash — this is exactly
        # the scenario class the fault-injection demo exercises constantly,
        # so this path is not a rare edge case, it must be solid.
        available = [a for a in agents if a.status != AgentStatus.LOST]
        if self.session is None or len(available) != self.trained_n_agents:
            return hungarian_assign(tasks, agents)
        return self._allocate_with_policy(tasks, agents)

    def _allocate_with_policy(self, tasks: list[Task], agents: list[Agent]) -> dict[str, str]:
        import numpy as np

        assignment: dict[str, str] = {}
        taken: set[str] = set()
        # Sequential: matches the training env's one-task-at-a-time structure.
        for task in sorted(tasks, key=lambda t: -t.priority):
            available = [a for a in agents if a.id not in taken and a.status != AgentStatus.LOST]
            if not available:
                continue
            if len(available) != self.trained_n_agents:
                # Same fixed-input-size constraint as the top-level allocate()
                # gate, but re-checked per task: a multi-task batch shrinks the
                # candidate pool as earlier tasks consume agents, so later
                # tasks in the SAME call can fall outside the trained envelope
                # even when the call started inside it. Fall back per-task
                # rather than crash or abandon the rest of the batch.
                single_result = hungarian_assign([task], [a for a in agents if a.id not in taken])
                if task.id in single_result:
                    assignment[task.id] = single_result[task.id]
                    taken.add(single_result[task.id])
                continue
            obs = _encode_observation(task, available)
            input_name = self.session.get_inputs()[0].name
            logits = self.session.run(None, {input_name: obs[None, :].astype(np.float32)})[0]
            # Logits are only valid for the first len(available) action slots —
            # the policy was trained with a fixed agent-count action space.
            valid_logits = logits[0, : len(available)]

            # Hard capability constraint: the policy is trained to prefer
            # eligible agents but is not *guaranteed* to never violate the
            # requirement (confirmed empirically — see
            # models/baseline_comparison.json's capability_mismatches). A
            # task requiring a specific agent type must NEVER go to the wrong
            # type in production, so mask ineligible agents' logits to -inf
            # before argmax rather than trust the model's soft preference.
            if task.required_type is not None:
                for i, a in enumerate(available):
                    if a.type != task.required_type:
                        valid_logits[i] = -np.inf
                if np.all(np.isneginf(valid_logits)):
                    continue  # no eligible agent in this candidate set at all

            best_idx = int(np.argmax(valid_logits))
            chosen = available[best_idx]
            assignment[task.id] = chosen.id
            taken.add(chosen.id)
        return assignment


def _encode_observation(task: Task, agents: list[Agent]):
    """Must exactly mirror AllocationEnv._observe()'s encoding (app/ml/env.py) —
    the ONNX model was trained on that exact layout. Kept here, not imported
    from env.py, deliberately: env.py depends on gymnasium (training-time only),
    this module must stay importable without it at inference time."""
    import numpy as np

    parts = []
    for agent in agents:
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
