"""
VIDUR Schemas Package.

Single import surface for every Pydantic request/response model used
by `backend/app/api/v1/routes`. One submodule per API-facing module,
matching the routes package layout.
"""

from app.schemas.ai_reasoning_schemas import ReasoningReportResponse, ReasoningRunRequest
from app.schemas.common import ErrorResponse
from app.schemas.config_schemas import AppInfoResponse, FeatureFlagsResponse
from app.schemas.deep_learning_vision_schemas import (
    VisualComparisonReportResponse,
    VisualComparisonRunRequest,
)
from app.schemas.health_schemas import DatabaseHealthResponse
from app.schemas.inspection_schemas import InspectionReportResponse, InspectionRunRequest
from app.schemas.memory_schemas import (
    HealthScoreTrendResponse,
    MemoryHistoryResponse,
    MemoryRecallRequest,
    MemoryRecordResponse,
)
from app.schemas.ml_prediction_schemas import MLPredictionReportResponse, MLPredictionRunRequest
from app.schemas.nlp_schemas import NLPReportResponse, NLPRunRequest
from app.schemas.project_schemas import (
    ProjectIdRequest,
    ProjectResourcesResponse,
    ProjectValidationResponse,
)

__all__ = [
    "ErrorResponse",
    "AppInfoResponse",
    "FeatureFlagsResponse",
    "ProjectIdRequest",
    "ProjectValidationResponse",
    "ProjectResourcesResponse",
    "DatabaseHealthResponse",
    "InspectionRunRequest",
    "InspectionReportResponse",
    "ReasoningRunRequest",
    "ReasoningReportResponse",
    "NLPRunRequest",
    "NLPReportResponse",
    "MLPredictionRunRequest",
    "MLPredictionReportResponse",
    "VisualComparisonRunRequest",
    "VisualComparisonReportResponse",
    "MemoryRecallRequest",
    "MemoryRecordResponse",
    "MemoryHistoryResponse",
    "HealthScoreTrendResponse",
]
