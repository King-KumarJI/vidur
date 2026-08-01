"""Unit tests for app.core.ml_prediction.regression_risk_predictor."""

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import ProjectFeatureVector
from app.core.ml_prediction.regression_risk_predictor import RegressionRiskPredictor


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


def test_predict_low_risk_for_quiet_project():
    prediction = RegressionRiskPredictor().predict(_vector())
    assert prediction.risk_level == RiskLevel.LOW
    assert 0.0 <= prediction.probability < 0.25


def test_predict_probability_bounded_between_zero_and_one():
    prediction = RegressionRiskPredictor().predict(
        _vector(
            drift_churn_ratio=5.0,
            severity_weighted_density=50.0,
            average_cyclomatic_complexity=200.0,
            max_dependency_risk=100.0,
        )
    )
    assert 0.0 <= prediction.probability <= 1.0
    assert prediction.risk_level == RiskLevel.CRITICAL


def test_predict_higher_churn_increases_probability():
    calm = RegressionRiskPredictor().predict(_vector(drift_churn_ratio=0.0))
    churny = RegressionRiskPredictor().predict(_vector(drift_churn_ratio=0.8))
    assert churny.probability > calm.probability


def test_predict_reports_contributing_factors_for_high_churn():
    prediction = RegressionRiskPredictor().predict(_vector(drift_churn_ratio=0.9))
    assert any("churn" in factor.lower() for factor in prediction.contributing_factors)


def test_predict_no_contributing_factors_for_quiet_project():
    prediction = RegressionRiskPredictor().predict(_vector())
    assert prediction.contributing_factors == []
