"""
VIDUR API Layer
Module: Memory
Purpose: Routes for recalling VIDUR's own analysis history for the
active Project ID bound by `ProjectIsolationMiddleware`: semantic
recall, chronological history, and health-score trend. Recording
memory records is not exposed as its own route - every pipeline route
(Inspection Engine, AI Reasoning, NLP, ML Prediction, Deep Learning
Vision) already records its own report as a side effect of running,
via each module's own service.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_memory_service, get_project_id
from app.schemas.memory_schemas import (
    HealthScoreTrendResponse,
    MemoryHistoryResponse,
    MemoryRecallRequest,
    MemoryRecallMatchResponse,
)
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post("/recall", response_model=List[MemoryRecallMatchResponse], summary="Semantically recall past analysis records")
async def recall_memory(
    body: MemoryRecallRequest,
    project_id: str = Depends(get_project_id),
    service: MemoryService = Depends(get_memory_service),
) -> List[MemoryRecallMatchResponse]:
    matches = await service.recall(project_id, body.query_text, body.top_k, body.record_type)
    return [MemoryRecallMatchResponse.model_validate(match.to_dict()) for match in matches]


@router.get("/history", response_model=MemoryHistoryResponse, summary="List recorded analysis history")
async def get_memory_history(
    project_id: str = Depends(get_project_id),
    record_type: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, gt=0),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryHistoryResponse:
    records = await service.history(project_id, record_type, limit)
    return MemoryHistoryResponse.model_validate({"records": [record.to_dict() for record in records]})


@router.get("/health-score-trend", response_model=HealthScoreTrendResponse, summary="Get recorded health-score trend")
async def get_health_score_trend(
    project_id: str = Depends(get_project_id),
    record_type: Optional[List[str]] = Query(default=None, alias="record_types"),
    limit: Optional[int] = Query(default=None, gt=0),
    service: MemoryService = Depends(get_memory_service),
) -> HealthScoreTrendResponse:
    health_scores = await service.health_score_trend(project_id, record_type, limit)
    return HealthScoreTrendResponse.model_validate({"health_scores": health_scores})
