"""Route tests for /api/v1/inspection, including project-id header
enforcement shared by every project-scoped route (ProjectIsolationMiddleware)."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_inspection_service
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.exceptions import InvalidInspectionTargetError
from app.core.inspection_engine.models import InspectionReport
from app.main import app

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubService:
    def __init__(self, report=None, error=None) -> None:
        self.report = report
        self.error = error
        self.calls = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        if self.error:
            raise self.error
        return self.report


def _report() -> InspectionReport:
    return InspectionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
        health_score=87.5,
    )


def test_run_inspection_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/inspection/run", json={"root_path": "/tmp/demo"})
    assert response.status_code == 400
    assert response.json()["error"] == "missing_project_id"


def test_run_inspection_returns_serialized_report(client, project_headers):
    stub = _StubService(report=_report())
    app.dependency_overrides[get_inspection_service] = lambda: stub

    response = client.post("/api/v1/inspection/run", json={"root_path": "/tmp/demo"}, headers=project_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "demo-project"
    assert body["health_score"] == 87.5
    assert stub.calls == [("demo-project", "/tmp/demo")]


def test_run_inspection_maps_invalid_target_to_400(client, project_headers):
    stub = _StubService(error=InvalidInspectionTargetError("not a directory"))
    app.dependency_overrides[get_inspection_service] = lambda: stub

    response = client.post("/api/v1/inspection/run", json={"root_path": "/nope"}, headers=project_headers)

    assert response.status_code == 400
    assert response.json()["error"] == "InvalidInspectionTargetError"


def test_run_inspection_rejects_empty_root_path(client, project_headers):
    response = client.post("/api/v1/inspection/run", json={"root_path": ""}, headers=project_headers)
    assert response.status_code == 422
