"""Unit tests for app.services.deep_learning_vision_service.

Exercises `_build_snapshot`'s request-schema -> core-dataclass
conversion directly, plus DeepLearningVisionService's orchestration -
feature-flag gating and post-run persistence - against stub
DeepLearningVisionEngine / MemoryEngine collaborators.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

from app.config.feature_flags import FeatureFlag
from app.core.deep_learning_vision.enums import ComparisonVerdict
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.schemas.deep_learning_vision_schemas import (
    BoundingBoxInput,
    LayoutElementInput,
    LayoutSnapshotInput,
    PixelImageInput,
    VisualSnapshotInput,
)
from app.services import deep_learning_vision_service as dlv_service_module
from app.services.deep_learning_vision_service import DeepLearningVisionService, _build_snapshot

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubEngine:
    def __init__(self, report: VisualComparisonReport) -> None:
        self.report = report
        self.calls: List[tuple] = []

    def run(self, project_id, baseline, current, canvas_width, canvas_height):
        self.calls.append((project_id, baseline, current, canvas_width, canvas_height))
        return self.report


class _StubMemoryEngine:
    def __init__(self) -> None:
        self.recorded: List[VisualComparisonReport] = []

    async def record_visual_comparison(self, report: VisualComparisonReport):
        self.recorded.append(report)
        return report


def _report() -> VisualComparisonReport:
    return VisualComparisonReport(
        project_id="demo-project",
        baseline_label="before",
        current_label="after",
        generated_at=_NOW,
        verdict=ComparisonVerdict.MATCH,
    )


def _snapshot_input(label: str = "before") -> VisualSnapshotInput:
    return VisualSnapshotInput(
        label=label,
        image=PixelImageInput(width=2, height=1, channels=3, pixels=[0, 0, 0, 255, 255, 255]),
        layout=LayoutSnapshotInput(
            elements=[
                LayoutElementInput(
                    element_id="btn-1",
                    tag="button",
                    bounds=BoundingBoxInput(x=0, y=0, width=10, height=5),
                    text="Submit",
                )
            ]
        ),
    )


def _enable_dlv(monkeypatch, enabled: bool = True):
    monkeypatch.setattr(
        dlv_service_module.feature_flags,
        "is_enabled",
        lambda flag: enabled if flag == FeatureFlag.MAJOR_DEEP_LEARNING_VISUAL_INSPECTION else True,
    )


def test_build_snapshot_converts_image_and_layout():
    snapshot = _build_snapshot("demo-project", _snapshot_input())

    assert snapshot.project_id == "demo-project"
    assert snapshot.label == "before"
    assert snapshot.image.width == 2
    assert snapshot.image.pixels == (0, 0, 0, 255, 255, 255)
    assert snapshot.layout.elements[0].element_id == "btn-1"
    assert snapshot.layout.elements[0].bounds.width == 10


def test_build_snapshot_defaults_captured_at_to_now_when_absent():
    snapshot = _build_snapshot("demo-project", VisualSnapshotInput(label="before"))
    assert snapshot.image is None
    assert snapshot.layout is None
    assert snapshot.captured_at is not None


def test_run_passes_converted_snapshots_to_engine(monkeypatch):
    _enable_dlv(monkeypatch)
    engine = _StubEngine(_report())
    service = DeepLearningVisionService(engine=engine, memory_engine=_StubMemoryEngine())

    asyncio.run(
        service.run(
            "demo-project", _snapshot_input("before"), _snapshot_input("after"), canvas_width=100, canvas_height=200
        )
    )

    project_id, baseline, current, canvas_width, canvas_height = engine.calls[0]
    assert project_id == "demo-project"
    assert baseline.label == "before"
    assert current.label == "after"
    assert canvas_width == 100
    assert canvas_height == 200


def test_run_persists_report_when_memory_enabled(monkeypatch):
    _enable_dlv(monkeypatch)
    engine = _StubEngine(_report())
    memory_engine = _StubMemoryEngine()
    service = DeepLearningVisionService(engine=engine, memory_engine=memory_engine)

    report = asyncio.run(service.run("demo-project", _snapshot_input("before"), _snapshot_input("after")))

    assert memory_engine.recorded == [report]
