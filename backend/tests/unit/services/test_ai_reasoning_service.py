"""Unit tests for app.services.ai_reasoning_service.

Exercises AIReasoningService's orchestration - running an inspection
first, reasoning over its report, then persisting - against a stub
InspectionService (rather than a real one) plus stub AIReasoningEngine
/ MemoryEngine collaborators.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

from app.config.feature_flags import FeatureFlag
from app.core.ai_reasoning.models import ReasoningReport
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import InspectionReport
from app.memory.enums import MemoryRecordType
from app.memory.models import MemoryRecord
from app.services import ai_reasoning_service as ai_reasoning_service_module
from app.services.ai_reasoning_service import AIReasoningService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubInspectionService:
    def __init__(self, report: InspectionReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.report


class _StubReasoningEngine:
    def __init__(self, report: ReasoningReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    def run(self, project_id, inspection_report):
        self.calls.append((project_id, inspection_report))
        return self.report


class _StubMemoryEngine:
    def __init__(self) -> None:
        self.recorded: List[ReasoningReport] = []

    async def record_reasoning(self, report: ReasoningReport) -> MemoryRecord:
        self.recorded.append(report)
        return MemoryRecord(
            record_id="rec-1",
            project_id=report.project_id,
            record_type=MemoryRecordType.AI_REASONING,
            recorded_at=_NOW,
            summary="stub",
            payload=report.to_dict(),
        )


def _inspection_report() -> InspectionReport:
    return InspectionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=_NOW,
        completed_at=_NOW,
        health_score=90.0,
    )


def _reasoning_report() -> ReasoningReport:
    return ReasoningReport(project_id="demo-project", root_path="/tmp/demo", generated_at=_NOW)


def test_run_reasons_over_the_freshly_run_inspection():
    inspection_report = _inspection_report()
    inspection_service = _StubInspectionService(inspection_report)
    reasoning_engine = _StubReasoningEngine(_reasoning_report())
    memory_engine = _StubMemoryEngine()
    service = AIReasoningService(
        engine=reasoning_engine, inspection_service=inspection_service, memory_engine=memory_engine
    )

    returned_inspection, returned_reasoning = asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert inspection_service.calls == [("demo-project", "/tmp/demo")]
    assert reasoning_engine.calls == [("demo-project", inspection_report)]
    assert returned_inspection is inspection_report
    assert returned_reasoning is reasoning_engine.report


def test_run_persists_reasoning_report_when_memory_enabled():
    inspection_service = _StubInspectionService(_inspection_report())
    reasoning_engine = _StubReasoningEngine(_reasoning_report())
    memory_engine = _StubMemoryEngine()
    service = AIReasoningService(
        engine=reasoning_engine, inspection_service=inspection_service, memory_engine=memory_engine
    )

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == [reasoning_engine.report]


def test_run_skips_persistence_when_memory_disabled(monkeypatch):
    monkeypatch.setattr(
        ai_reasoning_service_module.feature_flags,
        "is_enabled",
        lambda flag: flag != FeatureFlag.MINOR_PROJECT_MEMORY,
    )
    inspection_service = _StubInspectionService(_inspection_report())
    reasoning_engine = _StubReasoningEngine(_reasoning_report())
    memory_engine = _StubMemoryEngine()
    service = AIReasoningService(
        engine=reasoning_engine, inspection_service=inspection_service, memory_engine=memory_engine
    )

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == []
