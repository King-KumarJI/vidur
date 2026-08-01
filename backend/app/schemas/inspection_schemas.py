"""
VIDUR Schemas
Submodule: Inspection Engine
Purpose: Request/response shapes for the Inspection Engine module's
routes. Response schemas mirror `app.core.inspection_engine.models`
`to_dict()` output field-for-field; the engine's own dataclasses
remain the single source of truth for report content (Article 31-32).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InspectionRunRequest(BaseModel):
    """Request to run a full inspection of a project root already
    present on the VIDUR backend's own file system."""

    model_config = ConfigDict(extra="forbid")

    root_path: str = Field(..., min_length=1, description="Absolute path to the project root to inspect.")


class FileRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    absolute_path: str
    size_bytes: int
    line_count: int
    extension: str
    content_hash: str


class FileMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    function_count: int
    class_count: int
    max_cyclomatic_complexity: int
    average_cyclomatic_complexity: float
    docstring_coverage: float
    has_syntax_error: bool


class FindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    severity: str
    code: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None


class InspectionSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    root_path: str
    generated_at: str
    files: Dict[str, FileRecordResponse]


class InspectionReportResponse(BaseModel):
    """Mirrors `InspectionReport.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    root_path: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    files: List[FileRecordResponse]
    file_metrics: List[FileMetricsResponse]
    findings: List[FindingResponse]
    health_score: float
    snapshot: Optional[InspectionSnapshotResponse] = None
