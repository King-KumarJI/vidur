"""Unit tests for app.memory.engine.

Exercised against in-memory fakes for MemoryRecordStore and
MemorySemanticIndex (rather than the real Mongo-/Chroma-backed
implementations, which require a live server) so MemoryEngine's own
orchestration logic - feature-flag gating, project isolation,
project-id normalization, and recall hydration - is verified in
isolation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.deep_learning_vision.enums import ComparisonVerdict
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import InspectionReport
from app.core.project_isolation.exceptions import InvalidProjectIdError
from app.memory.engine import MemoryEngine
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import InvalidMemoryQueryError, MemoryDisabledError
from app.memory.models import MemoryRecord, MemorySemanticMatch

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeRecordStore:
    def __init__(self) -> None:
        self.saved: Dict[str, MemoryRecord] = {}

    async def save(self, record: MemoryRecord) -> MemoryRecord:
        self.saved[record.record_id] = record
        return record

    async def list_records(self, project_id, record_type=None, limit=None) -> List[MemoryRecord]:
        records = [
            record
            for record in self.saved.values()
            if record.project_id == project_id
            and (record_type is None or record.record_type == record_type)
        ]
        records.sort(key=lambda record: record.recorded_at, reverse=True)
        return records[:limit] if limit is not None else records

    async def get_by_ids(self, project_id, record_ids) -> List[MemoryRecord]:
        return [
            self.saved[record_id]
            for record_id in record_ids
            if record_id in self.saved and self.saved[record_id].project_id == project_id
        ]

    async def health_score_history(self, project_id, record_types=None, limit=None) -> List[float]:
        records = [
            record
            for record in self.saved.values()
            if record.project_id == project_id
            and record.health_score is not None
            and (not record_types or record.record_type in record_types)
        ]
        records.sort(key=lambda record: record.recorded_at)
        scores = [record.health_score for record in records]
        return scores[:limit] if limit is not None else scores


class _FakeSemanticIndex:
    def __init__(self) -> None:
        self.indexed: Dict[str, MemoryRecord] = {}

    def index(self, record: MemoryRecord) -> None:
        self.indexed[record.record_id] = record

    def query(
        self, project_id, query_text, top_k: int = 5, record_type: Optional[MemoryRecordType] = None
    ) -> List[MemorySemanticMatch]:
        candidates = [
            record
            for record in self.indexed.values()
            if record.project_id == project_id
            and (record_type is None or record.record_type == record_type)
        ]
        return [
            MemorySemanticMatch(record_id=record.record_id, similarity_score=1.0)
            for record in candidates[:top_k]
        ]


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_PROJECT_MEMORY=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_PROJECT_MEMORY=False))


def _engine(registry: Optional[FeatureFlagRegistry] = None):
    store = _FakeRecordStore()
    index = _FakeSemanticIndex()
    engine = MemoryEngine(
        record_store=store,
        semantic_index=index,
        feature_flag_registry=registry or _enabled_registry(),
    )
    return engine, store, index


def _inspection_report(project_id: str = "demo-project", health_score: float = 88.0) -> InspectionReport:
    return InspectionReport(
        project_id=project_id,
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
        health_score=health_score,
    )


def _visual_report(project_id: str = "demo-project") -> VisualComparisonReport:
    return VisualComparisonReport(
        project_id=project_id,
        baseline_label="before",
        current_label="after",
        generated_at=_NOW,
        verdict=ComparisonVerdict.MATCH,
    )


def test_record_inspection_raises_when_feature_flag_disabled():
    engine, _, _ = _engine(_disabled_registry())
    with pytest.raises(MemoryDisabledError):
        asyncio.run(engine.record_inspection(_inspection_report()))


def test_record_inspection_raises_for_invalid_project_id():
    engine, _, _ = _engine()
    with pytest.raises(InvalidProjectIdError):
        asyncio.run(engine.record_inspection(_inspection_report(project_id="!!invalid!!")))


def test_record_inspection_persists_and_indexes():
    engine, store, index = _engine()

    record = asyncio.run(engine.record_inspection(_inspection_report(health_score=91.0)))

    assert record.project_id == "demo-project"
    assert record.record_type == MemoryRecordType.INSPECTION
    assert record.health_score == 91.0
    assert record.record_id in store.saved
    assert record.record_id in index.indexed


def test_record_visual_comparison_has_no_health_score():
    engine, store, _ = _engine()

    record = asyncio.run(engine.record_visual_comparison(_visual_report()))

    assert record.record_type == MemoryRecordType.VISUAL_REGRESSION
    assert record.health_score is None
    assert store.saved[record.record_id].payload["verdict"] == "match"


def test_record_normalizes_project_id_case():
    engine, _, _ = _engine()
    record = asyncio.run(engine.record_inspection(_inspection_report(project_id="Demo-Project")))
    assert record.project_id == "demo-project"


def test_recall_raises_when_feature_flag_disabled():
    engine, _, _ = _engine(_disabled_registry())
    with pytest.raises(MemoryDisabledError):
        asyncio.run(engine.recall("demo-project", "query"))


def test_recall_raises_for_empty_query_text():
    engine, _, _ = _engine()
    with pytest.raises(InvalidMemoryQueryError):
        asyncio.run(engine.recall("demo-project", "   "))


def test_recall_returns_hydrated_matches():
    engine, _, _ = _engine()
    asyncio.run(engine.record_inspection(_inspection_report()))

    matches = asyncio.run(engine.recall("demo-project", "inspection"))

    assert len(matches) == 1
    assert matches[0].record.record_type == MemoryRecordType.INSPECTION
    assert matches[0].similarity_score == 1.0


def test_recall_returns_empty_list_when_no_records_indexed():
    engine, _, _ = _engine()
    assert asyncio.run(engine.recall("demo-project", "anything")) == []


def test_history_returns_most_recent_first():
    engine, _, _ = _engine()
    asyncio.run(engine.record_inspection(_inspection_report()))
    asyncio.run(engine.record_visual_comparison(_visual_report()))

    records = asyncio.run(engine.history("demo-project"))

    assert len(records) == 2
    assert records[0].recorded_at >= records[1].recorded_at


def test_history_filters_by_record_type():
    engine, _, _ = _engine()
    asyncio.run(engine.record_inspection(_inspection_report()))
    asyncio.run(engine.record_visual_comparison(_visual_report()))

    records = asyncio.run(engine.history("demo-project", record_type=MemoryRecordType.VISUAL_REGRESSION))

    assert len(records) == 1
    assert records[0].record_type == MemoryRecordType.VISUAL_REGRESSION


def test_health_score_trend_raises_when_feature_flag_disabled():
    engine, _, _ = _engine(_disabled_registry())
    with pytest.raises(MemoryDisabledError):
        asyncio.run(engine.health_score_trend("demo-project"))


def test_health_score_trend_returns_oldest_first_scores():
    engine, _, _ = _engine()
    asyncio.run(engine.record_inspection(_inspection_report(health_score=70.0)))
    asyncio.run(engine.record_inspection(_inspection_report(health_score=80.0)))

    scores = asyncio.run(engine.health_score_trend("demo-project"))

    assert scores == [70.0, 80.0]


def test_health_score_trend_excludes_records_without_a_score():
    engine, _, _ = _engine()
    asyncio.run(engine.record_visual_comparison(_visual_report()))
    asyncio.run(engine.record_inspection(_inspection_report(health_score=65.0)))

    scores = asyncio.run(engine.health_score_trend("demo-project"))

    assert scores == [65.0]
