"""Unit tests for app.core.deep_learning_vision.report_generator."""

from app.core.deep_learning_vision.enums import ComparisonVerdict, EmbeddingComparisonMethod, VisualRiskLevel
from app.core.deep_learning_vision.models import (
    ImageEmbeddingComparisonResult,
    PixelDiffResult,
    VisualRegressionFinding,
)
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
        embedding_diff=None,
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
        embedding_diff=None,
        pixel_diff=None,
        layout_diff=None,
        consistency_issues=[],
        findings=[],
        verdict=ComparisonVerdict.MATCH,
    )

    assert "no meaningful visual differences" in report.summary.lower()
    assert "no data" in report.summary.lower()


def test_generate_summary_reflects_embedding_data_source():
    embedding_diff = ImageEmbeddingComparisonResult(
        method=EmbeddingComparisonMethod.CLIP,
        similarity=0.5,
        risk_level=VisualRiskLevel.CRITICAL,
        detail="OpenCLIP cosine similarity: 0.5000.",
    )
    findings = [
        VisualRegressionFinding(category="embedding_diff", risk_level=VisualRiskLevel.CRITICAL, message="changed")
    ]

    report = VisualComparisonReportGenerator().generate(
        project_id="demo-project",
        baseline_label="a",
        current_label="b",
        embedding_diff=embedding_diff,
        pixel_diff=None,
        layout_diff=None,
        consistency_issues=[],
        findings=findings,
        verdict=ComparisonVerdict.REGRESSION,
    )

    assert "embedding data" in report.summary.lower()
    assert report.embedding_diff is embedding_diff
    assert report.to_dict()["embedding_diff"]["method"] == "clip"
    assert report.to_dict()["embedding_diff"]["similarity"] == 0.5


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
        embedding_diff=None,
        pixel_diff=None,
        layout_diff=None,
        consistency_issues=[],
        findings=findings,
        verdict=ComparisonVerdict.REGRESSION,
    )

    filtered = report.findings_by_risk_level(VisualRiskLevel.MODERATE)
    assert [f.message for f in filtered] == ["critical", "moderate"]
