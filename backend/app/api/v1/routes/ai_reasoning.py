"""
VIDUR API Layer
Module: AI Reasoning
Purpose: Route for running a fresh inspection followed by AI reasoning
over its findings, scoped to the active Project ID bound by
`ProjectIsolationMiddleware`.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_ai_reasoning_service, get_project_id
from app.schemas.ai_reasoning_schemas import ReasoningReportResponse, ReasoningRunRequest
from app.services.ai_reasoning_service import AIReasoningService

router = APIRouter(prefix="/ai-reasoning", tags=["AI Reasoning"])


@router.post("/run", response_model=ReasoningReportResponse, summary="Run inspection + AI reasoning")
async def run_ai_reasoning(
    body: ReasoningRunRequest,
    project_id: str = Depends(get_project_id),
    service: AIReasoningService = Depends(get_ai_reasoning_service),
) -> ReasoningReportResponse:
    _inspection_report, reasoning_report = await service.run(project_id, body.root_path)
    return ReasoningReportResponse.model_validate(reasoning_report.to_dict())
