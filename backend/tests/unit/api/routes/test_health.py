"""Route tests for /health (mounted outside the versioned API prefix,
exempt from ProjectIsolationMiddleware)."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_db_health_service
from app.main import app
from app.models.db_health import DatabaseHealthReport


class _StubService:
    def __init__(self, report: DatabaseHealthReport) -> None:
        self.report = report

    async def check(self) -> DatabaseHealthReport:
        return self.report


def test_health_check_requires_no_project_id_header(client):
    report = DatabaseHealthReport(
        mongodb_connected=True, chromadb_connected=True, checked_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    app.dependency_overrides[get_db_health_service] = lambda: _StubService(report)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["mongodb_connected"] is True
    assert body["healthy"] is True


def test_health_check_reports_unhealthy_when_a_store_is_down(client):
    report = DatabaseHealthReport(
        mongodb_connected=False, chromadb_connected=True, checked_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    app.dependency_overrides[get_db_health_service] = lambda: _StubService(report)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["healthy"] is False
