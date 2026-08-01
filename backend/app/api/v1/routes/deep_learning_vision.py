"""
VIDUR API Layer
Module: Deep Learning Vision
Purpose: Route for comparing two caller-supplied visual snapshots,
scoped to the active Project ID bound by `ProjectIsolationMiddleware`.
Ships behind the `MAJOR_DEEP_LEARNING_VISUAL_INSPECTION` feature flag
(Article 41-44), disabled by default - the route always exists and
compiles, but `DeepLearningVisionEngine.run` raises
`DeepLearningVisionDisabledError` (mapped to HTTP 403 by
`app.api.v1.error_handlers`) until the flag is enabled.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_deep_learning_vision_service, get_project_id
from app.schemas.deep_learning_vision_schemas import (
    VisualComparisonReportResponse,
    VisualComparisonRunRequest,
)
from app.services.deep_learning_vision_service import DeepLearningVisionService

router = APIRouter(prefix="/deep-learning-vision", tags=["Deep Learning Vision"])


@router.post(
    "/compare", response_model=VisualComparisonReportResponse, summary="Compare two visual snapshots"
)
async def run_visual_comparison(
    body: VisualComparisonRunRequest,
    project_id: str = Depends(get_project_id),
    service: DeepLearningVisionService = Depends(get_deep_learning_vision_service),
) -> VisualComparisonReportResponse:
    report = await service.run(
        project_id,
        body.baseline,
        body.current,
        canvas_width=body.canvas_width,
        canvas_height=body.canvas_height,
    )
    return VisualComparisonReportResponse.model_validate(report.to_dict())
