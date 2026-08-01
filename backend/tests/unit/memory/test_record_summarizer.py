"""Unit tests for app.memory.record_summarizer."""

from datetime import datetime, timezone

from app.core.ai_reasoning.models import ReasoningReport
from app.core.deep_learning_vision.enums import ComparisonVerdict
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import InspectionReport
from app.core.ml_prediction.enums import RiskLevel, TrendDirection
from app.core.ml_prediction.models import (
    FailureProbabilityPrediction,
    MLPredictionReport,
    ProjectFeatureVector,
    QualityTrendPrediction,
    RegressionRiskPrediction,
    TechnicalDebtEstimate,
)
from app.core.nlp.models import DocumentedIntent, ImplementedIntent, NLPReport
from app.memory.record_summarizer import RecordSummarizer

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _inspection_report() -> InspectionReport:
    return InspectionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
        health_score=91.5,
    )


def _reasoning_report() -> ReasoningReport:
    return ReasoningReport(project_id="demo-project", root_path="/tmp/demo", generated_at=_NOW)


def _nlp_report() -> NLPReport:
    return NLPReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=_NOW,
        documented_intent=DocumentedIntent(),
        implemented_intent=ImplementedIntent(),
    )


def _ml_prediction_report() -> MLPredictionReport:
    feature_vector = ProjectFeatureVector(
        file_count=10,
        average_cyclomatic_complexity=2.0,
        max_cyclomatic_complexity=5,
        average_docstring_coverage=0.5,
        finding_density=0.1,
        severity_weighted_density=0.2,
        drift_churn_ratio=0.0,
        average_dependency_risk=0.1,
        max_dependency_risk=0.3,
        health_score=77.25,
    )
    return MLPredictionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=_NOW,
        feature_vector=feature_vector,
        module_risk_scores=[],
        regression_risk=RegressionRiskPrediction(probability=0.2, risk_level=RiskLevel.LOW),
        technical_debt=TechnicalDebtEstimate(
            debt_score=10.0, risk_level=RiskLevel.LOW, estimated_remediation_hours=2.0
        ),
        quality_trend=QualityTrendPrediction(
            direction=TrendDirection.STABLE,
            current_health_score=77.25,
            projected_next_health_score=77.25,
            slope_per_run=0.0,
            data_points_used=1,
        ),
        failure_probability=FailureProbabilityPrediction(probability=0.1, risk_level=RiskLevel.LOW),
    )


def _visual_comparison_report() -> VisualComparisonReport:
    return VisualComparisonReport(
        project_id="demo-project",
        baseline_label="before",
        current_label="after",
        generated_at=_NOW,
        verdict=ComparisonVerdict.MATCH,
    )


def test_summarize_inspection_includes_status_and_health_score():
    summary = RecordSummarizer().summarize_inspection(_inspection_report())
    assert "status=completed" in summary
    assert "health_score=91.50" in summary


def test_health_score_for_inspection_returns_report_health_score():
    assert RecordSummarizer().health_score_for_inspection(_inspection_report()) == 91.5


def test_summarize_reasoning_includes_counts():
    summary = RecordSummarizer().summarize_reasoning(_reasoning_report())
    assert "correlation group(s)" in summary
    assert "recommendation(s)" in summary


def test_health_score_for_reasoning_is_none():
    assert RecordSummarizer().health_score_for_reasoning(_reasoning_report()) is None


def test_summarize_nlp_includes_finding_count():
    summary = RecordSummarizer().summarize_nlp(_nlp_report())
    assert "consistency finding(s)" in summary


def test_health_score_for_nlp_is_none():
    assert RecordSummarizer().health_score_for_nlp(_nlp_report()) is None


def test_summarize_ml_prediction_includes_risk_levels():
    summary = RecordSummarizer().summarize_ml_prediction(_ml_prediction_report())
    assert "regression_risk=low" in summary
    assert "quality_trend=stable" in summary


def test_health_score_for_ml_prediction_reads_feature_vector():
    assert RecordSummarizer().health_score_for_ml_prediction(_ml_prediction_report()) == 77.25


def test_summarize_visual_comparison_includes_verdict():
    summary = RecordSummarizer().summarize_visual_comparison(_visual_comparison_report())
    assert "verdict=match" in summary
    assert "before" in summary and "after" in summary


def test_health_score_for_visual_comparison_is_none():
    assert (
        RecordSummarizer().health_score_for_visual_comparison(_visual_comparison_report()) is None
    )
