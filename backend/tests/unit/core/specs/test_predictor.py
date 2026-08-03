"""Unit tests for app.core.specs.predictor (CLAUDE.md Specs Module: ML
Prediction Engine) - all four required outputs, cold-start honesty,
and a concrete worked example proving the weekly zero-fill emits
exactly 7 Mon-Sun points with the correct days zeroed.

Exercised against an injected fake SpecsStorage (no live MongoDB) and
an injected fixed clock (so the weekly Mon-Sun window is deterministic
rather than depending on the day the test happens to run), matching
this codebase's established DI-for-tests pattern
(`SpecsStorage.database_provider`, `local_agent.py`'s `clock=`).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.specs.exceptions import SpecsPredictionDisabledError
from app.core.specs.models import (
    ComputerMetrics,
    EnvironmentalMetrics,
    MetricReading,
    PersonalMetrics,
    SpecsSnapshot,
)
from app.core.specs.predictor import SpecsPredictionEngine
from app.core.specs.storage import SpecsStorage

_MISSING = MetricReading.missing()

# A fixed Wednesday, used as "now" throughout - makes the Mon-Sun week
# window (and every relative-time assertion) fully deterministic.
_NOW = datetime(2026, 1, 7, 15, 0, tzinfo=timezone.utc)
_MONDAY = datetime(2026, 1, 5, tzinfo=timezone.utc).date()


def _snapshot(
    recorded_at: datetime,
    typing: Optional[float] = None,
    mouse: Optional[float] = None,
    project_id: str = "demo-project",
) -> SpecsSnapshot:
    typing_reading = MetricReading.present(typing) if typing is not None else _MISSING
    mouse_reading = MetricReading.present(mouse) if mouse is not None else _MISSING
    return SpecsSnapshot(
        project_id=project_id,
        recorded_at=recorded_at,
        personal=PersonalMetrics(
            last_session_duration_minutes=_MISSING,
            sleep_hours=_MISSING,
            caffeine_intake_mg=_MISSING,
            typing_speed_cpm=typing_reading,
            mouse_activity_rate=mouse_reading,
            break_frequency_per_hour=_MISSING,
        ),
        computer=ComputerMetrics(_MISSING, _MISSING, _MISSING, _MISSING),
        environmental=EnvironmentalMetrics(_MISSING, _MISSING, _MISSING, _MISSING),
    )


def _session_snapshots(start: datetime, count: int, interval_minutes: float = 5.0) -> List[SpecsSnapshot]:
    return [_snapshot(start + timedelta(minutes=i * interval_minutes), typing=40.0) for i in range(count)]


class _FakeStorage:
    def __init__(self, snapshots: List[SpecsSnapshot]) -> None:
        self.snapshots = snapshots

    async def list_snapshots(self, project_id: str, since=None) -> List[SpecsSnapshot]:
        if since is None:
            return list(self.snapshots)
        return [s for s in self.snapshots if s.recorded_at >= since]


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_PREDICTIVE_DASHBOARDS=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_PREDICTIVE_DASHBOARDS=False))


def _engine(snapshots: List[SpecsSnapshot], enabled: bool = True, now: datetime = _NOW) -> SpecsPredictionEngine:
    return SpecsPredictionEngine(
        storage=_FakeStorage(snapshots),
        feature_flag_registry=_enabled_registry() if enabled else _disabled_registry(),
        clock=lambda: now,
    )


def test_predict_disabled_raises():
    engine = _engine([], enabled=False)
    with pytest.raises(SpecsPredictionDisabledError):
        asyncio.run(engine.predict("demo-project"))


def test_predict_cold_start_reports_no_confidence_and_no_fabrication():
    engine = _engine([])
    report = asyncio.run(engine.predict("demo-project"))

    assert report.upcoming_session.confidence.value == "none"
    assert report.upcoming_session.likelihood_score == 20.0
    assert report.upcoming_session.predicted_duration_minutes is None
    assert report.upcoming_session.predicted_success_score is None

    assert report.last_session.has_session is False
    assert report.last_session.message == "No sessions have been recorded yet."

    assert report.recent_sessions.sessions_considered == 0
    assert report.recent_sessions.average_success_score is None


def test_predict_cold_start_with_recent_activity_raises_likelihood():
    # One active snapshot 30 minutes ago (inside the last-hour window),
    # but not enough snapshots anywhere to form a derived session.
    snapshots = [_snapshot(_NOW - timedelta(minutes=30), typing=40.0)]
    engine = _engine(snapshots)
    report = asyncio.run(engine.predict("demo-project"))

    assert report.upcoming_session.confidence.value == "none"
    assert report.upcoming_session.likelihood_score == 70.0


def test_predict_weekly_zero_fill_always_has_exactly_seven_points():
    engine = _engine([])
    report = asyncio.run(engine.predict("demo-project"))
    assert len(report.weekly_coding_time.points) == 7


def test_predict_weekly_zero_fill_concrete_worked_example():
    """Two sessions this week: Monday 09:00-09:20 (20 min) and
    Wednesday 10:00-10:30 (30 min). Every other day of the Mon-Sun week
    containing `_NOW` (2026-01-05 .. 2026-01-11) must come back as an
    explicit zero, never omitted."""
    monday_session = _session_snapshots(datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc), count=5)
    wednesday_session = _session_snapshots(datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc), count=7)
    snapshots = sorted(monday_session + wednesday_session, key=lambda s: s.recorded_at)

    engine = _engine(snapshots)
    report = asyncio.run(engine.predict("demo-project"))
    weekly = report.weekly_coding_time

    assert weekly.week_start.isoformat() == "2026-01-05"
    assert weekly.week_end.isoformat() == "2026-01-11"
    assert len(weekly.points) == 7

    by_day = {point.date.isoformat(): point for point in weekly.points}
    expected_dates = [f"2026-01-{day:02d}" for day in range(5, 12)]
    assert sorted(by_day.keys()) == expected_dates

    assert by_day["2026-01-05"].day_of_week == "Monday"
    assert by_day["2026-01-05"].total_minutes == 20.0
    assert by_day["2026-01-05"].session_count == 1

    assert by_day["2026-01-07"].day_of_week == "Wednesday"
    assert by_day["2026-01-07"].total_minutes == 30.0
    assert by_day["2026-01-07"].session_count == 1

    for date_key in ("2026-01-06", "2026-01-08", "2026-01-09", "2026-01-10", "2026-01-11"):
        assert by_day[date_key].total_minutes == 0.0
        assert by_day[date_key].session_count == 0


def test_predict_last_session_and_recent_sessions_reflect_derived_sessions():
    first = _session_snapshots(datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc), count=5)  # 20 min
    second = _session_snapshots(datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc), count=9)  # 40 min
    snapshots = sorted(first + second, key=lambda s: s.recorded_at)

    engine = _engine(snapshots)
    report = asyncio.run(engine.predict("demo-project"))

    assert report.last_session.has_session is True
    assert report.last_session.duration_minutes == 40.0

    assert report.recent_sessions.sessions_considered == 2
    assert "fewer than 5" in report.recent_sessions.message


def test_predict_cold_start_never_claims_trained_model_confidence():
    engine = _engine([])
    report = asyncio.run(engine.predict("demo-project"))
    assert "not a trained-model prediction" in report.upcoming_session.basis


def test_predict_upcoming_session_likelihood_always_in_percentage_range():
    """`likelihood_score` is documented (and consumed by the frontend,
    which renders it directly as `{value}%`) as a plain 0-100
    percentage - never a 0-1 fraction. Covers cold-start-no-telemetry,
    cold-start-with-activity, and warm (derived-sessions) scenarios so
    a regression to a 0-1 fraction (or any other scale) in any branch
    of `_predict_upcoming_session` is caught here rather than surfacing
    as a client-side double-scaling bug (e.g. rendering "7600%")."""
    no_telemetry_report = asyncio.run(_engine([]).predict("demo-project"))
    assert 0.0 <= no_telemetry_report.upcoming_session.likelihood_score <= 100.0

    active_snapshots = [_snapshot(_NOW - timedelta(minutes=30), typing=40.0)]
    active_report = asyncio.run(_engine(active_snapshots).predict("demo-project"))
    assert 0.0 <= active_report.upcoming_session.likelihood_score <= 100.0

    warm_snapshots = sorted(
        _session_snapshots(datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc), count=5)
        + _session_snapshots(datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc), count=9),
        key=lambda s: s.recorded_at,
    )
    warm_report = asyncio.run(_engine(warm_snapshots).predict("demo-project"))
    assert 0.0 <= warm_report.upcoming_session.likelihood_score <= 100.0


class _NaiveMongoCollection:
    """Mimics a *real* (non `tz_aware`) Motor/PyMongo collection: BSON
    date fields round-trip as naive datetimes on read even though the
    value written was aware - see `app.db.mongodb.client`
    (`AsyncIOMotorClient` is built without `tz_aware=True`).

    Every other test in this file drives `SpecsPredictionEngine`
    through `_FakeStorage`, which hands back the exact `SpecsSnapshot`
    objects it was constructed with - always aware, since the tests
    build them with `tzinfo=timezone.utc` throughout. That never
    reproduces the reported bug (`GET /specs/prediction` 500ing against
    real MongoDB) because it never exercises the Mongo boundary at all.
    This fake does, by routing through the real `SpecsStorage` -
    `_document_to_snapshot`'s `_as_utc_aware` normalization is the only
    thing standing between this and `TypeError: can't compare
    offset-naive and offset-aware datetimes` in `predictor.py`'s
    `now - timedelta(hours=1)` window comparison.
    """

    def __init__(self) -> None:
        self._documents: List[Dict[str, Any]] = []

    @staticmethod
    def _strip_tz(document: Dict[str, Any]) -> Dict[str, Any]:
        stored = dict(document)
        for key, value in stored.items():
            if isinstance(value, datetime) and value.tzinfo is not None:
                stored[key] = value.astimezone(timezone.utc).replace(tzinfo=None)
        return stored

    async def insert_one(self, document: Dict[str, Any]) -> None:
        self._documents.append(self._strip_tz(document))

    async def find_one(self, query: Dict[str, Any], sort=None) -> Optional[Dict[str, Any]]:
        matches = [d for d in self._documents if all(d.get(k) == v for k, v in query.items())]
        if sort:
            for key, direction in reversed(sort):
                matches = sorted(matches, key=lambda d: d[key], reverse=(direction == -1))
        return matches[0] if matches else None

    def find(self, query: Dict[str, Any]):
        matches = [d for d in self._documents if all(d.get(k) == v for k, v in query.items())]

        class _Cursor:
            def __init__(self, docs: List[Dict[str, Any]]) -> None:
                self._docs = docs

            def sort(self, key: str, direction: int) -> "_Cursor":
                self._docs = sorted(self._docs, key=lambda d: d[key], reverse=(direction == -1))
                return self

            async def to_list(self, length=None) -> List[Dict[str, Any]]:
                return list(self._docs) if length is None else list(self._docs[:length])

        return _Cursor(matches)


class _NaiveMongoDatabase:
    def __init__(self) -> None:
        self._collections: Dict[str, _NaiveMongoCollection] = {}

    def __getitem__(self, name: str) -> _NaiveMongoCollection:
        return self._collections.setdefault(name, _NaiveMongoCollection())


def test_predict_survives_naive_datetimes_returned_by_real_mongo():
    """Integration reproduction of the reported bug: `GET
    /specs/prediction` 500ing with `TypeError: can't compare
    offset-naive and offset-aware datetimes` against real MongoDB. Runs
    `SpecsPredictionEngine.predict` through the *real* `SpecsStorage`
    (not `_FakeStorage`) backed by `_NaiveMongoCollection`, which - like
    real Motor without `tz_aware=True` - returns naive datetimes for
    every BSON date field regardless of the aware value that was
    written. Before `_as_utc_aware` was applied on every Mongo read in
    `storage.py`, `snapshot.recorded_at >= now - timedelta(hours=1)` in
    `_predict_upcoming_session` raised exactly that TypeError the first
    time a real (non-fake) Mongo collection was involved."""
    database = _NaiveMongoDatabase()
    registry = FeatureFlagRegistry(
        overrides=FeatureFlagSettings(
            MAJOR_IOT_ENVIRONMENTAL_ANALYTICS=True,
            MAJOR_PREDICTIVE_DASHBOARDS=True,
        )
    )
    storage = SpecsStorage(database_provider=lambda project_id: database, feature_flag_registry=registry)
    engine = SpecsPredictionEngine(storage=storage, feature_flag_registry=registry)

    async def scenario():
        await storage.ingest("demo-project", personal={"typing_speed_cpm": 40.0})
        return await engine.predict("demo-project")

    report = asyncio.run(scenario())

    assert report.project_id == "demo-project"
    assert len(report.weekly_coding_time.points) == 7
