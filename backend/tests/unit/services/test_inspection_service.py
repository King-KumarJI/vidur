"""Unit tests for app.services.inspection_service.

Exercises InspectionService's orchestration logic - baseline snapshot
lookup and post-run persistence - against stub InspectionEngine /
MemoryEngine collaborators (constructor-injected, same DI pattern as
every prior module's engine tests), so it is verified independent of
real file-system scanning or a live database.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from app.config.feature_flags import FeatureFlag
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import FileRecord, InspectionReport, InspectionSnapshot
from app.memory.enums import MemoryRecordType
from app.memory.models import MemoryRecord
from app.services import inspection_service as inspection_service_module
from app.services.inspection_service import InspectionService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubEngine:
    def __init__(self, report: InspectionReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    def run(self, project_id, root_path, previous_snapshot=None):
        self.calls.append((project_id, root_path, previous_snapshot))
        return self.report


class _StubMemoryEngine:
    def __init__(self, history_records: Optional[List[MemoryRecord]] = None) -> None:
        self._history_records = history_records or []
        self.recorded: List[InspectionReport] = []

    async def history(self, project_id, record_type=None, limit=None):
        return self._history_records[:limit] if limit is not None else self._history_records

    async def record_inspection(self, report: InspectionReport) -> MemoryRecord:
        self.recorded.append(report)
        return MemoryRecord(
            record_id="rec-1",
            project_id=report.project_id,
            record_type=MemoryRecordType.INSPECTION,
            recorded_at=_NOW,
            summary="stub",
            payload=report.to_dict(),
            health_score=report.health_score,
        )


def _report(project_id: str = "demo-project") -> InspectionReport:
    return InspectionReport(
        project_id=project_id,
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
        health_score=90.0,
    )


def test_run_passes_none_baseline_when_no_history_exists():
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine(history_records=[])
    service = InspectionService(engine=engine, memory_engine=memory_engine)

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert engine.calls[0] == ("demo-project", "/tmp/demo", None)


def test_run_persists_report_when_memory_enabled():
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = InspectionService(engine=engine, memory_engine=memory_engine)

    report = asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == [report]


def test_run_skips_baseline_lookup_and_persistence_when_memory_disabled(monkeypatch):
    monkeypatch.setattr(
        inspection_service_module.feature_flags,
        "is_enabled",
        lambda flag: flag != FeatureFlag.MINOR_PROJECT_MEMORY,
    )
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = InspectionService(engine=engine, memory_engine=memory_engine)

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert engine.calls[0] == ("demo-project", "/tmp/demo", None)
    assert memory_engine.recorded == []


def test_run_deserializes_previous_snapshot_from_history():
    file_record = FileRecord(
        relative_path="a.py",
        absolute_path="/tmp/demo/a.py",
        size_bytes=10,
        line_count=1,
        extension=".py",
        content_hash="abc123",
    )
    snapshot = InspectionSnapshot(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=_NOW,
        files={"a.py": file_record},
    )
    previous_report = _report()
    previous_report.snapshot = snapshot
    history_record = MemoryRecord(
        record_id="rec-0",
        project_id="demo-project",
        record_type=MemoryRecordType.INSPECTION,
        recorded_at=_NOW,
        summary="previous run",
        payload=previous_report.to_dict(),
        health_score=90.0,
    )

    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine(history_records=[history_record])
    service = InspectionService(engine=engine, memory_engine=memory_engine)

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    _, _, previous_snapshot = engine.calls[0]
    assert previous_snapshot is not None
    assert previous_snapshot.files["a.py"].content_hash == "abc123"


def test_run_treats_missing_snapshot_field_as_no_baseline():
    previous_report = _report()
    history_record = MemoryRecord(
        record_id="rec-0",
        project_id="demo-project",
        record_type=MemoryRecordType.INSPECTION,
        recorded_at=_NOW,
        summary="previous run without a snapshot",
        payload=previous_report.to_dict(),
        health_score=90.0,
    )

    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine(history_records=[history_record])
    service = InspectionService(engine=engine, memory_engine=memory_engine)

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert engine.calls[0] == ("demo-project", "/tmp/demo", None)
