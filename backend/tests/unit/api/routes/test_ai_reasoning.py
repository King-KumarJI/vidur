"""Route tests for /api/v1/ai-reasoning."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_ai_reasoning_service
from app.core.ai_reasoning.models import ReasoningReport
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import InspectionReport
from app.main import app

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubService:
    def __init__(self, inspection_report, reasoning_report) -> None:
        self.inspection_report = inspection_report
        self.reasoning_report = reasoning_report
        self.calls = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.inspection_report, self.reasoning_report


def test_run_ai_reasoning_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/ai-reasoning/run", json={"root_path": "/tmp/demo"})
    assert response.status_code == 400


def test_run_ai_reasoning_returns_only_the_reasoning_report(client, project_headers):
    inspection_report = InspectionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
    )
    reasoning_report = ReasoningReport(project_id="demo-project", root_path="/tmp/demo", generated_at=_NOW)
    stub = _StubService(inspection_report, reasoning_report)
    app.dependency_overrides[get_ai_reasoning_service] = lambda: stub

    response = client.post("/api/v1/ai-reasoning/run", json={"root_path": "/tmp/demo"}, headers=project_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "demo-project"
    assert "correlation_groups" in body
    assert "status" not in body
    assert stub.calls == [("demo-project", "/tmp/demo")]
