"""Unit tests for app.core.deep_learning_vision.visual_regression_detector."""

from app.core.deep_learning_vision.enums import (
    ComparisonVerdict,
    LayoutChangeType,
    LayoutConsistencyIssueType,
    VisualRiskLevel,
)
from app.core.deep_learning_vision.models import (
    BoundingBox,
    LayoutConsistencyIssue,
    LayoutDiffResult,
    LayoutElementChange,
    PixelDiffResult,
)
from app.core.deep_learning_vision.visual_regression_detector import VisualRegressionDetector


def test_detect_with_no_input_returns_match_and_no_findings():
    findings, verdict = VisualRegressionDetector().detect(None, None, [])

    assert findings == []
    assert verdict == ComparisonVerdict.MATCH


def test_detect_low_risk_pixel_diff_produces_no_finding():
    pixel_diff = PixelDiffResult(
        total_pixel_count=100, changed_pixel_count=1, diff_ratio=0.01, regions=[], risk_level=VisualRiskLevel.LOW
    )

    findings, verdict = VisualRegressionDetector().detect(pixel_diff, None, [])

    assert findings == []
    assert verdict == ComparisonVerdict.MATCH


def test_detect_moderate_pixel_diff_produces_minor_difference_verdict():
    pixel_diff = PixelDiffResult(
        total_pixel_count=100, changed_pixel_count=5, diff_ratio=0.05, regions=[], risk_level=VisualRiskLevel.MODERATE
    )

    findings, verdict = VisualRegressionDetector().detect(pixel_diff, None, [])

    assert len(findings) == 1
    assert findings[0].category == "pixel_diff"
    assert verdict == ComparisonVerdict.MINOR_DIFFERENCE


def test_detect_critical_pixel_diff_produces_regression_verdict():
    pixel_diff = PixelDiffResult(
        total_pixel_count=100, changed_pixel_count=30, diff_ratio=0.3, regions=[], risk_level=VisualRiskLevel.CRITICAL
    )

    findings, verdict = VisualRegressionDetector().detect(pixel_diff, None, [])

    assert verdict == ComparisonVerdict.REGRESSION


def test_detect_reports_removed_elements_individually_even_at_low_overall_risk():
    layout_diff = LayoutDiffResult(
        changes=[
            LayoutElementChange(
                element_id="nav-button",
                change_type=LayoutChangeType.REMOVED,
                baseline_bounds=BoundingBox(0, 0, 10, 10),
                detail="removed",
            )
        ],
        risk_level=VisualRiskLevel.LOW,
    )

    findings, verdict = VisualRegressionDetector().detect(None, layout_diff, [])

    removed_findings = [f for f in findings if f.element_id == "nav-button"]
    assert len(removed_findings) == 1
    assert removed_findings[0].risk_level == VisualRiskLevel.HIGH
    assert verdict == ComparisonVerdict.REGRESSION


def test_detect_aggregates_non_removal_layout_changes():
    layout_diff = LayoutDiffResult(
        changes=[
            LayoutElementChange(element_id="a", change_type=LayoutChangeType.MOVED, detail="moved"),
            LayoutElementChange(element_id="b", change_type=LayoutChangeType.MOVED, detail="moved"),
            LayoutElementChange(element_id="c", change_type=LayoutChangeType.RESIZED, detail="resized"),
        ],
        risk_level=VisualRiskLevel.HIGH,
    )

    findings, verdict = VisualRegressionDetector().detect(None, layout_diff, [])

    moved_findings = [f for f in findings if "moved" in f.message]
    assert len(moved_findings) == 1
    assert "2 element(s)" in moved_findings[0].message
    assert verdict == ComparisonVerdict.REGRESSION


def test_detect_includes_consistency_issue_findings():
    issue = LayoutConsistencyIssue(
        issue_type=LayoutConsistencyIssueType.OVERLAPPING_ELEMENTS,
        element_ids=["a", "b"],
        detail="a and b overlap",
        risk_level=VisualRiskLevel.MODERATE,
    )

    findings, verdict = VisualRegressionDetector().detect(None, None, [issue])

    assert len(findings) == 1
    assert findings[0].category == "layout_consistency"
    assert findings[0].element_id == "a"
    assert verdict == ComparisonVerdict.MINOR_DIFFERENCE
