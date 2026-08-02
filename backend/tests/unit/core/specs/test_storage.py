"""Unit tests for app.core.specs.storage.

Exercised against an in-memory fake standing in for a motor
AsyncIOMotorCollection, since no live MongoDB server is available in
this environment - the same pattern `tests/unit/memory/test_record_store.py`
establishes. SpecsStorage accepts an injectable `database_provider` for
exactly this purpose.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
from pymongo.errors import PyMongoError

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.project_isolation.exceptions import InvalidProjectIdError
from app.core.specs.exceptions import (
    InvalidSpecsPayloadError,
    SpecsDisabledError,
    SpecsPersistenceError,
)
from app.core.specs.storage import SpecsStorage

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeCursor:
    def __init__(self, documents: List[Dict[str, Any]]) -> None:
        self._documents = documents

    def sort(self, key: str, direction: int) -> "_FakeCursor":
        self._documents = sorted(self._documents, key=lambda d: d[key], reverse=(direction == -1))
        return self

    async def to_list(self, length=None) -> List[Dict[str, Any]]:
        if length is not None:
            return list(self._documents[:length])
        return list(self._documents)


class _FakeCollection:
    def __init__(self, fail: bool = False) -> None:
        self._documents: List[Dict[str, Any]] = []
        self._fail = fail

    async def insert_one(self, document: Dict[str, Any]) -> None:
        if self._fail:
            raise PyMongoError("simulated failure")
        self._documents.append(dict(document))

    async def find_one(self, query: Dict[str, Any], sort=None) -> Optional[Dict[str, Any]]:
        if self._fail:
            raise PyMongoError("simulated failure")
        matches = [d for d in self._documents if all(d.get(k) == v for k, v in query.items())]
        if sort:
            for key, direction in reversed(sort):
                matches = sorted(matches, key=lambda d: d[key], reverse=(direction == -1))
        return matches[0] if matches else None

    def find(self, query: Dict[str, Any]) -> _FakeCursor:
        if self._fail:
            raise PyMongoError("simulated failure")
        matches = [d for d in self._documents if all(d.get(k) == v for k, v in query.items())]
        return _FakeCursor(matches)


class _FakeDatabase:
    def __init__(self, fail: bool = False) -> None:
        self._collections: Dict[str, _FakeCollection] = {}
        self._fail = fail

    def __getitem__(self, name: str) -> _FakeCollection:
        return self._collections.setdefault(name, _FakeCollection(fail=self._fail))


class _NaiveMongoCollection:
    """Mimics a *real* (non `tz_aware`) Motor/PyMongo collection: BSON
    date fields round-trip as naive datetimes on read, even though the
    value written was timezone-aware - see `app.db.mongodb.client`
    (`AsyncIOMotorClient` is constructed without `tz_aware=True`).

    `_FakeCollection` above stores whatever Python object it was handed
    and hands the *same* object back, so every datetime that passes
    through it stays aware - it can never reproduce the naive/aware
    mismatch that crashed `GET /specs/prediction` against real MongoDB.
    This fake strips `tzinfo` on write, exactly like the real driver
    does, so tests against it exercise the actual bug rather than a
    scenario where every datetime happens to be consistently typed.
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

    def find(self, query: Dict[str, Any]) -> _FakeCursor:
        matches = [d for d in self._documents if all(d.get(k) == v for k, v in query.items())]
        return _FakeCursor(matches)


class _NaiveMongoDatabase:
    def __init__(self) -> None:
        self._collections: Dict[str, _NaiveMongoCollection] = {}

    def __getitem__(self, name: str) -> _NaiveMongoCollection:
        return self._collections.setdefault(name, _NaiveMongoCollection())


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_IOT_ENVIRONMENTAL_ANALYTICS=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_IOT_ENVIRONMENTAL_ANALYTICS=False))


def _storage(fail: bool = False, enabled: bool = True) -> SpecsStorage:
    databases: Dict[str, _FakeDatabase] = {}

    def provider(project_id: str) -> _FakeDatabase:
        return databases.setdefault(project_id, _FakeDatabase(fail=fail))

    return SpecsStorage(
        database_provider=provider,
        feature_flag_registry=_enabled_registry() if enabled else _disabled_registry(),
    )


