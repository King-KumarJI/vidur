"""
VIDUR API Layer
Module: ML Prediction
Purpose: Route for running inspection (optionally followed by AI
reasoning) and then ML risk prediction, scoped to the active Project
ID bound by `ProjectIsolationMiddleware`. Ships behind the
`MAJOR_ML_RISK_PREDICTION` feature flag (Article 41-44), disabled by
default - the route always exists and compiles, but
`MLPredictionService.run` raises `MLPredictionDisabledError` (mapped
to HTTP 403 by `app.api.v1.error_handlers`) until the flag is enabled.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_ml_prediction_service, get_project_id
from app.schemas.ml_prediction_schemas import MLPredictionReportResponse, MLPredictionRunRequest
from app.services.ml_prediction_service import MLPredictionService

router = APIRouter(prefix="/ml-prediction", tags=["ML Prediction"])


@router.post("/run", response_model=MLPredictionReportResponse, summary="Run inspection + ML risk prediction")
async def run_ml_prediction(
    body: MLPredictionRunRequest,
    project_id: str = Depends(get_project_id),
    service: MLPredictionService = Depends(get_ml_prediction_service),
) -> MLPredictionReportResponse:
    report = await service.run(project_id, body.root_path, include_reasoning=body.include_reasoning)
    return MLPredictionReportResponse.model_validate(report.to_dict())
