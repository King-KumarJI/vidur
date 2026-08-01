"""
VIDUR API Layer
Module: Inspection Engine
Purpose: Route for running a full static project inspection, scoped
to the active Project ID bound by `ProjectIsolationMiddleware`.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_inspection_service, get_project_id
from app.schemas.inspection_schemas import InspectionReportResponse, InspectionRunRequest
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspection", tags=["Inspection Engine"])


@router.post("/run", response_model=InspectionReportResponse, summary="Run a full project inspection")
async def run_inspection(
    body: InspectionRunRequest,
    project_id: str = Depends(get_project_id),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionReportResponse:
    report = await service.run(project_id, body.root_path)
    return InspectionReportResponse.model_validate(report.to_dict())
