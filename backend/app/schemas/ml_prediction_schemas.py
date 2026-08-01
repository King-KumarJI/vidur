"""
VIDUR Schemas
Submodule: ML Prediction
Purpose: Request/response shapes for the ML Prediction module's
routes. Response schemas mirror `app.core.ml_prediction.models`
`to_dict()` output field-for-field; the engine's own dataclasses
remain the single source of truth for report content (Article 31-32).
Ships behind the `MAJOR_ML_RISK_PREDICTION` feature flag (Article
41-44), disabled by default.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class MLPredictionRunRequest(BaseModel):
    """Request to run a full inspection (optionally followed by AI
    reasoning) and then ML prediction over a project root already
    present on the VIDUR backend's own file system."""

    model_config = ConfigDict(extra="forbid")

    root_path: str = Field(
        ..., min_length=1, description="Absolute path to the project root to inspect and predict on."
    )
    include_reasoning: bool = Field(
        default=True,
        description=(
            "Whether to run AI reasoning first and feed its dependency-impact "
            "data into prediction. Disable to predict from inspection data alone."
        ),
    )


class ProjectFeatureVectorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class ModuleRiskScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    complexity_score: float
    dependency_risk_score: float
    finding_severity_score: float
    composite_risk_score: float
    risk_level: str


class RegressionRiskPredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probability: float
    risk_level: str
    contributing_factors: List[str]
    summary: str


class TechnicalDebtEstimateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    debt_score: float
    risk_level: str
    estimated_remediation_hours: float
    contributing_factors: List[str]
    summary: str


class QualityTrendPredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str
    current_health_score: float
    projected_next_health_score: float
    slope_per_run: float
    data_points_used: int
    summary: str


class FailureProbabilityPredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probability: float
    risk_level: str
    contributing_factors: List[str]
    summary: str


class MLPredictionReportResponse(BaseModel):
    """Mirrors `MLPredictionReport.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    root_path: str
    generated_at: str
    feature_vector: ProjectFeatureVectorResponse
    module_risk_scores: List[ModuleRiskScoreResponse]
    regression_risk: RegressionRiskPredictionResponse
    technical_debt: TechnicalDebtEstimateResponse
    quality_trend: QualityTrendPredictionResponse
    failure_probability: FailureProbabilityPredictionResponse
