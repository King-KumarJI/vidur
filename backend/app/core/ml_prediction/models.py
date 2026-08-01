"""
VIDUR Core - ML Prediction
Submodule: Models
Purpose: Plain, JSON-serializable data structures produced by the ML
Prediction pipeline (the engineered project feature vector, per-module
risk scores, regression-risk/technical-debt/quality-trend/failure-
probability predictions, and the aggregated report).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from app.core.ml_prediction.enums import RiskLevel, TrendDirection


@dataclass(frozen=True)
class ProjectFeatureVector:
    """Deterministic, numeric summary of a single InspectionReport (and,
    when available, its paired ReasoningReport) used as the shared input
    to every downstream predictor. Kept separate from InspectionReport
    itself so predictors depend on a small, stable numeric surface
    rather than the full report."""

    file_count: int
    average_cyclomatic_complexity: float
    max_cyclomatic_complexity: int
    average_docstring_coverage: float
    finding_density: float
    severity_weighted_density: float
    drift_churn_ratio: float
    average_dependency_risk: float
    max_dependency_risk: float
    health_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_count": self.file_count,
            "average_cyclomatic_complexity": self.average_cyclomatic_complexity,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "average_docstring_coverage": self.average_docstring_coverage,
            "finding_density": self.finding_density,
            "severity_weighted_density": self.severity_weighted_density,
            "drift_churn_ratio": self.drift_churn_ratio,
            "average_dependency_risk": self.average_dependency_risk,
            "max_dependency_risk": self.max_dependency_risk,
            "health_score": self.health_score,
        }


@dataclass(frozen=True)
class ModuleRiskScore:
    """Composite risk ranking for a single file, combining its own
    complexity, its dependency blast radius (when a ReasoningReport was
    supplied), and the severity of its own findings. Identifies
    "high-risk modules" per Chapter VII of the Constitution."""

    file_path: str
    complexity_score: float
    dependency_risk_score: float
    finding_severity_score: float
    composite_risk_score: float
    risk_level: RiskLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "complexity_score": self.complexity_score,
            "dependency_risk_score": self.dependency_risk_score,
            "finding_severity_score": self.finding_severity_score,
            "composite_risk_score": self.composite_risk_score,
            "risk_level": self.risk_level.value,
        }


@dataclass(frozen=True)
class RegressionRiskPrediction:
    """Predicted probability that the current inspection run's changes
    introduce a regression, per Chapter VII ("predicts regression
    probability"). Advisory only: never replaces deterministic
    validation (Article 10-11, Chapter VII ML)."""

    probability: float
    risk_level: RiskLevel
    contributing_factors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability": self.probability,
            "risk_level": self.risk_level.value,
            "contributing_factors": list(self.contributing_factors),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class TechnicalDebtEstimate:
    """Predicted technical debt for the project, per Chapter VII
    ("predicts technical debt"): a 0-100 debt score plus an estimated
    remediation effort in hours."""

    debt_score: float
    risk_level: RiskLevel
    estimated_remediation_hours: float
    contributing_factors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debt_score": self.debt_score,
            "risk_level": self.risk_level.value,
            "estimated_remediation_hours": self.estimated_remediation_hours,
            "contributing_factors": list(self.contributing_factors),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class QualityTrendPrediction:
    """Predicted trajectory of the project's health score, per Chapter
    VII ("predicts ... quality trends"), derived from a caller-supplied
    history of prior health scores (persistence of that history is the
    responsibility of the future Memory module, matching the precedent
    set by InspectionSnapshot)."""

    direction: TrendDirection
    current_health_score: float
    projected_next_health_score: float
    slope_per_run: float
    data_points_used: int
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "current_health_score": self.current_health_score,
            "projected_next_health_score": self.projected_next_health_score,
            "slope_per_run": self.slope_per_run,
            "data_points_used": self.data_points_used,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class FailureProbabilityPrediction:
    """Predicted overall probability of project failure (build/release
    quality breakdown), per Chapter VII ("predicts failure
    probability"), combining regression risk, technical debt, drift
    churn, and the current health score."""

    probability: float
    risk_level: RiskLevel
    contributing_factors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability": self.probability,
            "risk_level": self.risk_level.value,
            "contributing_factors": list(self.contributing_factors),
            "summary": self.summary,
        }


@dataclass
class MLPredictionReport:
    """Aggregated result of a single ML Prediction run over one
    InspectionReport (and optional paired ReasoningReport)."""

    project_id: str
    root_path: str
    generated_at: datetime
    feature_vector: ProjectFeatureVector
    module_risk_scores: List[ModuleRiskScore]
    regression_risk: RegressionRiskPrediction
    technical_debt: TechnicalDebtEstimate
    quality_trend: QualityTrendPrediction
    failure_probability: FailureProbabilityPrediction

    def high_risk_modules(self, minimum_level: RiskLevel = RiskLevel.HIGH) -> List[ModuleRiskScore]:
        """Return module risk scores at or above `minimum_level`,
        highest risk first."""
        return sorted(
            (m for m in self.module_risk_scores if m.risk_level.weight >= minimum_level.weight),
            key=lambda m: (-m.composite_risk_score, m.file_path),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_path": self.root_path,
            "generated_at": self.generated_at.isoformat(),
            "feature_vector": self.feature_vector.to_dict(),
            "module_risk_scores": [score.to_dict() for score in self.module_risk_scores],
            "regression_risk": self.regression_risk.to_dict(),
            "technical_debt": self.technical_debt.to_dict(),
            "quality_trend": self.quality_trend.to_dict(),
            "failure_probability": self.failure_probability.to_dict(),
        }
