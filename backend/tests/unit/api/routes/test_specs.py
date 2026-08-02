"""Route tests for /api/v1/specs, including the
MAJOR_IOT_ENVIRONMENTAL_ANALYTICS feature-flag-disabled path (Article
41-44: ships disabled by default, mapped to HTTP 403)."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_specs_prediction_engine, get_specs_storage
from app.core.specs.enums import ConfidenceLevel
from app.core.specs.exceptions import SpecsDisabledError, SpecsPredictionDisabledError
from app.core.specs.models import (
    CalendarSnapshot,
    ComputerMetrics,
    Deadline,
    EnvironmentalMetrics,
    LastSessionSummary,
    MetricReading,
    PersonalMetrics,
    RecentSessionsComparison,
    SpecsPredictionReport,
    SpecsSnapshot,
    UpcomingSessionPrediction,
    WeeklyCodingTime,
    WeeklyPoint,
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


class _StubPredictionEngine:
    def __init__(self, error=None) -> None:
        self.error = error

    async def predict(self, project_id):
        if self.error:
            raise self.error
        week_start = _NOW.date()
        return SpecsPredictionReport(
            project_id=project_id,
            generated_at=_NOW,
            upcoming_session=UpcomingSessionPrediction(
                likelihood_score=20.0,
                predicted_duration_minutes=None,
                predicted_success_score=None,
                confidence=ConfidenceLevel.NONE,
                basis="no history",
            ),
            last_session=LastSessionSummary(
                has_session=False,
                started_at=None,
                ended_at=None,
                duration_minutes=None,
                success_score=None,
                success_score_basis=None,
                message="No sessions have been recorded yet.",
            ),
            recent_sessions=RecentSessionsComparison(
                sessions_considered=0,
                success_scores=[],
                average_success_score=None,
                message="No sessions have been recorded yet.",
            ),
            weekly_coding_time=WeeklyCodingTime(
                project_id=project_id,
                week_start=week_start,
                week_end=week_start,
                points=[
                    WeeklyPoint(day_of_week="Thursday", date=week_start, total_minutes=0.0, session_count=0)
                ],
            ),
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


def test_get_prediction_returns_all_four_outputs(client, project_headers):
    app.dependency_overrides[get_specs_prediction_engine] = lambda: _StubPredictionEngine()
    response = client.get("/api/v1/specs/prediction", headers=project_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "demo-project"
    assert set(body.keys()) >= {
        "upcoming_session",
        "last_session",
        "recent_sessions",
        "weekly_coding_time",
    }
    assert body["upcoming_session"]["confidence"] == "none"
    assert body["last_session"]["has_session"] is False
    assert body["recent_sessions"]["sessions_considered"] == 0
    assert len(body["weekly_coding_time"]["points"]) == 1


def test_get_prediction_maps_disabled_feature_flag_to_403(client, project_headers):
    app.dependency_overrides[get_specs_prediction_engine] = lambda: _StubPredictionEngine(
        error=SpecsPredictionDisabledError(
            "Specs prediction was requested but the MAJOR_PREDICTIVE_DASHBOARDS feature flag is disabled."
        )
    )
    response = client.get("/api/v1/specs/prediction", headers=project_headers)
    assert response.status_code == 403
    assert response.json()["error"] == "SpecsPredictionDisabledError"


def test_get_prediction_without_project_id_header_returns_400(client):
    response = client.get("/api/v1/specs/prediction")
    assert response.status_code == 400
