"""
VIDUR API Layer
Submodule: Error Handlers
Purpose: Map every domain exception raised by the modules the API
Layer fronts (Project Isolation, DB, Inspection Engine, AI Reasoning,
NLP, ML Prediction, Deep Learning Vision, Memory) onto a uniform JSON
error envelope and an appropriate HTTP status code, registered once
against each module's base exception class. Starlette resolves a
raised exception's handler by walking its MRO, so registering only the
base classes here is sufficient to catch every subclass (Disabled/
Invalid/etc.) without per-subclass registration.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.ai_reasoning.exceptions import AIReasoningError, InvalidReasoningInputError, ReasoningDisabledError
from app.core.deep_learning_vision.exceptions import (
    DeepLearningVisionDisabledError,
    DeepLearningVisionError,
    ImageDimensionMismatchError,
    InvalidComparisonInputError,
    InvalidImageDataError,
    InvalidLayoutDataError,
)
from app.core.inspection_engine.exceptions import (
    InspectionDisabledError,
    InspectionEngineError,
    InvalidInspectionTargetError,
)
from app.core.ml_prediction.exceptions import InvalidPredictionInputError, MLPredictionDisabledError, MLPredictionError
from app.core.nlp.exceptions import InvalidNLPInputError, NLPDisabledError, NLPError
from app.core.project_isolation.exceptions import (
    CrossProjectAccessError,
    InvalidProjectIdError,
    ProjectContextNotSetError,
    ProjectIsolationError,
    ProjectNotRegisteredError,
)
from app.core.specs.exceptions import (
    InvalidSpecsPayloadError,
    SpecsDisabledError,
    SpecsModuleError,
    SpecsPredictionDisabledError,
)
from app.db.exceptions import DatabaseError
from app.memory.exceptions import InvalidMemoryQueryError, MemoryDisabledError, MemoryModuleError

_DISABLED_ERRORS = (
    InspectionDisabledError,
    ReasoningDisabledError,
    NLPDisabledError,
    MLPredictionDisabledError,
    DeepLearningVisionDisabledError,
    MemoryDisabledError,
    SpecsDisabledError,
    SpecsPredictionDisabledError,
)

_INVALID_INPUT_ERRORS = (
    InvalidProjectIdError,
    InvalidInspectionTargetError,
    InvalidReasoningInputError,
    InvalidNLPInputError,
    InvalidPredictionInputError,
    InvalidComparisonInputError,
    InvalidImageDataError,
    InvalidLayoutDataError,
    ImageDimensionMismatchError,
    InvalidMemoryQueryError,
    InvalidSpecsPayloadError,
    ProjectNotRegisteredError,
    CrossProjectAccessError,
)

_CONTEXT_ERRORS = (ProjectContextNotSetError,)

# Every module's base exception is registered as a handler key.
# Isolation exceptions (e.g. InvalidProjectIdError) subclass
# ProjectIsolationError, which every module's `run()` also lets
# propagate unwrapped, so it is registered directly as well.
_REGISTERED_BASE_EXCEPTIONS = (
    InspectionEngineError,
    AIReasoningError,
    NLPError,
    MLPredictionError,
    DeepLearningVisionError,
    MemoryModuleError,
    SpecsModuleError,
    ProjectIsolationError,
    DatabaseError,
)


def _status_code_for(exc: Exception) -> int:
    if isinstance(exc, _DISABLED_ERRORS):
        return status.HTTP_403_FORBIDDEN
    if isinstance(exc, _INVALID_INPUT_ERRORS):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(exc, _CONTEXT_ERRORS):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=_status_code_for(exc),
        content={"error": type(exc).__name__, "message": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register one exception handler per module's base exception
    class against `app`. Call once at application startup."""
    for base_exception in _REGISTERED_BASE_EXCEPTIONS:
        app.add_exception_handler(base_exception, _handle_domain_error)
