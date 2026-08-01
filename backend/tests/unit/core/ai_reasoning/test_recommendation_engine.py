"""Unit tests for app.core.ai_reasoning.recommendation_engine."""

from app.core.ai_reasoning.enums import (
    ChurnLevel,
    CorrelationBasis,
    InsightCategory,
    RecommendationPriority,
)
from app.core.ai_reasoning.models import (
    DebuggingHypothesis,
    DependencyImpactAssessment,
    DriftInsight,
    IssueCorrelationGroup,
)
from app.core.ai_reasoning.recommendation_engine import RecommendationEngine
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding


def _finding(code, file_path, severity=Severity.WARNING):
    return Finding(
        category=FindingCategory.CODE_QUALITY,
        severity=severity,
        code=code,
        message="test",
        file_path=file_path,
    )


def test_build_creates_recommendation_per_correlation_group():
    group = IssueCorrelationGroup(
        basis=CorrelationBasis.SAME_FILE,
        key="a.py",
        findings=[
            _finding("HIGH_COMPLEXITY", "a.py"),
            _finding("LOW_DOCSTRING_COVERAGE", "a.py"),
        ],
        summary="test summary",
    )
    recs = RecommendationEngine().build([group], [], [], None)
    assert len(recs) == 1
    assert recs[0].category is InsightCategory.ISSUE_CORRELATION


def test_build_skips_low_risk_dependency_assessments():
    assessment = DependencyImpactAssessment(
        file_path="a.py",
        direct_dependents=0,
        transitive_dependents=0,
        dependent_paths=[],
        finding_count=1,
        risk_score=0.5,
    )
    recs = RecommendationEngine().build([], [assessment], [], None)
    assert recs == []


def test_build_includes_high_risk_dependency_assessment():
    assessment = DependencyImpactAssessment(
        file_path="a.py",
        direct_dependents=2,
        transitive_dependents=2,
        dependent_paths=["b.py", "c.py"],
        finding_count=1,
        risk_score=5.0,
    )
    recs = RecommendationEngine().build([], [assessment], [], None)
    assert len(recs) == 1
    assert recs[0].category is InsightCategory.DEPENDENCY_IMPACT


def test_build_skips_single_occurrence_hypotheses():
    hypothesis = DebuggingHypothesis(
        finding_code="HIGH_COMPLEXITY",
        probable_cause="x",
        explanation="y",
        suggested_next_steps=["z"],
        occurrence_count=1,
        related_files=["a.py"],
    )
    recs = RecommendationEngine().build([], [], [hypothesis], None)
    assert recs == []


def test_build_includes_recurring_hypotheses():
    hypothesis = DebuggingHypothesis(
        finding_code="HIGH_COMPLEXITY",
        probable_cause="x",
        explanation="y",
        suggested_next_steps=["z"],
        occurrence_count=3,
        related_files=["a.py", "b.py"],
    )
    recs = RecommendationEngine().build([], [], [hypothesis], None)
    assert len(recs) == 1
    assert recs[0].category is InsightCategory.DEBUGGING_ASSISTANCE


def test_build_skips_low_churn_drift_without_high_impact():
    drift = DriftInsight(churn_level=ChurnLevel.LOW, added_count=1, modified_count=0, removed_count=0)
    recs = RecommendationEngine().build([], [], [], drift)
    assert recs == []


def test_build_includes_high_churn_drift():
    drift = DriftInsight(churn_level=ChurnLevel.HIGH, added_count=5, modified_count=0, removed_count=0)
    recs = RecommendationEngine().build([], [], [], drift)
    assert len(recs) == 1
    assert recs[0].category is InsightCategory.DRIFT_SIGNIFICANCE


def test_build_sorts_by_priority_descending():
    low_group = IssueCorrelationGroup(
        basis=CorrelationBasis.SAME_FILE,
        key="a.py",
        findings=[_finding("X", "a.py", Severity.INFO), _finding("Y", "a.py", Severity.INFO)],
    )
    critical_drift = DriftInsight(
        churn_level=ChurnLevel.HIGH,
        added_count=1,
        modified_count=0,
        removed_count=0,
        high_impact_files=["z.py"],
    )
    recs = RecommendationEngine().build([low_group], [], [], critical_drift)
    assert recs[0].priority is RecommendationPriority.CRITICAL
