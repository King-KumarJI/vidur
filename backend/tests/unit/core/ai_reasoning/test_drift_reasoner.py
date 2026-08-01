"""Unit tests for app.core.ai_reasoning.drift_reasoner."""

from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.enums import ChurnLevel
from app.core.ai_reasoning.models import DependencyImpactAssessment
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding


def _drift_finding(code, file_path, severity=Severity.INFO):
    return Finding(
        category=FindingCategory.DRIFT,
        severity=severity,
        code=code,
        message="test drift",
        file_path=file_path,
    )


def test_reason_returns_none_without_drift_findings():
    assert DriftReasoner().reason([], [], total_files=10) is None


def test_reason_classifies_low_churn():
    findings = [_drift_finding("FILE_MODIFIED", "a.py")]
    insight = DriftReasoner().reason(findings, [], total_files=100)
    assert insight.churn_level is ChurnLevel.LOW
    assert insight.modified_count == 1


def test_reason_classifies_high_churn():
    findings = [_drift_finding("FILE_ADDED", f"f{i}.py") for i in range(5)]
    insight = DriftReasoner().reason(findings, [], total_files=10)
    assert insight.churn_level is ChurnLevel.HIGH


def test_reason_flags_removed_files_as_high_impact():
    findings = [_drift_finding("FILE_REMOVED", "a.py", Severity.WARNING)]
    insight = DriftReasoner().reason(findings, [], total_files=10)
    assert insight.high_impact_files == ["a.py"]


def test_reason_flags_high_risk_modified_files():
    findings = [_drift_finding("FILE_MODIFIED", "a.py")]
    assessments = [
        DependencyImpactAssessment(
            file_path="a.py",
            direct_dependents=3,
            transitive_dependents=3,
            dependent_paths=["b.py", "c.py", "d.py"],
            finding_count=1,
            risk_score=3.0,
        )
    ]
    insight = DriftReasoner().reason(findings, assessments, total_files=10)
    assert insight.high_impact_files == ["a.py"]


def test_reason_does_not_flag_low_risk_modified_files():
    findings = [_drift_finding("FILE_MODIFIED", "a.py")]
    assessments = [
        DependencyImpactAssessment(
            file_path="a.py",
            direct_dependents=0,
            transitive_dependents=0,
            dependent_paths=[],
            finding_count=1,
            risk_score=0.5,
        )
    ]
    insight = DriftReasoner().reason(findings, assessments, total_files=10)
    assert insight.high_impact_files == []