def test_ingest_disabled_raises():
    storage = _storage(enabled=False)
    with pytest.raises(SpecsDisabledError):
        asyncio.run(storage.ingest("demo-project"))


def test_ingest_invalid_project_id_raises():
    storage = _storage()
    with pytest.raises(InvalidProjectIdError):
        asyncio.run(storage.ingest("!!"))


def test_ingest_marks_omitted_sections_missing():
    storage = _storage()
    snapshot = asyncio.run(storage.ingest("demo-project"))

    assert snapshot.personal.sleep_hours.status.value == "missing"
    assert snapshot.personal.sleep_hours.value is None
    assert snapshot.computer.cpu_usage_percent.status.value == "missing"
    assert snapshot.environmental.temperature_celsius.status.value == "missing"


def test_ingest_marks_partial_section_fields_individually():
    storage = _storage()
    snapshot = asyncio.run(
        storage.ingest(
            "demo-project",
            personal={"sleep_hours": 7.5},
            environmental={"temperature_celsius": 21.0, "source": "hardware"},
        )
    )

    assert snapshot.personal.sleep_hours.status.value == "present"
    assert snapshot.personal.sleep_hours.value == 7.5
    assert snapshot.personal.caffeine_intake_mg.status.value == "missing"

    assert snapshot.environmental.temperature_celsius.status.value == "present"
    assert snapshot.environmental.temperature_celsius.source == "hardware"
    assert snapshot.environmental.humidity_percent.status.value == "missing"


def test_get_current_snapshot_returns_all_missing_when_nothing_ingested():
    storage = _storage()
    snapshot = asyncio.run(storage.get_current_snapshot("demo-project"))

    assert snapshot.personal.sleep_hours.status.value == "missing"
    assert snapshot.computer.cpu_usage_percent.status.value == "missing"
    assert snapshot.environmental.noise_level_db.status.value == "missing"


def test_get_current_snapshot_returns_most_recent_ingestion():
    storage = _storage()

    async def scenario():
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        await storage.ingest("demo-project", personal={"sleep_hours": 8.0})
        return await storage.get_current_snapshot("demo-project")

    snapshot = asyncio.run(scenario())
    assert snapshot.personal.sleep_hours.value == 8.0


def test_get_current_snapshot_merges_fields_across_ingestions_not_just_latest():
    """Reproduces the real bug found in manual testing: the local agent
    posts full computer+personal+environmental data on its own 30s
    interval, then the frontend's manual-input form posts only
    {sleep_hours} independently. Pre-fix, get_current_snapshot returned
    only the single most recent document, so the manual post's narrow
    payload blanked out the CPU/RAM/typing-speed/environmental fields
    that were still current. Per CLAUDE.md's Current snapshot semantics
    (merge, not replace), every individual field's most recently
    reported value must survive regardless of which later ingestion
    call omitted it."""
    storage = _storage()

    async def scenario():
        await storage.ingest(
            "demo-project",
            personal={
                "last_session_duration_minutes": 45.0,
                "sleep_hours": 6.0,
                "caffeine_intake_mg": 80.0,
                "typing_speed_cpm": 220.0,
                "mouse_activity_rate": 30.0,
                "break_frequency_per_hour": 2.0,
            },
            computer={
                "cpu_usage_percent": 55.0,
                "ram_usage_percent": 60.0,
                "disk_io_kbps": 512.0,
                "internet_latency_ms": 20.0,
            },
            environmental={
                "temperature_celsius": 22.0,
                "humidity_percent": 45.0,
                "ambient_light_lux": 300.0,
                "noise_level_db": 35.0,
                "source": "simulation",
            },
        )
        # The frontend's manual-input form posts only sleep_hours,
        # independently of the local agent's next 30s interval post.
        await storage.ingest("demo-project", personal={"sleep_hours": 8.0})
        return await storage.get_current_snapshot("demo-project")

    snapshot = asyncio.run(scenario())

    # The new manual value took effect...
    assert snapshot.personal.sleep_hours.value == 8.0
    # ...but every field from the earlier agent ingestion is still
    # present, not blanked out to "missing".
    assert snapshot.personal.last_session_duration_minutes.value == 45.0
    assert snapshot.personal.caffeine_intake_mg.value == 80.0
    assert snapshot.personal.typing_speed_cpm.value == 220.0
    assert snapshot.personal.mouse_activity_rate.value == 30.0
    assert snapshot.personal.break_frequency_per_hour.value == 2.0

    assert snapshot.computer.cpu_usage_percent.value == 55.0
    assert snapshot.computer.ram_usage_percent.value == 60.0
    assert snapshot.computer.disk_io_kbps.value == 512.0
    assert snapshot.computer.internet_latency_ms.value == 20.0

    assert snapshot.environmental.temperature_celsius.value == 22.0
    assert snapshot.environmental.humidity_percent.value == 45.0
    assert snapshot.environmental.ambient_light_lux.value == 300.0
    assert snapshot.environmental.noise_level_db.value == 35.0
    assert snapshot.environmental.temperature_celsius.source == "simulation"


