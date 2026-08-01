"""
VIDUR API Layer
Module: NLP
Purpose: Route for running a full NLP analysis of a project root,
scoped to the active Project ID bound by `ProjectIsolationMiddleware`.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_nlp_service, get_project_id
from app.schemas.nlp_schemas import NLPReportResponse, NLPRunRequest
from app.services.nlp_service import NLPService

router = APIRouter(prefix="/nlp", tags=["NLP"])


@router.post("/run", response_model=NLPReportResponse, summary="Run a full NLP analysis")
async def run_nlp_analysis(
    body: NLPRunRequest,
    project_id: str = Depends(get_project_id),
    service: NLPService = Depends(get_nlp_service),
) -> NLPReportResponse:
    report = await service.run(project_id, body.root_path)
    return NLPReportResponse.model_validate(report.to_dict())
