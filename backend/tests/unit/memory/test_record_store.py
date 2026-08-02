"""Unit tests for app.memory.record_store.

Exercised against an in-memory fake standing in for a motor
AsyncIOMotorCollection, since no live MongoDB server is available in
this environment (matching the "Pending Verification: Live
MongoDB/ChromaDB connectivity" note carried by every prior module's
tracker entry). MemoryRecordStore accepts an injectable
`database_provider` for exactly this purpose.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest
from pymongo.errors import PyMongoError

from app.memory.enums import MemoryRecordType
from app.memory.exceptions import MemoryPersistenceError
from app.memory.models import MemoryRecord
from app.memory.record_store import MemoryRecordStore

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeCursor:
    def __init__(self, documents: List[Dict[str, Any]]) -> None:
        self._documents = documents
        self._limit = None

    def sort(self, key: str, direction: int) -> "_FakeCursor":
        self._documents = sorted(self._documents, key=lambda d: d[key], reverse=(direction == -1))
        return self

    def limit(self, count: int) -> "_FakeCursor":
        self._limit = count
        return self

    async def to_list(self, length=None) -> List[Dict[str, Any]]:
        documents = self._documents
        if self._limit is not None:
            documents = documents[: self._limit]
        elif length is not None:
            documents = documents[:length]
        return list(documents)


class _FakeCollection:
    def __init__(self, fail: bool = False) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._fail = fail

    async def replace_one(self, filter_: Dict[str, Any], document: Dict[str, Any], upsert: bool = False):
        if self._fail:
            raise PyMongoError("simulated failure")
        self._store[filter_["_id"]] = document

    def find(self, query: Dict[str, Any]) -> _FakeCursor:
        if self._fail:
            raise PyMongoError("simulated failure")

        def matches(document: Dict[str, Any]) -> bool:
            for key, expected in query.items():
                if isinstance(expected, dict):
                    if "$in" in expected and document.get(key) not in expected["$in"]:
                        return False
                    if "$ne" in expected and document.get(key) == expected["$ne"]:
                        return False
                elif document.get(key) != expected:
                    return False
            return True

        return _FakeCursor([document for document in self._store.values() if matches(document)])


class _FakeDatabase:
    def __init__(self, fail: bool = False) -> None:
        self._collections: Dict[str, _FakeCollection] = {}
        self._fail = fail

    def __getitem__(self, name: str) -> _FakeCollection:
        return self._collections.setdefault(name, _FakeCollection(fail=self._fail))


def _store(fail: bool = False) -> MemoryRecordStore:
    databases: Dict[str, _FakeDatabase] = {}

    def provider(project_id: str) -> _FakeDatabase:
        return databases.setdefault(project_id, _FakeDatabase(fail=fail))

    return MemoryRecordStore(database_provider=provider)


def _record(record_id: str, offset_minutes: int, health_score=91.0, record_type=MemoryRecordType.INSPECTION) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        project_id="demo-project",
        record_type=record_type,
        recorded_at=_BASE_TIME + timedelta(minutes=offset_minutes),
        summary=f"summary {record_id}",
        payload={"record_id": record_id},
        health_score=health_score,
    )


def test_save_persists_record_idempotently():
    store = _store()
    record = _record("rec-1", 0)

    async def scenario():
        await store.save(record)
        await store.save(record)  # replay should not create a duplicate
        return await store.list_records("demo-project")

    records = asyncio.run(scenario())
    assert len(records) == 1
    assert records[0].record_id == "rec-1"


def test_list_records_orders_most_recent_first_and_respects_limit():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 0))
        await store.save(_record("rec-2", 5))
        await store.save(_record("rec-3", 10))
        return await store.list_records("demo-project", limit=2)

    records = asyncio.run(scenario())
    assert [record.record_id for record in records] == ["rec-3", "rec-2"]


def test_list_records_filters_by_record_type():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 0, record_type=MemoryRecordType.INSPECTION))
        await store.save(_record("rec-2", 1, record_type=MemoryRecordType.NLP))
        return await store.list_records("demo-project", record_type=MemoryRecordType.NLP)

    records = asyncio.run(scenario())
    assert [record.record_id for record in records] == ["rec-2"]


def test_get_by_ids_returns_only_matching_project_records():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 0))
        other_provider_records = await store.get_by_ids("other-project", ["rec-1"])
        same_project_records = await store.get_by_ids("demo-project", ["rec-1", "missing"])
        return other_provider_records, same_project_records

    other_project, same_project = asyncio.run(scenario())
    assert other_project == []
    assert [record.record_id for record in same_project] == ["rec-1"]


def test_get_by_ids_returns_empty_list_for_empty_input():
    store = _store()
    assert asyncio.run(store.get_by_ids("demo-project", [])) == []


def test_health_score_history_is_oldest_first_and_excludes_none():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 10, health_score=70.0))
        await store.save(_record("rec-2", 0, health_score=60.0))
        await store.save(_record("rec-3", 5, health_score=None))
        return await store.health_score_history("demo-project")

    scores = asyncio.run(scenario())
    assert scores == [60.0, 70.0]


def test_health_score_history_filters_by_record_types():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 0, health_score=60.0, record_type=MemoryRecordType.INSPECTION))
        await store.save(_record("rec-2", 5, health_score=80.0, record_type=MemoryRecordType.ML_PREDICTION))
        return await store.health_score_history(
            "demo-project", record_types=[MemoryRecordType.ML_PREDICTION]
        )

    scores = asyncio.run(scenario())
    assert scores == [80.0]


def test_quality_trend_training_data_is_oldest_first_and_paired_with_finding_counts():
    store = _store()

    async def scenario():
        record_a = _record("rec-1", 5, health_score=70.0)
        record_a = MemoryRecord(
            record_id=record_a.record_id,
            project_id=record_a.project_id,
            record_type=record_a.record_type,
            recorded_at=record_a.recorded_at,
            summary=record_a.summary,
            payload={"findings": [{"id": "f1"}, {"id": "f2"}]},
            health_score=record_a.health_score,
        )
        record_b = _record("rec-2", 0, health_score=60.0)
        record_b = MemoryRecord(
            record_id=record_b.record_id,
            project_id=record_b.project_id,
            record_type=record_b.record_type,
            recorded_at=record_b.recorded_at,
            summary=record_b.summary,
            payload={"findings": [{"id": "f1"}]},
            health_score=record_b.health_score,
        )
        await store.save(record_a)
        await store.save(record_b)
        return await store.quality_trend_training_data("demo-project")

    training_data = asyncio.run(scenario())
    assert training_data == [(60.0, 1), (70.0, 2)]


def test_quality_trend_training_data_excludes_non_inspection_records():
    store = _store()

    async def scenario():
        inspection = _record("rec-1", 0, health_score=60.0, record_type=MemoryRecordType.INSPECTION)
        inspection = MemoryRecord(
            record_id=inspection.record_id,
            project_id=inspection.project_id,
            record_type=inspection.record_type,
            recorded_at=inspection.recorded_at,
            summary=inspection.summary,
            payload={"findings": [{"id": "f1"}]},
            health_score=inspection.health_score,
        )
        ml_prediction = _record(
            "rec-2", 5, health_score=80.0, record_type=MemoryRecordType.ML_PREDICTION
        )
        await store.save(inspection)
        await store.save(ml_prediction)
        return await store.quality_trend_training_data("demo-project")

    training_data = asyncio.run(scenario())
    assert training_data == [(60.0, 1)]


def test_quality_trend_training_data_treats_missing_findings_key_as_zero():
    store = _store()

    async def scenario():
        await store.save(_record("rec-1", 0, health_score=60.0))
        return await store.quality_trend_training_data("demo-project")

    training_data = asyncio.run(scenario())
    assert training_data == [(60.0, 0)]


def test_quality_trend_training_data_wraps_pymongo_errors():
    store = _store(fail=True)
    with pytest.raises(MemoryPersistenceError):
        asyncio.run(store.quality_trend_training_data("demo-project"))


def test_save_wraps_pymongo_errors():
    store = _store(fail=True)
    with pytest.raises(MemoryPersistenceError):
        asyncio.run(store.save(_record("rec-1", 0)))


def test_list_records_wraps_pymongo_errors():
    store = _store(fail=True)
    with pytest.raises(MemoryPersistenceError):
        asyncio.run(store.list_records("demo-project"))
