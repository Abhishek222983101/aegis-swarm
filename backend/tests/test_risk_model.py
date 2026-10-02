import pytest

from app.ml.risk_model import RiskClassifier, RiskFeatures, generate_training_data


def test_generate_training_data_shape_and_labels():
    X, y = generate_training_data(n_samples=200, seed=1)
    assert X.shape == (200, 4)
    assert set(y.tolist()) <= {0, 1}
    assert 0 < y.sum() < 200  # not degenerate — both classes present


def test_generate_training_data_is_seed_deterministic():
    X1, y1 = generate_training_data(n_samples=100, seed=5)
    X2, y2 = generate_training_data(n_samples=100, seed=5)
    assert (X1 == X2).all()
    assert (y1 == y2).all()


def test_fallback_classifier_flags_clearly_high_risk_situation():
    clf = RiskClassifier(model_path=None)  # force the domain-rule fallback
    assert clf.backend == "domain_rule_fallback"
    bad = RiskFeatures(comm_quality=0.0, battery_margin=0.05, obstacle_density=1.0, policy_confidence=0.1)
    assert clf.should_escalate(bad) is True


def test_fallback_classifier_does_not_flag_clearly_safe_situation():
    clf = RiskClassifier(model_path=None)
    good = RiskFeatures(comm_quality=1.0, battery_margin=0.95, obstacle_density=0.0, policy_confidence=0.95)
    assert clf.should_escalate(good) is False


def test_risk_probability_is_bounded_0_to_1():
    clf = RiskClassifier(model_path=None)
    for cq, bm, od, pc in [(0, 0, 0, 0), (1, 1, 1, 1), (0.5, 0.5, 0.5, 0.5)]:
        p = clf.risk_probability(RiskFeatures(cq, bm, od, pc))
        assert 0.0 <= p <= 1.0


def test_trained_classifier_loads_when_present():
    from pathlib import Path
    model_path = Path(__file__).resolve().parent.parent / "models" / "risk_classifier.joblib"
    if not model_path.exists():
        pytest.skip("no trained risk classifier present in this environment")
    clf = RiskClassifier(model_path=model_path)
    assert clf.backend == "trained_classifier"
    bad = RiskFeatures(comm_quality=0.0, battery_margin=0.02, obstacle_density=1.0, policy_confidence=0.05)
    assert clf.should_escalate(bad) is True
