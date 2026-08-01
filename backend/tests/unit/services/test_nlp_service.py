"""Unit tests for app.services.nlp_service.

Exercises NLPService's orchestration - running NLPEngine, then
persisting the report - against stub NLPEngine / MemoryEngine
collaborators.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

from app.config.feature_flags import FeatureFlag
from app.core.nlp.models import DocumentedIntent, ImplementedIntent, NLPReport
from app.memory.enums import MemoryRecordType
from app.memory.models import MemoryRecord
from app.services import nlp_service as nlp_service_module
from app.services.nlp_service import NLPService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubEngine:
    def __init__(self, report: NLPReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.report


class _StubMemoryEngine:
    def __init__(self) -> None:
        self.recorded: List[NLPReport] = []

    async def record_nlp(self, report: NLPReport) -> MemoryRecord:
        self.recorded.append(report)
        return MemoryRecord(
            record_id="rec-1",
            project_id=report.project_id,
            record_type=MemoryRecordType.NLP,
            recorded_at=_NOW,
            summary="stub",
            payload=report.to_dict(),
        )


def _report() -> NLPReport:
    return NLPReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=_NOW,
        documented_intent=DocumentedIntent(),
        implemented_intent=ImplementedIntent(analyzed_file_count=0),
    )


def test_run_delegates_to_engine():
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = NLPService(engine=engine, memory_engine=memory_engine)

    report = asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert engine.calls == [("demo-project", "/tmp/demo")]
    assert report is engine.report


def test_run_persists_report_when_memory_enabled():
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = NLPService(engine=engine, memory_engine=memory_engine)

    report = asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == [report]


def test_run_skips_persistence_when_memory_disabled(monkeypatch):
    monkeypatch.setattr(
        nlp_service_module.feature_flags,
        "is_enabled",
        lambda flag: flag != FeatureFlag.MINOR_PROJECT_MEMORY,
    )
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = NLPService(engine=engine, memory_engine=memory_engine)

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == []
