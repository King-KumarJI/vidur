"""Route tests for /api/v1/nlp."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_nlp_service
from app.core.nlp.models import DocumentedIntent, ImplementedIntent, NLPReport
from app.main import app

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubService:
    def __init__(self, report) -> None:
        self.report = report
        self.calls = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.report


def test_run_nlp_analysis_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/nlp/run", json={"root_path": "/tmp/demo"})
    assert response.status_code == 400


def test_run_nlp_analysis_returns_serialized_report(client, project_headers):
    report = NLPReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=_NOW,
        documented_intent=DocumentedIntent(project_title="Demo"),
        implemented_intent=ImplementedIntent(analyzed_file_count=3),
    )
    stub = _StubService(report)
    app.dependency_overrides[get_nlp_service] = lambda: stub

    response = client.post("/api/v1/nlp/run", json={"root_path": "/tmp/demo"}, headers=project_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["documented_intent"]["project_title"] == "Demo"
    assert body["implemented_intent"]["analyzed_file_count"] == 3
