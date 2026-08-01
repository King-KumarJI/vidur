"""
VIDUR Schemas
Submodule: Memory
Purpose: Request/response shapes for the Memory module's routes.
Response schemas mirror `app.memory.models` `to_dict()` output
field-for-field; the Memory module's own dataclasses remain the single
source of truth for record content (Article 31-32). `payload` stays
an opaque, already-JSON-safe blob, matching `MemoryRecord.payload`'s
own contract - it is the originating report's own `to_dict()` output,
not reinterpreted here.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemoryRecallRequest(BaseModel):
    """Request to semantically recall a project's past analysis
    records most relevant to `query_text`."""

    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(..., min_length=1)
    top_k: int = Field(default=5, gt=0, le=50)
    record_type: Optional[str] = Field(
        default=None, description="Restrict recall to one MemoryRecordType value (e.g. 'inspection')."
    )


class MemoryRecordResponse(BaseModel):
    """Mirrors `MemoryRecord.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    project_id: str
    record_type: str
    recorded_at: str
    summary: str
    payload: Dict[str, Any]
    health_score: Optional[float] = None


class MemoryRecallMatchResponse(BaseModel):
    """Mirrors `MemoryRecallMatch.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    record: MemoryRecordResponse
    similarity_score: float


class MemoryHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: List[MemoryRecordResponse]


class HealthScoreTrendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    health_scores: List[float]
