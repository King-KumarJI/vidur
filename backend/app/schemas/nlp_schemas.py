"""
VIDUR Schemas
Submodule: NLP
Purpose: Request/response shapes for the NLP module's routes. Response
schemas mirror `app.core.nlp.models` `to_dict()` output field-for-
field; the engine's own dataclasses remain the single source of truth
for report content (Article 31-32).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NLPRunRequest(BaseModel):
    """Request to run a full NLP analysis of a project root already
    present on the VIDUR backend's own file system."""

    model_config = ConfigDict(extra="forbid")

    root_path: str = Field(..., min_length=1, description="Absolute path to the project root to analyze.")


class RequirementStatementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    source_path: str
    line: int
    keywords: List[str]


class DocumentedIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_title: Optional[str] = None
    declared_features: List[str]
    declared_dependencies: List[str]
    requirement_statements: List[RequirementStatementResponse]


class ImplementedIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyzed_file_count: int
    imported_third_party_packages: List[str]
    file_text_blobs: Dict[str, str]


class ConsistencyFindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    severity: str
    code: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None


class SemanticSimilarityResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_text: str
    best_match_file: Optional[str] = None
    similarity_score: float


class NLPReportResponse(BaseModel):
    """Mirrors `NLPReport.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    root_path: str
    generated_at: str
    documented_intent: DocumentedIntentResponse
    implemented_intent: ImplementedIntentResponse
    consistency_findings: List[ConsistencyFindingResponse]
    semantic_similarity_results: List[SemanticSimilarityResultResponse]
