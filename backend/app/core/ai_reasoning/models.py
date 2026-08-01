"""
VIDUR Core - AI Reasoning
Submodule: Models
Purpose: Plain, JSON-serializable data structures produced by the AI
Reasoning pipeline (correlated issue groups, dependency-impact
assessments, debugging hypotheses, drift insight, recommendations,
and the aggregated reasoning report).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.ai_reasoning.enums import ChurnLevel, CorrelationBasis, InsightCategory, RecommendationPriority
from app.core.inspection_engine.models import Finding


@dataclass(frozen=True)
class IssueCorrelationGroup:
    """A set of findings that are likely related because they share a
    common signal (the same file, or the same finding code recurring
    across files)."""

    basis: CorrelationBasis
    key: str
    findings: List[Finding] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "basis": self.basis.value,
            "key": self.key,
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": self.summary,
        }


@dataclass(frozen=True)
class DependencyImpactAssessment:
    """The blast radius of a single internal file that has at least
    one finding: how many other internal files transitively depend on
    it, and a risk score combining that reach with the severity of its
    own findings."""

    file_path: str
    direct_dependents: int
    transitive_dependents: int
    dependent_paths: List[str] = field(default_factory=list)
    finding_count: int = 0
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "direct_dependents": self.direct_dependents,
            "transitive_dependents": self.transitive_dependents,
            "dependent_paths": list(self.dependent_paths),
            "finding_count": self.finding_count,
            "risk_score": self.risk_score,
        }


@dataclass(frozen=True)
class DebuggingHypothesis:
    """A probable-cause explanation and suggested diagnostic next
    steps for one recurring finding code. Advisory only: VIDUR never
    applies the suggested steps itself (Article 10-11)."""

    finding_code: str
    probable_cause: str
    explanation: str
    suggested_next_steps: List[str] = field(default_factory=list)
    occurrence_count: int = 0
    related_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_code": self.finding_code,
            "probable_cause": self.probable_cause,
            "explanation": self.explanation,
            "suggested_next_steps": list(self.suggested_next_steps),
            "occurrence_count": self.occurrence_count,
            "related_files": list(self.related_files),
        }


@dataclass(frozen=True)
class DriftInsight:
    """Interpretation of the drift-category findings for a single
    inspection run: overall churn level plus any drifted files that
    also carry a high dependency blast radius."""

    churn_level: ChurnLevel
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    high_impact_files: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "churn_level": self.churn_level.value,
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "modified_count": self.modified_count,
            "high_impact_files": list(self.high_impact_files),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class Recommendation:
    """A single, human-readable, prioritized recommendation for the
    developer to review. VIDUR recommends; it never silently applies
    a recommendation (Article 10-11)."""

    priority: RecommendationPriority
    category: InsightCategory
    title: str
    description: str
    supporting_finding_codes: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "supporting_finding_codes": list(self.supporting_finding_codes),
            "affected_files": list(self.affected_files),
        }


@dataclass
class ReasoningReport:
    """Aggregated result of a single AI Reasoning run over one
    InspectionReport."""

    project_id: str
    root_path: str
    generated_at: datetime
    correlation_groups: List[IssueCorrelationGroup] = field(default_factory=list)
    dependency_assessments: List[DependencyImpactAssessment] = field(default_factory=list)
    debugging_hypotheses: List[DebuggingHypothesis] = field(default_factory=list)
    drift_insight: Optional[DriftInsight] = None
    recommendations: List[Recommendation] = field(default_factory=list)

    def recommendations_by_priority(self, priority: RecommendationPriority) -> List[Recommendation]:
        return [rec for rec in self.recommendations if rec.priority is priority]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_path": self.root_path,
            "generated_at": self.generated_at.isoformat(),
            "correlation_groups": [group.to_dict() for group in self.correlation_groups],
            "dependency_assessments": [
                assessment.to_dict() for assessment in self.dependency_assessments
            ],
            "debugging_hypotheses": [
                hypothesis.to_dict() for hypothesis in self.debugging_hypotheses
            ],
            "drift_insight": self.drift_insight.to_dict() if self.drift_insight else None,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
        }
