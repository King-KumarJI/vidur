"""
VIDUR Core - ML Prediction
Submodule: High-Risk Module Identifier
Purpose: Rank every file touched by the inspection run by a composite
risk score - its own static complexity, its dependency blast radius
(from AI Reasoning's DependencyImpactAssessment, when available), and
the severity of its own findings - identifying "high-risk modules" per
Chapter VII of the Constitution.
"""

from collections import defaultdict
from typing import Dict, List, Optional

from app.core.ai_reasoning.models import DependencyImpactAssessment
from app.core.inspection_engine.models import FileMetrics, Finding
from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import ModuleRiskScore

#: A max cyclomatic complexity at or above this value is treated as
#: maximally risky on the complexity axis (complexity_score caps near
#: 1.0 around this point, though it is not hard-clamped).
COMPLEXITY_REFERENCE = 20.0

#: A DependencyReasoner risk_score at or above this value is treated as
#: maximally risky on the dependency axis.
DEPENDENCY_RISK_REFERENCE = 5.0

#: A summed Severity.weight at or above this value (e.g. one CRITICAL
#: plus a couple of WARNINGs) is treated as maximally risky on the
#: finding-severity axis.
FINDING_SEVERITY_REFERENCE = 10.0

#: Blend weights for the three normalized axes into one composite
#: score. Dependency blast radius is weighted highest because a defect
#: in a file many others depend on propagates further than an
#: equivalent defect in an unused file (same philosophy as
#: DependencyReasoner.risk_score in AI Reasoning).
COMPLEXITY_WEIGHT = 0.3
DEPENDENCY_WEIGHT = 0.4
FINDING_SEVERITY_WEIGHT = 0.3

CRITICAL_COMPOSITE_THRESHOLD = 1.0
HIGH_COMPOSITE_THRESHOLD = 0.6
MODERATE_COMPOSITE_THRESHOLD = 0.3


def _classify(composite_risk_score: float) -> RiskLevel:
    if composite_risk_score >= CRITICAL_COMPOSITE_THRESHOLD:
        return RiskLevel.CRITICAL
    if composite_risk_score >= HIGH_COMPOSITE_THRESHOLD:
        return RiskLevel.HIGH
    if composite_risk_score >= MODERATE_COMPOSITE_THRESHOLD:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


class HighRiskModuleIdentifier:
    """Computes one ModuleRiskScore per file that has complexity
    metrics, a dependency-impact assessment, or findings of its own."""

    def identify(
        self,
        file_metrics: List[FileMetrics],
        findings: List[Finding],
        dependency_assessments: Optional[List[DependencyImpactAssessment]] = None,
    ) -> List[ModuleRiskScore]:
        """Return one ModuleRiskScore per relevant file, ordered by
        descending composite risk score."""
        dependency_assessments = dependency_assessments or []

        metrics_by_path: Dict[str, FileMetrics] = {m.relative_path: m for m in file_metrics}
        risk_by_path: Dict[str, float] = {
            a.file_path: a.risk_score for a in dependency_assessments
        }
        severity_weight_by_path: Dict[str, int] = defaultdict(int)
        for finding in findings:
            if finding.file_path is not None:
                severity_weight_by_path[finding.file_path] += finding.severity.weight

        all_paths = set(metrics_by_path) | set(risk_by_path) | set(severity_weight_by_path)

        scores: List[ModuleRiskScore] = []
        for path in all_paths:
            metric = metrics_by_path.get(path)
            complexity_score = (
                round(metric.max_cyclomatic_complexity / COMPLEXITY_REFERENCE, 4)
                if metric is not None
                else 0.0
            )
            dependency_risk_score = round(risk_by_path.get(path, 0.0) / DEPENDENCY_RISK_REFERENCE, 4)
            finding_severity_score = round(
                severity_weight_by_path.get(path, 0) / FINDING_SEVERITY_REFERENCE, 4
            )
            composite_risk_score = round(
                (complexity_score * COMPLEXITY_WEIGHT)
                + (dependency_risk_score * DEPENDENCY_WEIGHT)
                + (finding_severity_score * FINDING_SEVERITY_WEIGHT),
                4,
            )
            scores.append(
                ModuleRiskScore(
                    file_path=path,
                    complexity_score=complexity_score,
                    dependency_risk_score=dependency_risk_score,
                    finding_severity_score=finding_severity_score,
                    composite_risk_score=composite_risk_score,
                    risk_level=_classify(composite_risk_score),
                )
            )

        scores.sort(key=lambda score: (-score.composite_risk_score, score.file_path))
        return scores
