"""
VIDUR - Memory
Submodule: Record Summarizer
Purpose: Translate a completed Inspection Engine / AI Reasoning / NLP
/ ML Prediction / Deep Learning Vision report into the short,
human-readable summary text stored alongside it for semantic recall,
and extract the health score (when the report carries one) that feeds
MemoryEngine.health_score_trend.
"""

from typing import Optional

from app.core.ai_reasoning.models import ReasoningReport
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.core.inspection_engine.models import InspectionReport
from app.core.ml_prediction.models import MLPredictionReport
from app.core.nlp.models import NLPReport


class RecordSummarizer:
    """Builds the `summary` text and `health_score` stored on a
    MemoryRecord for each report type the Memory module knows how to
    persist. Kept as a single-responsibility component (Article
    30-35) so MemoryEngine stays a pure orchestrator."""

    def summarize_inspection(self, report: InspectionReport) -> str:
        return (
            f"Inspection run for '{report.root_path}': status={report.status.value}, "
            f"health_score={report.health_score:.2f}, files={len(report.files)}, "
            f"findings={len(report.findings)}."
        )

    def health_score_for_inspection(self, report: InspectionReport) -> Optional[float]:
        return report.health_score

    def summarize_reasoning(self, report: ReasoningReport) -> str:
        drift_clause = (
            f"; drift churn={report.drift_insight.churn_level.value}"
            if report.drift_insight is not None
            else ""
        )
        return (
            f"AI reasoning run for '{report.root_path}': "
            f"{len(report.correlation_groups)} correlation group(s), "
            f"{len(report.dependency_assessments)} dependency assessment(s), "
            f"{len(report.recommendations)} recommendation(s){drift_clause}."
        )

    def health_score_for_reasoning(self, report: ReasoningReport) -> Optional[float]:
        return None

    def summarize_nlp(self, report: NLPReport) -> str:
        return (
            f"NLP consistency run for '{report.root_path}': "
            f"{len(report.consistency_findings)} consistency finding(s) against "
            f"{len(report.documented_intent.requirement_statements)} documented "
            f"requirement statement(s)."
        )

    def health_score_for_nlp(self, report: NLPReport) -> Optional[float]:
        return None

    def summarize_ml_prediction(self, report: MLPredictionReport) -> str:
        return (
            f"ML prediction run for '{report.root_path}': "
            f"regression_risk={report.regression_risk.risk_level.value}, "
            f"technical_debt={report.technical_debt.risk_level.value}, "
            f"quality_trend={report.quality_trend.direction.value}, "
            f"failure_probability={report.failure_probability.risk_level.value}."
        )

    def health_score_for_ml_prediction(self, report: MLPredictionReport) -> Optional[float]:
        return report.feature_vector.health_score

    def summarize_visual_comparison(self, report: VisualComparisonReport) -> str:
        return (
            f"Visual comparison '{report.baseline_label}' -> '{report.current_label}': "
            f"verdict={report.verdict.value}, findings={len(report.findings)}."
        )

    def health_score_for_visual_comparison(self, report: VisualComparisonReport) -> Optional[float]:
        return None
