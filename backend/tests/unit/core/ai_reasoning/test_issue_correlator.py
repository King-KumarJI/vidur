"""Unit tests for app.core.ai_reasoning.issue_correlator."""

from app.core.ai_reasoning.enums import CorrelationBasis
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding


def _finding(code, file_path, severity=Severity.WARNING):
    return Finding(
        category=FindingCategory.CODE_QUALITY,
        severity=severity,
        code=code,
        message="test finding",
        file_path=file_path,
    )


def test_correlate_groups_findings_in_same_file():
    findings = [
        _finding("HIGH_COMPLEXITY", "a.py"),
        _finding("LOW_DOCSTRING_COVERAGE", "a.py"),
        _finding("HIGH_COMPLEXITY", "b.py"),
    ]
    groups = IssueCorrelator().correlate(findings)

    same_file_groups = [g for g in groups if g.basis is CorrelationBasis.SAME_FILE]
    assert len(same_file_groups) == 1
    assert same_file_groups[0].key == "a.py"
    assert len(same_file_groups[0].findings) == 2


def test_correlate_groups_same_code_across_files():
    findings = [
        _finding("FORBIDDEN_MARKER_TODO", "a.py"),
        _finding("FORBIDDEN_MARKER_TODO", "b.py"),
        _finding("FORBIDDEN_MARKER_TODO", "c.py"),
    ]
    groups = IssueCorrelator().correlate(findings)

    same_code_groups = [g for g in groups if g.basis is CorrelationBasis.SAME_CODE]
    assert len(same_code_groups) == 1
    assert same_code_groups[0].key == "FORBIDDEN_MARKER_TODO"
    assert len(same_code_groups[0].findings) == 3


def test_correlate_ignores_singleton_files_and_codes():
    findings = [_finding("HIGH_COMPLEXITY", "a.py")]
    groups = IssueCorrelator().correlate(findings)
    assert groups == []


def test_correlate_orders_by_severity_weight_descending():
    findings = [
        _finding("LOW_DOCSTRING_COVERAGE", "a.py", Severity.INFO),
        _finding("HIGH_COMPLEXITY", "a.py", Severity.INFO),
        _finding("SYNTAX_ERROR", "b.py", Severity.CRITICAL),
        _finding("SYNTAX_ERROR", "c.py", Severity.CRITICAL),
    ]
    groups = IssueCorrelator().correlate(findings)
    assert groups[0].key == "SYNTAX_ERROR"
