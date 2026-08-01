"""Unit tests for app.core.inspection_engine.health_score."""

from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.health_score import HealthScoreCalculator
from app.core.inspection_engine.models import Finding


def _finding(severity: Severity) -> Finding:
    return Finding(
        category=FindingCategory.CODE_QUALITY,
        severity=severity,
        code="TEST",
        message="test finding",
    )


def test_calculate_returns_max_score_with_no_findings():
    assert HealthScoreCalculator().calculate([], total_files=10) == 100.0


def test_calculate_reduces_score_with_findings():
    findings = [_finding(Severity.WARNING)]
    score = HealthScoreCalculator().calculate(findings, total_files=1)
    assert 0.0 <= score < 100.0


def test_calculate_more_severe_findings_reduce_score_more():
    warning_score = HealthScoreCalculator().calculate([_finding(Severity.WARNING)], total_files=1)
    critical_score = HealthScoreCalculator().calculate([_finding(Severity.CRITICAL)], total_files=1)
    assert critical_score < warning_score


def test_calculate_score_never_below_zero():
    findings = [_finding(Severity.CRITICAL) for _ in range(50)]
    score = HealthScoreCalculator().calculate(findings, total_files=1)
    assert score == 0.0


def test_calculate_normalizes_by_file_count():
    findings = [_finding(Severity.WARNING)]
    small_project_score = HealthScoreCalculator().calculate(findings, total_files=1)
    large_project_score = HealthScoreCalculator().calculate(findings, total_files=1000)
    assert large_project_score > small_project_score


def test_count_by_severity_includes_zero_counts():
    counts = HealthScoreCalculator.count_by_severity([_finding(Severity.ERROR)])
    assert counts == {"info": 0, "warning": 0, "error": 1, "critical": 0}
