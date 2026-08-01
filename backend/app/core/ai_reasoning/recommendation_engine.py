"""
VIDUR Core - AI Reasoning
Submodule: Recommendation Engine
Purpose: Aggregate issue-correlation groups, dependency-impact
assessments, debugging hypotheses, and drift insight into a single,
prioritized list of human-readable recommendations. Per Article 10-11
of the VIDUR Constitution, recommendations are advisory only - VIDUR
never applies them automatically.
"""

from typing import List, Optional

from app.core.ai_reasoning.enums import (
    ChurnLevel,
    CorrelationBasis,
    InsightCategory,
    RecommendationPriority,
)
from app.core.ai_reasoning.models import (
    DebuggingHypothesis,
    DependencyImpactAssessment,
    DriftInsight,
    IssueCorrelationGroup,
    Recommendation,
)

#: Minimum dependency risk score (see DependencyReasoner) before a
#: file's blast radius is surfaced as its own recommendation.
MIN_RISK_SCORE_FOR_RECOMMENDATION = 1.0

#: Minimum recurrence count before a debugging hypothesis is surfaced
#: as a systemic-pattern recommendation (a single occurrence is
#: already visible via its own finding; only repeats warrant a
#: dedicated recommendation).
MIN_OCCURRENCES_FOR_RECOMMENDATION = 2


def _priority_for_weight(weight: float) -> RecommendationPriority:
    """Map a severity-style weight (aligned with Severity.weight:
    INFO=1, WARNING=3, ERROR=7, CRITICAL=15) onto a recommendation
    priority."""
    if weight >= 15:
        return RecommendationPriority.CRITICAL
    if weight >= 7:
        return RecommendationPriority.HIGH
    if weight >= 3:
        return RecommendationPriority.MEDIUM
    return RecommendationPriority.LOW


class RecommendationEngine:
    """Builds the final, prioritized Recommendation list for a
    reasoning run."""

    def build(
        self,
        correlation_groups: List[IssueCorrelationGroup],
        dependency_assessments: List[DependencyImpactAssessment],
        debugging_hypotheses: List[DebuggingHypothesis],
        drift_insight: Optional[DriftInsight],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        recommendations.extend(self._correlation_recommendations(correlation_groups))
        recommendations.extend(self._dependency_recommendations(dependency_assessments))
        recommendations.extend(self._debugging_recommendations(debugging_hypotheses))
        drift_recommendation = self._drift_recommendation(drift_insight)
        if drift_recommendation is not None:
            recommendations.append(drift_recommendation)

        recommendations.sort(
            key=lambda rec: (-rec.priority.weight, rec.category.value, rec.title)
        )
        return recommendations

    @staticmethod
    def _correlation_recommendations(
        groups: List[IssueCorrelationGroup],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        for group in groups:
            weight = sum(finding.severity.weight for finding in group.findings)
            if group.basis is CorrelationBasis.SAME_FILE:
                title = f"Review concentrated issues in '{group.key}'"
            else:
                title = f"Address the recurring '{group.key}' pattern"
            recommendations.append(
                Recommendation(
                    priority=_priority_for_weight(weight),
                    category=InsightCategory.ISSUE_CORRELATION,
                    title=title,
                    description=group.summary,
                    supporting_finding_codes=sorted({f.code for f in group.findings}),
                    affected_files=sorted(
                        {f.file_path for f in group.findings if f.file_path is not None}
                    ),
                )
            )
        return recommendations

    @staticmethod
    def _dependency_recommendations(
        assessments: List[DependencyImpactAssessment],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        for assessment in assessments:
            if assessment.risk_score < MIN_RISK_SCORE_FOR_RECOMMENDATION:
                continue
            recommendations.append(
                Recommendation(
                    priority=_priority_for_weight(assessment.risk_score),
                    category=InsightCategory.DEPENDENCY_IMPACT,
                    title=f"Prioritize fixes in '{assessment.file_path}'",
                    description=(
                        f"'{assessment.file_path}' has {assessment.finding_count} finding(s) "
                        f"and {assessment.transitive_dependents} internal file(s) depend on "
                        "it transitively, so issues here can propagate further than an "
                        "equivalent issue in an unused file."
                    ),
                    supporting_finding_codes=[],
                    affected_files=[assessment.file_path, *assessment.dependent_paths],
                )
            )
        return recommendations

    @staticmethod
    def _debugging_recommendations(
        hypotheses: List[DebuggingHypothesis],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        for hypothesis in hypotheses:
            if hypothesis.occurrence_count < MIN_OCCURRENCES_FOR_RECOMMENDATION:
                continue
            recommendations.append(
                Recommendation(
                    priority=(
                        RecommendationPriority.HIGH
                        if hypothesis.occurrence_count >= 5
                        else RecommendationPriority.MEDIUM
                    ),
                    category=InsightCategory.DEBUGGING_ASSISTANCE,
                    title=f"Investigate recurring '{hypothesis.finding_code}' findings",
                    description=(
                        f"{hypothesis.probable_cause} {hypothesis.explanation} "
                        f"Suggested next steps: {'; '.join(hypothesis.suggested_next_steps)}"
                    ),
                    supporting_finding_codes=[hypothesis.finding_code],
                    affected_files=hypothesis.related_files,
                )
            )
        return recommendations

    @staticmethod
    def _drift_recommendation(drift_insight: Optional[DriftInsight]) -> Optional[Recommendation]:
        if drift_insight is None:
            return None
        if drift_insight.churn_level is ChurnLevel.LOW and not drift_insight.high_impact_files:
            return None

        if drift_insight.high_impact_files and drift_insight.churn_level is ChurnLevel.HIGH:
            priority = RecommendationPriority.CRITICAL
        elif drift_insight.high_impact_files or drift_insight.churn_level is ChurnLevel.HIGH:
            priority = RecommendationPriority.HIGH
        else:
            priority = RecommendationPriority.MEDIUM

        return Recommendation(
            priority=priority,
            category=InsightCategory.DRIFT_SIGNIFICANCE,
            title="Review structural drift since the previous inspection",
            description=drift_insight.summary,
            supporting_finding_codes=["FILE_ADDED", "FILE_REMOVED", "FILE_MODIFIED"],
            affected_files=drift_insight.high_impact_files,
        )
