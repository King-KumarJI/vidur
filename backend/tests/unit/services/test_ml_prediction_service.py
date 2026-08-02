"""Unit tests for app.services.ml_prediction_service.

Exercises MLPredictionService's orchestration - feature-flag gating,
optional reasoning, historical health-score/finding-count training
data lookup, prediction, and persistence - against stub
InspectionService / AIReasoningService / MLPredictionEngine /
MemoryEngine collaborators. `MLPredictionReport` itself is a large
nested dataclass with no bearing on this service's own orchestration
logic, so a trivial sentinel object stands in for it rather than
constructing a full report end-to-end.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import pytest

from app.config.feature_flags import FeatureFlag
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import InspectionReport
from app.core.ai_reasoning.models import ReasoningReport
from app.core.ml_prediction.exceptions import MLPredictionDisabledError
from app.services import ml_prediction_service as ml_prediction_service_module
from app.services.ml_prediction_service import MLPredictionService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakePredictionReport:
    """Stands in for MLPredictionReport - this service never inspects
    its fields, only passes it through."""


class _StubInspectionService:
    def __init__(self, report: InspectionReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.report


class _StubAIReasoningService:
    def __init__(self, inspection_report: InspectionReport, reasoning_report: ReasoningReport) -> None:
        self.inspection_report = inspection_report
        self.reasoning_report = reasoning_report
        self.calls: List[tuple] = []

    async def run(self, project_id, root_path):
        self.calls.append((project_id, root_path))
        return self.inspection_report, self.reasoning_report


class _StubEngine:
    def __init__(self, report) -> None:
        self.report = report
        self.calls: List[tuple] = []

    def run(
        self,
        project_id,
        inspection_report,
        reasoning_report,
        historical_health_scores,
        historical_finding_counts,
    ):
        self.calls.append(
            (
                project_id,
                inspection_report,
                reasoning_report,
                historical_health_scores,
                historical_finding_counts,
            )
        )
        return self.report


class _StubMemoryEngine:
    def __init__(self, training_data: Optional[List[Tuple[float, int]]] = None) -> None:
        self.training_data = training_data or []
        self.recorded: List = []

    async def quality_trend_training_data(self, project_id):
        return self.training_data

    async def record_ml_prediction(self, report):
        self.recorded.append(report)
        return report


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


def _enable_ml_prediction(monkeypatch, enabled: bool = True):
    monkeypatch.setattr(
        ml_prediction_service_module.feature_flags,
        "is_enabled",
        lambda flag: enabled if flag == FeatureFlag.MAJOR_ML_RISK_PREDICTION else True,
    )


def test_run_raises_when_feature_flag_disabled(monkeypatch):
    _enable_ml_prediction(monkeypatch, enabled=False)
    service = MLPredictionService(
        engine=_StubEngine(_FakePredictionReport()),
        inspection_service=_StubInspectionService(_inspection_report()),
        ai_reasoning_service=_StubAIReasoningService(_inspection_report(), _reasoning_report()),
        memory_engine=_StubMemoryEngine(),
    )

    with pytest.raises(MLPredictionDisabledError):
        asyncio.run(service.run("demo-project", "/tmp/demo"))


def test_run_uses_reasoning_by_default(monkeypatch):
    _enable_ml_prediction(monkeypatch)
    ai_reasoning_service = _StubAIReasoningService(_inspection_report(), _reasoning_report())
    inspection_service = _StubInspectionService(_inspection_report())
    engine = _StubEngine(_FakePredictionReport())
    service = MLPredictionService(
        engine=engine,
        inspection_service=inspection_service,
        ai_reasoning_service=ai_reasoning_service,
        memory_engine=_StubMemoryEngine(),
    )

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert ai_reasoning_service.calls == [("demo-project", "/tmp/demo")]
    assert inspection_service.calls == []
    assert engine.calls[0][2] is ai_reasoning_service.reasoning_report


def test_run_skips_reasoning_when_disabled_by_caller(monkeypatch):
    _enable_ml_prediction(monkeypatch)
    ai_reasoning_service = _StubAIReasoningService(_inspection_report(), _reasoning_report())
    inspection_service = _StubInspectionService(_inspection_report())
    engine = _StubEngine(_FakePredictionReport())
    service = MLPredictionService(
        engine=engine,
        inspection_service=inspection_service,
        ai_reasoning_service=ai_reasoning_service,
        memory_engine=_StubMemoryEngine(),
    )

    asyncio.run(service.run("demo-project", "/tmp/demo", include_reasoning=False))

    assert inspection_service.calls == [("demo-project", "/tmp/demo")]
    assert ai_reasoning_service.calls == []
    assert engine.calls[0][2] is None


def test_run_feeds_historical_health_scores_and_finding_counts_into_prediction(monkeypatch):
    _enable_ml_prediction(monkeypatch)
    engine = _StubEngine(_FakePredictionReport())
    memory_engine = _StubMemoryEngine(training_data=[(70.0, 3), (80.0, 1)])
    service = MLPredictionService(
        engine=engine,
        inspection_service=_StubInspectionService(_inspection_report()),
        ai_reasoning_service=_StubAIReasoningService(_inspection_report(), _reasoning_report()),
        memory_engine=memory_engine,
    )

    asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert engine.calls[0][3] == [70.0, 80.0]
    assert engine.calls[0][4] == [3, 1]


def test_run_persists_prediction_report(monkeypatch):
    _enable_ml_prediction(monkeypatch)
    engine = _StubEngine(_FakePredictionReport())
    memory_engine = _StubMemoryEngine()
    service = MLPredictionService(
        engine=engine,
        inspection_service=_StubInspectionService(_inspection_report()),
        ai_reasoning_service=_StubAIReasoningService(_inspection_report(), _reasoning_report()),
        memory_engine=memory_engine,
    )

    report = asyncio.run(service.run("demo-project", "/tmp/demo"))

    assert memory_engine.recorded == [report]
