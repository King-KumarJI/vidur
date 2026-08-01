"""Unit tests for app.core.ai_reasoning.dependency_reasoner."""

from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.file_scanner import ProjectFileScanner
from app.core.inspection_engine.models import Finding


def _scan(tmp_path):
    return ProjectFileScanner().scan(str(tmp_path))


def _finding(code, file_path, severity=Severity.WARNING):
    return Finding(
        category=FindingCategory.CODE_QUALITY,
        severity=severity,
        code=code,
        message="test finding",
        file_path=file_path,
    )


def test_assess_computes_transitive_dependents(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("x = 1\n")
    (pkg / "mid.py").write_text("from pkg import core\n")
    (pkg / "top.py").write_text("from pkg import mid\n")

    files = _scan(tmp_path)
    findings = [_finding("HIGH_COMPLEXITY", "pkg/core.py")]

    assessments = DependencyReasoner().assess(files, findings)

    assert len(assessments) == 1
    assessment = assessments[0]
    assert assessment.file_path == "pkg/core.py"
    assert assessment.direct_dependents == 1
    assert assessment.transitive_dependents == 2
    assert set(assessment.dependent_paths) == {"pkg/mid.py", "pkg/top.py"}


def test_assess_only_includes_files_with_findings(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "b.py").write_text("from pkg import a\n")

    files = _scan(tmp_path)
    assessments = DependencyReasoner().assess(files, [])
    assert assessments == []


def test_assess_risk_score_reflects_severity_and_dependents(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "leaf.py").write_text("x = 1\n")
    (pkg / "used.py").write_text("x = 1\n")
    (pkg / "importer.py").write_text("from pkg import used\n")

    files = _scan(tmp_path)
    findings = [
        _finding("HIGH_COMPLEXITY", "pkg/leaf.py", Severity.CRITICAL),
        _finding("HIGH_COMPLEXITY", "pkg/used.py", Severity.CRITICAL),
    ]
    assessments = {a.file_path: a for a in DependencyReasoner().assess(files, findings)}

    assert assessments["pkg/used.py"].risk_score > assessments["pkg/leaf.py"].risk_score


def test_assess_sorted_by_risk_score_descending(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "low.py").write_text("x = 1\n")
    (pkg / "high.py").write_text("x = 1\n")
    (pkg / "dep1.py").write_text("from pkg import high\n")
    (pkg / "dep2.py").write_text("from pkg import high\n")

    files = _scan(tmp_path)
    findings = [
        _finding("HIGH_COMPLEXITY", "pkg/low.py"),
        _finding("HIGH_COMPLEXITY", "pkg/high.py"),
    ]
    assessments = DependencyReasoner().assess(files, findings)
    assert assessments[0].file_path == "pkg/high.py"
