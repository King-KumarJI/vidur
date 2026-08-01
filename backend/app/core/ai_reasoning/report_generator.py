"""
VIDUR Core - AI Reasoning
Submodule: Report Generator
Purpose: Assemble the outputs of every reasoning stage (issue
correlation, dependency-impact assessment, debugging assistance,
drift reasoning, and recommendations) into a single ReasoningReport.
"""

from datetime import datetime
from typing import List, Optional

from app.core.ai_reasoning.models import (
    DebuggingHypothesis,
    DependencyImpactAssessment,
    DriftInsight,
    IssueCorrelationGroup,
    Recommendation,
    ReasoningReport,
)
from app.core.inspection_engine.models import utc_now


class ReasoningReportGenerator:
    """Builds the final ReasoningReport for a completed reasoning run."""

    def generate(
        self,
        *,
        project_id: str,
        root_path: str,
        correlation_groups: List[IssueCorrelationGroup],
        dependency_assessments: List[DependencyImpactAssessment],
        debugging_hypotheses: List[DebuggingHypothesis],
        drift_insight: Optional[DriftInsight],
        recommendations: List[Recommendation],
        generated_at: Optional[datetime] = None,
    ) -> ReasoningReport:
        """Assemble the final ReasoningReport for one reasoning run."""
        return ReasoningReport(
            project_id=project_id,
            root_path=root_path,
            generated_at=generated_at or utc_now(),
            correlation_groups=correlation_groups,
            dependency_assessments=dependency_assessments,
            debugging_hypotheses=debugging_hypotheses,
            drift_insight=drift_insight,
            recommendations=recommendations,
        )
