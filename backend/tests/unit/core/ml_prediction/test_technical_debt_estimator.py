"""Unit tests for app.core.ml_prediction.technical_debt_estimator."""

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import ProjectFeatureVector
from app.core.ml_prediction.technical_debt_estimator import TechnicalDebtEstimator


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


def test_estimate_low_debt_for_clean_project():
    estimate = TechnicalDebtEstimator().estimate(_vector())
    assert estimate.risk_level == RiskLevel.LOW
    assert estimate.debt_score < 25.0
    assert estimate.estimated_remediation_hours >= 0.0


def test_estimate_debt_score_capped_at_100():
    estimate = TechnicalDebtEstimator().estimate(
        _vector(average_cyclomatic_complexity=500.0, average_docstring_coverage=0.0, finding_density=10.0)
    )
    assert estimate.debt_score == 100.0
    assert estimate.risk_level == RiskLevel.CRITICAL


def test_estimate_low_docstring_coverage_increases_debt():
    documented = TechnicalDebtEstimator().estimate(_vector(average_docstring_coverage=1.0))
    undocumented = TechnicalDebtEstimator().estimate(_vector(average_docstring_coverage=0.0))
    assert undocumented.debt_score > documented.debt_score


def test_estimate_remediation_hours_scale_with_file_count():
    small = TechnicalDebtEstimator().estimate(
        _vector(file_count=1, average_cyclomatic_complexity=100.0)
    )
    large = TechnicalDebtEstimator().estimate(
        _vector(file_count=100, average_cyclomatic_complexity=100.0)
    )
    assert large.estimated_remediation_hours > small.estimated_remediation_hours


def test_estimate_reports_contributing_factors_for_high_complexity():
    estimate = TechnicalDebtEstimator().estimate(_vector(average_cyclomatic_complexity=40.0))
    assert any("complexity" in factor.lower() for factor in estimate.contributing_factors)
