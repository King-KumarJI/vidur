"""Unit tests for app.core.ml_prediction.report_generator."""

from app.core.ml_prediction.enums import RiskLevel, TrendDirection
from app.core.ml_prediction.models import (
    FailureProbabilityPrediction,
    ProjectFeatureVector,
    QualityTrendPrediction,
    RegressionRiskPrediction,
    TechnicalDebtEstimate,
)
from app.core.ml_prediction.report_generator import MLPredictionReportGenerator


def _feature_vector() -> ProjectFeatureVector:
    return ProjectFeatureVector(
        file_count=1,
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


def test_generate_builds_ml_prediction_report():
    report = MLPredictionReportGenerator().generate(
        project_id="demo-project",
        root_path="/tmp/demo",
        feature_vector=_feature_vector(),
        module_risk_scores=[],
        regression_risk=RegressionRiskPrediction(probability=0.1, risk_level=RiskLevel.LOW),
        technical_debt=TechnicalDebtEstimate(
            debt_score=5.0, risk_level=RiskLevel.LOW, estimated_remediation_hours=0.5
        ),
        quality_trend=QualityTrendPrediction(
            direction=TrendDirection.STABLE,
            current_health_score=100.0,
            projected_next_health_score=100.0,
            slope_per_run=0.0,
            data_points_used=1,
        ),
        failure_probability=FailureProbabilityPrediction(probability=0.1, risk_level=RiskLevel.LOW),
    )

    assert report.project_id == "demo-project"
    assert report.root_path == "/tmp/demo"
    assert report.generated_at is not None
    assert report.to_dict()["project_id"] == "demo-project"


def test_high_risk_modules_filters_and_sorts():
    from app.core.ml_prediction.models import ModuleRiskScore

    scores = [
        ModuleRiskScore("low.py", 0.1, 0.1, 0.1, 0.1, RiskLevel.LOW),
        ModuleRiskScore("high.py", 0.9, 0.9, 0.9, 0.9, RiskLevel.HIGH),
        ModuleRiskScore("critical.py", 1.0, 1.0, 1.0, 1.2, RiskLevel.CRITICAL),
    ]
    report = MLPredictionReportGenerator().generate(
        project_id="demo-project",
        root_path="/tmp/demo",
        feature_vector=_feature_vector(),
        module_risk_scores=scores,
        regression_risk=RegressionRiskPrediction(probability=0.1, risk_level=RiskLevel.LOW),
        technical_debt=TechnicalDebtEstimate(
            debt_score=5.0, risk_level=RiskLevel.LOW, estimated_remediation_hours=0.5
        ),
        quality_trend=QualityTrendPrediction(
            direction=TrendDirection.STABLE,
            current_health_score=100.0,
            projected_next_health_score=100.0,
            slope_per_run=0.0,
            data_points_used=1,
        ),
        failure_probability=FailureProbabilityPrediction(probability=0.1, risk_level=RiskLevel.LOW),
    )

    high_risk = report.high_risk_modules()
    assert [m.file_path for m in high_risk] == ["critical.py", "high.py"]
