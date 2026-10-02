"""Risk & Escalation Classifier — Phase 2.6.

This closes a real gap from the original build plan: the Supervisor was
reusing the mission-feasibility score directly as a confidence proxy instead
of using a second, separately trained model. That's not what was designed,
and it wasn't flagged clearly when it happened — fixing it here.

Honesty about training data: there is no historical log of real operator
escalation decisions to train on (this is a new system). The standard,
defensible bootstrap for exactly this situation is to generate synthetic
labels from an explicit, documented domain rule (below), train a real
classifier on it, and treat that classifier as the cold-start model — in a
real deployment it would be retrained on logged operator approve/override
decisions over time (the ledger already captures every escalation's outcome,
see app/ledger.py, so that retraining data accumulates automatically from day
one). The point of training a model here at all, instead of just hand-coding
the rule directly as an if-statement, is that a trained classifier can be
cheaply re-fit on that accumulating real data later without changing any
calling code — the rule-based version can't evolve past hand-tuning.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "risk_classifier.joblib"
FEATURE_NAMES = ["comm_quality", "battery_margin", "obstacle_density", "policy_confidence"]


@dataclass
class RiskFeatures:
    comm_quality: float  # 0..1, fraction of agents this agent can currently reach
    battery_margin: float  # 0..1, battery / 100
    obstacle_density: float  # 0..1, blocked zones relative to world area
    policy_confidence: float  # 0..1, mission feasibility score

    def to_array(self) -> np.ndarray:
        return np.array([[self.comm_quality, self.battery_margin, self.obstacle_density, self.policy_confidence]])


def _domain_rule_label(f: RiskFeatures, noise: random.Random) -> int:
    """The documented bootstrap rule generating synthetic training labels.
    Escalate when multiple risk factors stack — not any single weak signal."""
    risk_score = (
        (1 - f.comm_quality) * 0.35
        + (1 - f.battery_margin) * 0.30
        + f.obstacle_density * 0.15
        + (1 - f.policy_confidence) * 0.20
    )
    risk_score += noise.gauss(0, 0.05)  # label noise so the classifier learns a boundary, not a lookup table
    return int(risk_score > 0.5)


def generate_training_data(n_samples: int = 4000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n_samples):
        f = RiskFeatures(
            comm_quality=rng.uniform(0, 1),
            battery_margin=rng.uniform(0, 1),
            obstacle_density=rng.uniform(0, 1),
            policy_confidence=rng.uniform(0, 1),
        )
        X.append([f.comm_quality, f.battery_margin, f.obstacle_density, f.policy_confidence])
        y.append(_domain_rule_label(f, rng))
    return np.array(X), np.array(y)


def train_risk_model() -> Path:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    import joblib

    X, y = generate_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

    model = LogisticRegression()
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Risk classifier trained, held-out accuracy {acc:.3f} -> {MODEL_PATH}")
    return MODEL_PATH


class RiskClassifier:
    """Loads the trained classifier if present; falls back to the same
    documented domain rule (not a silent crash) if the model file is missing —
    consistent fallback pattern with Allocator (app/ml/inference.py)."""

    def __init__(self, model_path: Path | str | None = MODEL_PATH):
        self.model_path = Path(model_path) if model_path else None
        self.model = None
        self.backend = "domain_rule_fallback"
        if self.model_path and self.model_path.exists():
            try:
                import joblib

                self.model = joblib.load(self.model_path)
                self.backend = "trained_classifier"
            except Exception:
                self.model = None
                self.backend = "domain_rule_fallback"

    def should_escalate(self, features: RiskFeatures) -> bool:
        if self.model is not None:
            return bool(self.model.predict(features.to_array())[0])
        return bool(_domain_rule_label(features, random.Random()))

    def risk_probability(self, features: RiskFeatures) -> float:
        if self.model is not None:
            return float(self.model.predict_proba(features.to_array())[0][1])
        # Fallback: deterministic score from the same rule, no noise.
        return (
            (1 - features.comm_quality) * 0.35
            + (1 - features.battery_margin) * 0.30
            + features.obstacle_density * 0.15
            + (1 - features.policy_confidence) * 0.20
        )


if __name__ == "__main__":
    train_risk_model()
