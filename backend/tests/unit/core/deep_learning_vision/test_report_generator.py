"""Unit tests for app.core.deep_learning_vision.report_generator."""

from app.core.deep_learning_vision.enums import ComparisonVerdict, VisualRiskLevel
from app.core.deep_learning_vision.models import PixelDiffResult, VisualRegressionFinding
from app.core.deep_learning_vision.report_generator import VisualComparisonReportGenerator


def test_generate_builds_visual_comparison_report():
    pixel_diff = PixelDiffResult(
        total_pixel_count=100, changed_pixel_count=10, diff_ratio=0.1, regions=[], risk_level=VisualRiskLevel.HIGH
    )
    findings = [
        VisualRegressionFinding(category="pixel_diff", risk_level=VisualRiskLevel.HIGH, message="changed")
    ]

    report = VisualComparisonReportGenerator().generate(
        project_id="demo-project",
        baseline_label="homepage-v1",
        current_label="homepage-v2",
        pixel_diff=pixel_diff,
        layout_diff=None,
        consistency_issues=[],
        findings=findings,
        verdict=ComparisonVerdict.REGRESSION,
    )

    assert report.project_id == "demo-project"
    assert report.baseline_label == "homepage-v1"
    assert report.current_label == "homepage-v2"
    assert report.generated_at is not None
    assert report.verdict == ComparisonVerdict.REGRESSION
    assert "regression" in report.summary.lower()
    assert report.to_dict()["project_id"] == "demo-project"
    assert report.to_dict()["pixel_diff"]["risk_level"] == "high"


def test_generate_summary_reflects_match_with_no_data_sources():
    report = VisualComparisonReportGenerator().generate(
        project_id="demo-project",
        baseline_label="a",
        current_label="b",
        pixel_diff=None,
        layout_diff=None,
        consistency_issues=[],
        findings=[],
        verdict=ComparisonVerdict.MATCH,
    )

    assert "no meaningful visual differences" in report.summary.lower()
    assert "no data" in report.summary.lower()


def test_findings_by_risk_level_filters_and_sorts():
    findings = [
        VisualRegressionFinding(category="pixel_diff", risk_level=VisualRiskLevel.LOW, message="low"),
        VisualRegressionFinding(category="layout_diff", risk_level=VisualRiskLevel.CRITICAL, message="critical"),
        VisualRegressionFinding(category="layout_consistency", risk_level=VisualRiskLevel.MODERATE, message="moderate"),
    ]
    report = VisualComparisonReportGenerator().generate(
        project_id="demo-project",
        baseline_label="a",
        current_label="b",
        pixel_diff=None,
        layout_diff=None,
        consistency_issues=[],
        findings=findings,
        verdict=ComparisonVerdict.REGRESSION,
    )

    filtered = report.findings_by_risk_level(VisualRiskLevel.MODERATE)
    assert [f.message for f in filtered] == ["critical", "moderate"]
