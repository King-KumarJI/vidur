"""Unit tests for app.api.v1.error_handlers.

Registers the real handlers against a throwaway FastAPI app with one
route per exception under test (rather than driving a real service
failure through the full app), so the status-code mapping itself is
verified in isolation from any particular route's business logic.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.error_handlers import register_exception_handlers
from app.core.ai_reasoning.exceptions import InvalidReasoningInputError, ReasoningDisabledError
from app.core.deep_learning_vision.exceptions import DeepLearningVisionDisabledError
from app.core.inspection_engine.exceptions import InspectionDisabledError, InspectionEngineError, InvalidInspectionTargetError
from app.core.ml_prediction.exceptions import MLPredictionDisabledError
from app.core.nlp.exceptions import NLPError
from app.core.project_isolation.exceptions import InvalidProjectIdError, ProjectContextNotSetError
from app.core.specs.exceptions import InvalidSpecsPayloadError, SpecsDisabledError
from app.db.exceptions import DatabaseConnectionError
from app.memory.exceptions import InvalidMemoryQueryError, MemoryDisabledError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/inspection-disabled")
    def _raise_inspection_disabled():
        raise InspectionDisabledError("disabled")

    @app.get("/raise/reasoning-disabled")
    def _raise_reasoning_disabled():
        raise ReasoningDisabledError("disabled")

    @app.get("/raise/ml-prediction-disabled")
    def _raise_ml_prediction_disabled():
        raise MLPredictionDisabledError("disabled")

    @app.get("/raise/deep-learning-vision-disabled")
    def _raise_dlv_disabled():
        raise DeepLearningVisionDisabledError("disabled")

    @app.get("/raise/memory-disabled")
    def _raise_memory_disabled():
        raise MemoryDisabledError("disabled")

    @app.get("/raise/specs-disabled")
    def _raise_specs_disabled():
        raise SpecsDisabledError("disabled")

    @app.get("/raise/invalid-project-id")
    def _raise_invalid_project_id():
        raise InvalidProjectIdError("bad project id")

    @app.get("/raise/invalid-inspection-target")
    def _raise_invalid_target():
        raise InvalidInspectionTargetError("not a directory")

    @app.get("/raise/invalid-reasoning-input")
    def _raise_invalid_reasoning_input():
        raise InvalidReasoningInputError("bad input")

    @app.get("/raise/invalid-memory-query")
    def _raise_invalid_memory_query():
        raise InvalidMemoryQueryError("bad query")

    @app.get("/raise/invalid-specs-payload")
    def _raise_invalid_specs_payload():
        raise InvalidSpecsPayloadError("bad payload")

    @app.get("/raise/project-context-not-set")
    def _raise_context_not_set():
        raise ProjectContextNotSetError("no project bound")

    @app.get("/raise/inspection-engine-error")
    def _raise_inspection_engine_error():
        raise InspectionEngineError("unexpected failure")

    @app.get("/raise/nlp-error")
    def _raise_nlp_error():
        raise NLPError("unexpected failure")

    @app.get("/raise/database-error")
    def _raise_database_error():
        raise DatabaseConnectionError("connection refused")

    return app


def _client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_disabled_errors_map_to_403():
    client = _client()
    for path in (
        "/raise/inspection-disabled",
        "/raise/reasoning-disabled",
        "/raise/ml-prediction-disabled",
        "/raise/deep-learning-vision-disabled",
        "/raise/memory-disabled",
        "/raise/specs-disabled",
    ):
        response = client.get(path)
        assert response.status_code == 403, path


def test_invalid_input_errors_map_to_400():
    client = _client()
    for path in (
        "/raise/invalid-project-id",
        "/raise/invalid-inspection-target",
        "/raise/invalid-reasoning-input",
        "/raise/invalid-memory-query",
        "/raise/invalid-specs-payload",
    ):
        response = client.get(path)
        assert response.status_code == 400, path


def test_project_context_not_set_maps_to_400():
    response = _client().get("/raise/project-context-not-set")
    assert response.status_code == 400


def test_unclassified_domain_errors_map_to_500():
    client = _client()
    for path in ("/raise/inspection-engine-error", "/raise/nlp-error", "/raise/database-error"):
        response = client.get(path)
        assert response.status_code == 500, path


def test_error_envelope_contains_exception_name_and_message():
    response = _client().get("/raise/invalid-project-id")
    body = response.json()
    assert body["error"] == "InvalidProjectIdError"
    assert body["message"] == "bad project id"
