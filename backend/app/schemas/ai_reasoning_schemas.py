"""
VIDUR Schemas
Submodule: AI Reasoning
Purpose: Request/response shapes for the AI Reasoning module's routes.
Response schemas mirror `app.core.ai_reasoning.models` `to_dict()`
output field-for-field; the engine's own dataclasses remain the single
source of truth for report content (Article 31-32).
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.inspection_schemas import FindingResponse


class ReasoningRunRequest(BaseModel):
    """Request to run a full inspection followed by AI reasoning over
    a project root already present on the VIDUR backend's own file
    system."""

    model_config = ConfigDict(extra="forbid")

    root_path: str = Field(..., min_length=1, description="Absolute path to the project root to inspect and reason about.")


class IssueCorrelationGroupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: str
    key: str
    findings: List[FindingResponse]
    summary: str


class DependencyImpactAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    direct_dependents: int
    transitive_dependents: int
    dependent_paths: List[str]
    finding_count: int
    risk_score: float


class DebuggingHypothesisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_code: str
    probable_cause: str
    explanation: str
    suggested_next_steps: List[str]
    occurrence_count: int
    related_files: List[str]


class DriftInsightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    churn_level: str
    added_count: int
    removed_count: int
    modified_count: int
    high_impact_files: List[str]
    summary: str


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: str
    category: str
    title: str
    description: str
    supporting_finding_codes: List[str]
    affected_files: List[str]


class ReasoningReportResponse(BaseModel):
    """Mirrors `ReasoningReport.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    root_path: str
    generated_at: str
    correlation_groups: List[IssueCorrelationGroupResponse]
    dependency_assessments: List[DependencyImpactAssessmentResponse]
    debugging_hypotheses: List[DebuggingHypothesisResponse]
    drift_insight: Optional[DriftInsightResponse] = None
    recommendations: List[RecommendationResponse]
