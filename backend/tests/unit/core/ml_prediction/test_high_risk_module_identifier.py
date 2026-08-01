"""Unit tests for app.core.ml_prediction.high_risk_module_identifier."""

from app.core.ai_reasoning.models import DependencyImpactAssessment
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import FileMetrics, Finding
from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.high_risk_module_identifier import HighRiskModuleIdentifier


def _metrics(path: str, complexity: int) -> FileMetrics:
    return FileMetrics(
        relative_path=path,
        function_count=1,
        class_count=0,
        max_cyclomatic_complexity=complexity,
        average_cyclomatic_complexity=float(complexity),
        docstring_coverage=1.0,
        has_syntax_error=False,
    )


def _finding(path: str, severity: Severity) -> Finding:
    return Finding(FindingCategory.CODE_QUALITY, severity, "CODE", "msg", path)


def test_identify_returns_empty_for_no_input():
    assert HighRiskModuleIdentifier().identify([], []) == []


def test_identify_ranks_higher_complexity_above_lower():
    metrics = [_metrics("low.py", 2), _metrics("high.py", 40)]
    scores = HighRiskModuleIdentifier().identify(metrics, [])

    assert scores[0].file_path == "high.py"
    assert scores[0].composite_risk_score > scores[1].composite_risk_score


def test_identify_includes_dependency_risk():
    metrics = [_metrics("a.py", 2)]
    assessments = [DependencyImpactAssessment("a.py", 5, 10, [], 0, 8.0)]
    scores = HighRiskModuleIdentifier().identify(metrics, [], assessments)

    assert len(scores) == 1
    assert scores[0].dependency_risk_score > 0.0


def test_identify_includes_files_with_only_findings():
    findings = [_finding("only_findings.py", Severity.CRITICAL)]
    scores = HighRiskModuleIdentifier().identify([], findings)

    assert len(scores) == 1
    assert scores[0].file_path == "only_findings.py"
    assert scores[0].finding_severity_score > 0.0


def test_identify_classifies_risk_levels():
    metrics = [_metrics("critical.py", 100), _metrics("low.py", 1)]
    assessments = [DependencyImpactAssessment("critical.py", 20, 40, [], 5, 20.0)]
    scores = {s.file_path: s for s in HighRiskModuleIdentifier().identify(metrics, [], assessments)}

    assert scores["critical.py"].risk_level == RiskLevel.CRITICAL
    assert scores["low.py"].risk_level == RiskLevel.LOW


def test_identify_sorted_descending_by_composite_score():
    metrics = [_metrics("a.py", 5), _metrics("b.py", 15), _metrics("c.py", 1)]
    scores = HighRiskModuleIdentifier().identify(metrics, [])
    composite_scores = [s.composite_risk_score for s in scores]
    assert composite_scores == sorted(composite_scores, reverse=True)
