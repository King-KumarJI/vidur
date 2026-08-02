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
