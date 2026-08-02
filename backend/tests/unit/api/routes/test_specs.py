"""Route tests for /api/v1/specs, including the
MAJOR_IOT_ENVIRONMENTAL_ANALYTICS feature-flag-disabled path (Article
41-44: ships disabled by default, mapped to HTTP 403)."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_specs_storage
from app.core.specs.exceptions import SpecsDisabledError
from app.core.specs.models import (
    CalendarSnapshot,
    ComputerMetrics,
    Deadline,
    EnvironmentalMetrics,
    MetricReading,
    PersonalMetrics,
    SpecsSnapshot,
)
from app.main import app

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _all_missing_snapshot() -> SpecsSnapshot:
    missing = MetricReading.missing()
    return SpecsSnapshot(
        project_id="demo-project",
        recorded_at=_NOW,
        personal=PersonalMetrics(missing, missing, missing, missing, missing, missing),
        computer=ComputerMetrics(missing, missing, missing, missing),
        environmental=EnvironmentalMetrics(missing, missing, missing, missing),
    )


class _StubStorage:
    def __init__(self, error=None) -> None:
        self.error = error
        self.deadlines = []

    async def ingest(self, project_id, personal=None, computer=None, environmental=None):
        if self.error:
            raise self.error
        return _all_missing_snapshot()

    async def get_current_snapshot(self, project_id):
        if self.error:
            raise self.error
        return _all_missing_snapshot()

    async def add_deadline(self, project_id, title, due_at, notes=None):
        if self.error:
            raise self.error
        return Deadline(
            deadline_id="deadline-1",
            project_id=project_id,
            title=title,
            due_at=due_at,
            created_at=_NOW,
            notes=notes,
        )

    async def list_deadlines(self, project_id):
        if self.error:
            raise self.error
        return self.deadlines

    async def get_calendar(self, project_id):
        if self.error:
            raise self.error
        return CalendarSnapshot(
            project_id=project_id, current_time=_NOW, day_of_week="Thursday", upcoming_deadlines=self.deadlines
        )


def _disabled_error() -> SpecsDisabledError:
    return SpecsDisabledError(
        "Specs access was requested but the MAJOR_IOT_ENVIRONMENTAL_ANALYTICS feature flag is disabled."
    )


def test_ingest_maps_disabled_feature_flag_to_403(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage(error=_disabled_error())
    response = client.post("/api/v1/specs/ingest", json={}, headers=project_headers)
    assert response.status_code == 403
    assert response.json()["error"] == "SpecsDisabledError"


def test_ingest_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/specs/ingest", json={})
    assert response.status_code == 400


def test_ingest_accepts_partial_payload_and_returns_missing_status(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage()
    response = client.post(
        "/api/v1/specs/ingest", json={"personal": {"sleep_hours": 7.5}}, headers=project_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["personal"]["sleep_hours"]["status"] == "missing"


def test_get_current_snapshot_returns_snapshot(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage()
    response = client.get("/api/v1/specs/current", headers=project_headers)
    assert response.status_code == 200
    assert response.json()["project_id"] == "demo-project"


def test_add_deadline_returns_created_deadline(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage()
    response = client.post(
        "/api/v1/specs/deadlines",
        json={"title": "Ship v1", "due_at": "2026-02-01T00:00:00Z"},
        headers=project_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Ship v1"
    assert body["deadline_id"] == "deadline-1"


def test_list_deadlines_returns_empty_list(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage()
    response = client.get("/api/v1/specs/deadlines", headers=project_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_calendar_returns_day_of_week_and_deadlines(client, project_headers):
    app.dependency_overrides[get_specs_storage] = lambda: _StubStorage()
    response = client.get("/api/v1/specs/calendar", headers=project_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["day_of_week"] == "Thursday"
    assert body["upcoming_deadlines"] == []
