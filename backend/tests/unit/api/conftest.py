"""Shared fixtures for API Layer route tests.

`client` is built without entering the app's lifespan context (no
`with TestClient(app) as client:`), so `app.main`'s startup hook never
attempts a real MongoDB/ChromaDB connection - every route under test
gets its service swapped for a stub via `app.dependency_overrides`,
so no route handler touches a real data store either.
"""

from typing import Dict

import pytest
from fastapi.testclient import TestClient

from app.main import app

PROJECT_ID_HEADER = "X-Project-Id"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def project_headers() -> Dict[str, str]:
    return {PROJECT_ID_HEADER: "demo-project"}
