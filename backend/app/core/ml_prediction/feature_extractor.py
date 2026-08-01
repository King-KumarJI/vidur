"""
VIDUR Core - ML Prediction
Submodule: Feature Extractor
Purpose: Reduce a completed InspectionReport (and, when available, its
paired AI Reasoning ReasoningReport) into a single, deterministic
ProjectFeatureVector - the shared numeric input every ML Prediction
predictor operates on. Reuses Inspection Engine's own `health_score`
and AI Reasoning's `DependencyImpactAssessment.risk_score` rather than
recomputing them, per Article 31-32 (reuse before rewriting).
"""

from typing import List, Optional, Tuple

from app.core.ai_reasoning.models import ReasoningReport
from app.core.inspection_engine.enums import FindingCategory
from app.core.inspection_engine.models import FileMetrics, InspectionReport
from app.core.ml_prediction.models import ProjectFeatureVector

#: Docstring coverage assumed for a project with no analyzable Python
#: files - there is nothing undocumented, so this is not a penalty.
DEFAULT_DOCSTRING_COVERAGE_WHEN_NO_FILES = 1.0


class FeatureExtractor:
    """Builds a ProjectFeatureVector from inspection (and optional
    reasoning) output."""

    def extract(
        self,
        inspection_report: InspectionReport,
        reasoning_report: Optional[ReasoningReport] = None,
    ) -> ProjectFeatureVector:
        file_count = len(inspection_report.files)
        metrics = inspection_report.file_metrics

        average_complexity, max_complexity = self._complexity_stats(metrics)
        average_docstring_coverage = self._average_docstring_coverage(metrics)

        finding_count = len(inspection_report.findings)
        finding_density = round(finding_count / max(file_count, 1), 4)

        severity_weight_total = sum(
            finding.severity.weight for finding in inspection_report.findings
        )
        severity_weighted_density = round(severity_weight_total / max(file_count, 1), 4)

        drift_finding_count = sum(
            1
            for finding in inspection_report.findings
            if finding.category is FindingCategory.DRIFT
        )
        drift_churn_ratio = round(drift_finding_count / max(file_count, 1), 4)

        average_dependency_risk, max_dependency_risk = self._dependency_risk_stats(
            reasoning_report
        )

        return ProjectFeatureVector(
            file_count=file_count,
            average_cyclomatic_complexity=average_complexity,
            max_cyclomatic_complexity=max_complexity,
            average_docstring_coverage=average_docstring_coverage,
            finding_density=finding_density,
            severity_weighted_density=severity_weighted_density,
            drift_churn_ratio=drift_churn_ratio,
            average_dependency_risk=average_dependency_risk,
            max_dependency_risk=max_dependency_risk,
            health_score=inspection_report.health_score,
        )

    @staticmethod
    def _complexity_stats(metrics: List[FileMetrics]) -> Tuple[float, int]:
        if not metrics:
            return 0.0, 0
        complexities = [m.max_cyclomatic_complexity for m in metrics]
        average = round(sum(complexities) / len(complexities), 4)
        return average, max(complexities)

    @staticmethod
    def _average_docstring_coverage(metrics: List[FileMetrics]) -> float:
        if not metrics:
            return DEFAULT_DOCSTRING_COVERAGE_WHEN_NO_FILES
        return round(sum(m.docstring_coverage for m in metrics) / len(metrics), 4)

    @staticmethod
    def _dependency_risk_stats(
        reasoning_report: Optional[ReasoningReport],
    ) -> Tuple[float, float]:
        if reasoning_report is None or not reasoning_report.dependency_assessments:
            return 0.0, 0.0
        risk_scores = [a.risk_score for a in reasoning_report.dependency_assessments]
        return round(sum(risk_scores) / len(risk_scores), 4), max(risk_scores)
