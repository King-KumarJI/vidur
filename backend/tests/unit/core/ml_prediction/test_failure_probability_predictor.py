"""Unit tests for app.core.ml_prediction.failure_probability_predictor."""

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.failure_probability_predictor import FailureProbabilityPredictor
from app.core.ml_prediction.models import ProjectFeatureVector, RegressionRiskPrediction, TechnicalDebtEstimate


def _vector(**overrides) -> ProjectFeatureVector:
    defaults = dict(
        file_count=10,
        average_cyclomatic_complexity=1.0,
        max_cyclomatic_complexity=1,
        average_docstring_coverage=1.0,
        finding_density=0.0,
        severity_weighted_density=0.0,
        drift_churn_ratio=0.0,
        average_dependency_risk=0.0,
        max_dependency_risk=0.0,
        health_score=100.0,
    )
    defaults.update(overrides)
    return ProjectFeatureVector(**defaults)


def _regression(probability: float) -> RegressionRiskPrediction:
    return RegressionRiskPrediction(probability=probability, risk_level=RiskLevel.LOW)


def _debt(debt_score: float) -> TechnicalDebtEstimate:
    return TechnicalDebtEstimate(
        debt_score=debt_score, risk_level=RiskLevel.LOW, estimated_remediation_hours=0.0
    )


def test_predict_low_probability_for_healthy_project():
    prediction = FailureProbabilityPredictor().predict(_vector(), _regression(0.0), _debt(0.0))
    assert prediction.risk_level == RiskLevel.LOW
    assert prediction.probability < 0.25


def test_predict_probability_bounded():
    prediction = FailureProbabilityPredictor().predict(
        _vector(drift_churn_ratio=5.0, health_score=0.0), _regression(1.0), _debt(100.0)
    )
    assert 0.0 <= prediction.probability <= 1.0
    assert prediction.risk_level == RiskLevel.CRITICAL


def test_predict_higher_regression_risk_increases_probability():
    calm = FailureProbabilityPredictor().predict(_vector(), _regression(0.0), _debt(0.0))
    risky = FailureProbabilityPredictor().predict(_vector(), _regression(0.9), _debt(0.0))
    assert risky.probability > calm.probability


def test_predict_reports_contributing_factors():
    prediction = FailureProbabilityPredictor().predict(
        _vector(health_score=10.0), _regression(0.8), _debt(80.0)
    )
    assert prediction.contributing_factors
