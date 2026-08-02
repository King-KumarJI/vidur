"""Unit tests for app.core.deep_learning_vision.engine."""

from datetime import datetime, timezone

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.deep_learning_vision.engine import DeepLearningVisionEngine
from app.core.deep_learning_vision.enums import EmbeddingComparisonMethod, VisualRiskLevel
from app.core.deep_learning_vision.exceptions import (
    DeepLearningVisionDisabledError,
    InvalidComparisonInputError,
)
from app.core.deep_learning_vision.models import (
    BoundingBox,
    ImageEmbeddingComparisonResult,
    LayoutElement,
    LayoutSnapshot,
    PixelImage,
    VisualSnapshot,
)
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(
        overrides=FeatureFlagSettings(MAJOR_DEEP_LEARNING_VISUAL_INSPECTION=True)
    )


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(
        overrides=FeatureFlagSettings(MAJOR_DEEP_LEARNING_VISUAL_INSPECTION=False)
    )


def _pixel_image(fill: int) -> PixelImage:
    return PixelImage(width=2, height=2, channels=1, pixels=(fill, fill, fill, fill))


def _layout(x: int = 0) -> LayoutSnapshot:
    return LayoutSnapshot(elements=[LayoutElement("a", "div", BoundingBox(x, 0, 10, 10))])


def _snapshot(
    project_id: str = "demo-project",
    label: str = "homepage",
    image_bytes: bytes = None,
    image: PixelImage = None,
    layout: LayoutSnapshot = None,
) -> VisualSnapshot:
    return VisualSnapshot(
        project_id=project_id,
        label=label,
        captured_at=datetime.now(timezone.utc),
        image_bytes=image_bytes,
        image=image,
        layout=layout,
    )


class _StubEmbeddingComparator:
    def __init__(self, result: ImageEmbeddingComparisonResult) -> None:
        self.result = result
        self.calls = []

    def compare(self, baseline_bytes: bytes, current_bytes: bytes) -> ImageEmbeddingComparisonResult:
        self.calls.append((baseline_bytes, current_bytes))
        return self.result


def _embedding_result(risk_level: VisualRiskLevel = VisualRiskLevel.LOW) -> ImageEmbeddingComparisonResult:
    return ImageEmbeddingComparisonResult(
        method=EmbeddingComparisonMethod.CLIP,
        similarity=0.99,
        risk_level=risk_level,
        detail="stub",
    )


def test_run_raises_when_feature_flag_disabled():
    engine = DeepLearningVisionEngine(feature_flag_registry=_disabled_registry())
    baseline = _snapshot(image=_pixel_image(0))
    current = _snapshot(image=_pixel_image(0))

    with pytest.raises(DeepLearningVisionDisabledError):
        engine.run("demo-project", baseline, current)


def test_run_raises_for_invalid_project_id():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(image=_pixel_image(0))
    current = _snapshot(image=_pixel_image(0))

    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", baseline, current)


def test_run_raises_for_mismatched_baseline_project():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(project_id="project-a", image=_pixel_image(0))
    current = _snapshot(project_id="project-b", image=_pixel_image(0))

    with pytest.raises(InvalidComparisonInputError):
        engine.run("project-b", baseline, current)


def test_run_raises_when_image_presence_mismatched():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(image=_pixel_image(0))
    current = _snapshot(image=None, layout=_layout())

    with pytest.raises(InvalidComparisonInputError):
        engine.run("demo-project", baseline, current)


def test_run_raises_when_image_bytes_presence_mismatched():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(image_bytes=b"fake-png-bytes")
    current = _snapshot(image_bytes=None, layout=_layout())

    with pytest.raises(InvalidComparisonInputError):
        engine.run("demo-project", baseline, current)


def test_run_raises_when_neither_image_nor_layout_supplied():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot()
    current = _snapshot()

    with pytest.raises(InvalidComparisonInputError):
        engine.run("demo-project", baseline, current)


def test_run_produces_report_for_pixel_only():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(image=_pixel_image(0))
    current = _snapshot(image=_pixel_image(255))

    report = engine.run("demo-project", baseline, current)

    assert report.project_id == "demo-project"
    assert report.pixel_diff is not None
    assert report.layout_diff is None
    assert report.embedding_diff is None


def test_run_produces_report_for_layout_only():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(layout=_layout(x=0))
    current = _snapshot(layout=_layout(x=50))

    report = engine.run("demo-project", baseline, current)

    assert report.pixel_diff is None
    assert report.layout_diff is not None


def test_run_produces_report_for_both_image_and_layout():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(image=_pixel_image(0), layout=_layout(x=0))
    current = _snapshot(image=_pixel_image(0), layout=_layout(x=0))

    report = engine.run("demo-project", baseline, current, canvas_width=100, canvas_height=100)

    assert report.pixel_diff is not None
    assert report.layout_diff is not None


def test_run_normalizes_project_id_case():
    engine = DeepLearningVisionEngine(feature_flag_registry=_enabled_registry())
    baseline = _snapshot(project_id="demo-project", image=_pixel_image(0))
    current = _snapshot(project_id="demo-project", image=_pixel_image(0))

    report = engine.run("Demo-Project", baseline, current)

    assert report.project_id == "demo-project"


def test_run_produces_report_for_image_bytes_only_via_injected_comparator():
    stub_comparator = _StubEmbeddingComparator(_embedding_result())
    engine = DeepLearningVisionEngine(
        image_embedding_comparator=stub_comparator, feature_flag_registry=_enabled_registry()
    )
    baseline = _snapshot(image_bytes=b"baseline-bytes")
    current = _snapshot(image_bytes=b"current-bytes")

    report = engine.run("demo-project", baseline, current)

    assert report.embedding_diff is not None
    assert report.embedding_diff.risk_level == VisualRiskLevel.LOW
    assert report.pixel_diff is None
    assert stub_comparator.calls == [(b"baseline-bytes", b"current-bytes")]


def test_run_critical_embedding_diff_produces_regression_verdict():
    stub_comparator = _StubEmbeddingComparator(_embedding_result(risk_level=VisualRiskLevel.CRITICAL))
    engine = DeepLearningVisionEngine(
        image_embedding_comparator=stub_comparator, feature_flag_registry=_enabled_registry()
    )
    baseline = _snapshot(image_bytes=b"baseline-bytes")
    current = _snapshot(image_bytes=b"current-bytes")

    report = engine.run("demo-project", baseline, current)

    assert report.verdict.value == "regression"
