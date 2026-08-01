"""Smoke tests for app.main.create_app - confirms every router is
mounted at its expected prefix and middleware/exception handlers are
registered, without exercising any route's own business logic (that
is covered by tests/unit/api/routes and tests/unit/services)."""

from fastapi.middleware.cors import CORSMiddleware

from app.core.inspection_engine.exceptions import InspectionEngineError
from app.main import app
from app.middleware import ProjectIsolationMiddleware


def test_expected_middleware_is_registered():
    middleware_classes = [m.cls for m in app.user_middleware]
    assert ProjectIsolationMiddleware in middleware_classes
    assert CORSMiddleware in middleware_classes


def test_domain_exception_handlers_are_registered():
    assert InspectionEngineError in app.exception_handlers


def test_every_module_router_is_mounted():
    client_paths = {route.path for route in app.routes}
    expected_prefixes = (
        "/health",
        "/api/v1/config",
        "/api/v1/projects",
        "/api/v1/inspection",
        "/api/v1/ai-reasoning",
        "/api/v1/nlp",
        "/api/v1/ml-prediction",
        "/api/v1/deep-learning-vision",
        "/api/v1/memory",
    )
    for prefix in expected_prefixes:
        assert any(path.startswith(prefix) for path in client_paths), prefix


def test_docs_are_reachable_without_a_project_id_header(client):
    response = client.get("/docs")
    assert response.status_code == 200
