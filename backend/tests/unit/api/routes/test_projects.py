"""Route tests for /api/v1/projects (exempt from ProjectIsolationMiddleware)."""

from app.api.v1.dependencies import get_project_service
from app.core.project_isolation.exceptions import InvalidProjectIdError
from app.main import app


class _StubService:
    def validate(self, project_id: str) -> dict:
        return {"project_id": project_id.lower(), "valid": True}

    def resource_names(self, project_id: str) -> dict:
        if project_id == "!!bad!!":
            raise InvalidProjectIdError("bad project id")
        return {
            "project_id": project_id.lower(),
            "mongodb_database": f"vidur_project_{project_id.lower()}",
            "chromadb_collection": f"vidur_project_{project_id.lower()}",
        }


def test_validate_project_id(client):
    app.dependency_overrides[get_project_service] = lambda: _StubService()

    response = client.post("/api/v1/projects/validate", json={"project_id": "Demo-Project"})

    assert response.status_code == 200
    assert response.json() == {"project_id": "demo-project", "valid": True}


def test_get_project_resources(client):
    app.dependency_overrides[get_project_service] = lambda: _StubService()

    response = client.get("/api/v1/projects/demo-project/resources")

    assert response.status_code == 200
    body = response.json()
    assert body["mongodb_database"] == "vidur_project_demo-project"


def test_get_project_resources_maps_invalid_project_id_to_400(client):
    app.dependency_overrides[get_project_service] = lambda: _StubService()

    response = client.get("/api/v1/projects/!!bad!!/resources")

    assert response.status_code == 400
    assert response.json()["error"] == "InvalidProjectIdError"