def test_get_current_snapshot_field_missing_only_if_never_reported():
    """A field that was never present in ANY historical ingestion stays
    genuinely missing after a merge - the merge must not accidentally
    fabricate a value for fields no ingestion ever supplied."""
    storage = _storage()

    async def scenario():
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        await storage.ingest("demo-project", personal={"sleep_hours": 8.0})
        return await storage.get_current_snapshot("demo-project")

    snapshot = asyncio.run(scenario())
    assert snapshot.personal.sleep_hours.value == 8.0
    assert snapshot.personal.caffeine_intake_mg.status.value == "missing"
    assert snapshot.computer.cpu_usage_percent.status.value == "missing"
    assert snapshot.environmental.temperature_celsius.status.value == "missing"


def test_ingest_wraps_pymongo_errors():
    storage = _storage(fail=True)
    with pytest.raises(SpecsPersistenceError):
        asyncio.run(storage.ingest("demo-project"))


def test_add_deadline_persists_and_rejects_blank_title():
    storage = _storage()

    async def scenario():
        deadline = await storage.add_deadline(
            "demo-project", "Ship v1", _BASE_TIME + timedelta(days=1), notes="final review"
        )
        deadlines = await storage.list_deadlines("demo-project")
        return deadline, deadlines

    deadline, deadlines = asyncio.run(scenario())
    assert deadline.title == "Ship v1"
    assert deadline.notes == "final review"
    assert [d.deadline_id for d in deadlines] == [deadline.deadline_id]

    with pytest.raises(InvalidSpecsPayloadError):
        asyncio.run(storage.add_deadline("demo-project", "   ", _BASE_TIME))


def test_list_deadlines_orders_soonest_first():
    storage = _storage()

    async def scenario():
        await storage.add_deadline("demo-project", "Later", _BASE_TIME + timedelta(days=10))
        await storage.add_deadline("demo-project", "Sooner", _BASE_TIME + timedelta(days=1))
        return await storage.list_deadlines("demo-project")

    deadlines = asyncio.run(scenario())
    assert [d.title for d in deadlines] == ["Sooner", "Later"]


def test_list_snapshots_returns_oldest_first():
    storage = _storage()

    async def scenario():
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        await storage.ingest("demo-project", personal={"sleep_hours": 7.0})
        await storage.ingest("demo-project", personal={"sleep_hours": 8.0})
        return await storage.list_snapshots("demo-project")

    snapshots = asyncio.run(scenario())
    assert [s.personal.sleep_hours.value for s in snapshots] == [6.0, 7.0, 8.0]


def test_list_snapshots_empty_when_nothing_ingested():
    storage = _storage()
    snapshots = asyncio.run(storage.list_snapshots("demo-project"))
    assert snapshots == []


