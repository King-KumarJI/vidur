"""Unit tests for app.core.ml_prediction.feature_extractor."""

from datetime import datetime, timezone

from app.core.ai_reasoning.models import DependencyImpactAssessment, ReasoningReport
from app.core.inspection_engine.enums import FindingCategory, InspectionStatus, Severity
from app.core.inspection_engine.models import FileMetrics, FileRecord, Finding, InspectionReport
from app.core.ml_prediction.feature_extractor import FeatureExtractor


def _file_record(path: str) -> FileRecord:
    return FileRecord(
        relative_path=path,
        absolute_path=f"/tmp/{path}",
        size_bytes=100,
        line_count=10,
        extension=".py",
        content_hash="hash",
    )


def _file_metrics(path: str, complexity: int, docstring_coverage: float) -> FileMetrics:
    return FileMetrics(
        relative_path=path,
        function_count=2,
        class_count=0,
        max_cyclomatic_complexity=complexity,
        average_cyclomatic_complexity=float(complexity),
        docstring_coverage=docstring_coverage,
        has_syntax_error=False,
    )


def _inspection_report(files, file_metrics, findings, health_score=100.0) -> InspectionReport:
    now = datetime.now(timezone.utc)
    return InspectionReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        status=InspectionStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        files=files,
        file_metrics=file_metrics,
        findings=findings,
        health_score=health_score,
    )


def test_extract_with_no_files_uses_neutral_defaults():
    report = _inspection_report(files=[], file_metrics=[], findings=[], health_score=100.0)
    vector = FeatureExtractor().extract(report)

    assert vector.file_count == 0
    assert vector.average_cyclomatic_complexity == 0.0
    assert vector.max_cyclomatic_complexity == 0
    assert vector.average_docstring_coverage == 1.0
    assert vector.finding_density == 0.0
    assert vector.average_dependency_risk == 0.0
    assert vector.max_dependency_risk == 0.0
    assert vector.health_score == 100.0


def test_extract_computes_complexity_and_docstring_stats():
    files = [_file_record("a.py"), _file_record("b.py")]
    metrics = [_file_metrics("a.py", 10, 1.0), _file_metrics("b.py", 20, 0.0)]
    report = _inspection_report(files=files, file_metrics=metrics, findings=[])

    vector = FeatureExtractor().extract(report)

    assert vector.file_count == 2
    assert vector.average_cyclomatic_complexity == 15.0
    assert vector.max_cyclomatic_complexity == 20
    assert vector.average_docstring_coverage == 0.5


def test_extract_computes_finding_and_drift_density():
    files = [_file_record("a.py")]
    findings = [
        Finding(FindingCategory.CODE_QUALITY, Severity.WARNING, "CODE", "msg", "a.py"),
        Finding(FindingCategory.DRIFT, Severity.INFO, "FILE_MODIFIED", "msg", "a.py"),
    ]
    report = _inspection_report(files=files, file_metrics=[], findings=findings)

    vector = FeatureExtractor().extract(report)

    assert vector.finding_density == 2.0
    assert vector.severity_weighted_density == Severity.WARNING.weight + Severity.INFO.weight
    assert vector.drift_churn_ratio == 1.0


def test_extract_uses_dependency_risk_from_reasoning_report():
    files = [_file_record("a.py")]
    report = _inspection_report(files=files, file_metrics=[], findings=[])
    reasoning = ReasoningReport(
        project_id="demo-project",
        root_path="/tmp/demo",
        generated_at=datetime.now(timezone.utc),
        dependency_assessments=[
            DependencyImpactAssessment("a.py", 1, 1, ["b.py"], 1, 2.0),
            DependencyImpactAssessment("b.py", 0, 0, [], 1, 6.0),
        ],
    )

    vector = FeatureExtractor().extract(report, reasoning)

    assert vector.average_dependency_risk == 4.0
    assert vector.max_dependency_risk == 6.0


def test_extract_without_reasoning_report_defaults_dependency_risk_to_zero():
    files = [_file_record("a.py")]
    report = _inspection_report(files=files, file_metrics=[], findings=[])

    vector = FeatureExtractor().extract(report, None)

    assert vector.average_dependency_risk == 0.0
    assert vector.max_dependency_risk == 0.0
