"""
VIDUR API Layer
Submodule: Dependencies
Purpose: Shared FastAPI dependency providers for the v1 API - the
active Project ID (bound by `ProjectIsolationMiddleware` before any
route handler runs) and one factory per service, so routes never
construct a service or engine themselves and tests can override any
of them via `app.dependency_overrides`.
"""

from app.core.project_isolation import get_current_project_id
from app.core.specs.predictor import SpecsPredictionEngine
from app.core.specs.storage import SpecsStorage
from app.services.ai_reasoning_service import AIReasoningService
from app.services.config_service import ConfigService
from app.services.db_health_service import DBHealthService
from app.services.deep_learning_vision_service import DeepLearningVisionService
from app.services.inspection_service import InspectionService
from app.services.memory_service import MemoryService
from app.services.ml_prediction_service import MLPredictionService
from app.services.nlp_service import NLPService
from app.services.project_service import ProjectService


def get_project_id() -> str:
    """Return the Project ID bound to the current request by
    `ProjectIsolationMiddleware`. Raises ProjectContextNotSetError if
    called on a route that is exempt from project-scoping (Article
    21: every project-scoped operation must verify its active Project
    ID before execution)."""
    return get_current_project_id()


def get_config_service() -> ConfigService:
    return ConfigService()


def get_project_service() -> ProjectService:
    return ProjectService()


def get_db_health_service() -> DBHealthService:
    return DBHealthService()


def get_inspection_service() -> InspectionService:
    return InspectionService()


def get_ai_reasoning_service() -> AIReasoningService:
    return AIReasoningService()


def get_nlp_service() -> NLPService:
    return NLPService()


def get_ml_prediction_service() -> MLPredictionService:
    return MLPredictionService()


def get_deep_learning_vision_service() -> DeepLearningVisionService:
    return DeepLearningVisionService()


def get_memory_service() -> MemoryService:
    return MemoryService()


def get_specs_storage() -> SpecsStorage:
    return SpecsStorage()


def get_specs_prediction_engine() -> SpecsPredictionEngine:
    return SpecsPredictionEngine()