def test_list_snapshots_filters_by_since():
    storage = _storage()

    async def scenario():
        # Small sleeps around the cutoff, not just a bare `datetime.now()`
        # sandwiched between two ingests, because this platform's clock
        # has been observed to have coarse (~15ms) resolution (see the
        # `_sequence_counter` design note above) - without them the
        # cutoff could tie with either ingestion's real timestamp.
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        await asyncio.sleep(0.05)
        cutoff = datetime.now(timezone.utc)
        await asyncio.sleep(0.05)
        await storage.ingest("demo-project", personal={"sleep_hours": 7.0})
        return await storage.list_snapshots("demo-project", since=cutoff)

    snapshots = asyncio.run(scenario())
    assert [s.personal.sleep_hours.value for s in snapshots] == [7.0]


def test_list_snapshots_disabled_raises():
    storage = _storage(enabled=False)
    with pytest.raises(SpecsDisabledError):
        asyncio.run(storage.list_snapshots("demo-project"))


def test_get_calendar_excludes_past_deadlines():
    storage = _storage()

    async def scenario():
        await storage.add_deadline("demo-project", "Past", _BASE_TIME - timedelta(days=365 * 20))
        await storage.add_deadline("demo-project", "Future", _BASE_TIME + timedelta(days=365 * 20))
        return await storage.get_calendar("demo-project")

    calendar = asyncio.run(scenario())
    assert [d.title for d in calendar.upcoming_deadlines] == ["Future"]
    assert calendar.day_of_week in {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    }


def _naive_mongo_storage() -> SpecsStorage:
    database = _NaiveMongoDatabase()
    return SpecsStorage(
        database_provider=lambda project_id: database,
        feature_flag_registry=_enabled_registry(),
    )


def test_list_snapshots_normalizes_naive_datetimes_from_real_mongo():
    """Reproduces the naive-vs-aware crash: against a real (non
    `tz_aware`) Motor collection, `recorded_at` comes back naive even
    though `SpecsStorage.ingest` wrote it as aware via `utc_now()`.
    `predictor.py` compares snapshot timestamps against an aware
    `datetime.now(timezone.utc)` (its last-hour window); a naive value
    here raises `TypeError: can't compare offset-naive and
    offset-aware datetimes` on that comparison. Asserting the value is
    aware, and performing that exact comparison, proves the read-side
    fix (`_as_utc_aware` in `_document_to_snapshot`) actually applies."""
    storage = _naive_mongo_storage()

    async def scenario():
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        return await storage.list_snapshots("demo-project")

    snapshots = asyncio.run(scenario())
    assert len(snapshots) == 1
    assert snapshots[0].recorded_at.tzinfo is not None
    # The exact shape of predictor.py's last-hour-window comparison -
    # would raise TypeError pre-fix since recorded_at was naive.
    assert snapshots[0].recorded_at >= datetime.now(timezone.utc) - timedelta(hours=1)


def test_get_current_snapshot_normalizes_naive_datetime_from_real_mongo():
    storage = _naive_mongo_storage()

    async def scenario():
        await storage.ingest("demo-project", personal={"sleep_hours": 6.0})
        return await storage.get_current_snapshot("demo-project")

    snapshot = asyncio.run(scenario())
    assert snapshot.recorded_at.tzinfo is not None
    assert snapshot.recorded_at <= datetime.now(timezone.utc)


def test_deadlines_normalize_naive_datetimes_from_real_mongo():
    storage = _naive_mongo_storage()

    async def scenario():
        due_at = datetime.now(timezone.utc) + timedelta(days=365)
        await storage.add_deadline("demo-project", "Ship v1", due_at)
        deadlines = await storage.list_deadlines("demo-project")
        return deadlines, await storage.get_calendar("demo-project")

    deadlines, calendar = asyncio.run(scenario())
    assert deadlines[0].due_at.tzinfo is not None
    assert deadlines[0].created_at.tzinfo is not None
    # get_calendar compares due_at (naive pre-fix) against an aware
    # `now` - would raise TypeError pre-fix.
    assert calendar.upcoming_deadlines == deadlines
