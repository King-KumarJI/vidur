"""Unit tests for app.core.ai_reasoning.llm_recommendation_engine.

Uses a hand-written stub in place of OllamaClient (matching this
codebase's established constructor-injection test pattern), so no
network call is ever made by this test module.
"""

import json

import pytest

from app.core.ai_reasoning.enums import ChurnLevel, CorrelationBasis, InsightCategory, RecommendationPriority
from app.core.ai_reasoning.exceptions import OllamaResponseParsingError, OllamaUnavailableError
from app.core.ai_reasoning.llm_recommendation_engine import LLMRecommendationEngine
from app.core.ai_reasoning.models import DependencyImpactAssessment, DriftInsight, IssueCorrelationGroup
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding


class _StubOllamaClient:
    def __init__(self, content: str = "", error: Exception = None):
        self._content = content
        self._error = error
        self.last_system_prompt = None
        self.last_user_prompt = None

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self._error is not None:
            raise self._error
        return self._content


def _correlation_group() -> IssueCorrelationGroup:
    finding = Finding(
        code="HIGH_COMPLEXITY",
        message="too complex",
        severity=Severity.WARNING,
        category=FindingCategory.CODE_QUALITY,
        file_path="pkg/a.py",
    )
    return IssueCorrelationGroup(
        basis=CorrelationBasis.SAME_FILE,
        key="pkg/a.py",
        findings=[finding, finding],
        summary="2 findings concentrated in pkg/a.py",
    )


def test_build_returns_empty_list_without_calling_ollama_when_nothing_to_reason_about():
    stub = _StubOllamaClient(error=AssertionError("should not be called"))
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build([], [], [], None)

    assert recommendations == []


def test_build_parses_valid_object_response():
    content = json.dumps(
        {
            "recommendations": [
                {
                    "priority": "high",
                    "category": "issue_correlation",
                    "title": "Review pkg/a.py",
                    "description": "Multiple findings concentrated here.",
                    "supporting_finding_codes": ["HIGH_COMPLEXITY"],
                    "affected_files": ["pkg/a.py"],
                }
            ]
        }
    )
    stub = _StubOllamaClient(content=content)
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build([_correlation_group()], [], [], None)

    assert len(recommendations) == 1
    rec = recommendations[0]
    assert rec.priority is RecommendationPriority.HIGH
    assert rec.category is InsightCategory.ISSUE_CORRELATION
    assert rec.title == "Review pkg/a.py"
    assert rec.supporting_finding_codes == ["HIGH_COMPLEXITY"]
    assert rec.affected_files == ["pkg/a.py"]


def test_build_parses_bare_list_response():
    content = json.dumps(
        [
            {
                "priority": "low",
                "category": "drift_significance",
                "title": "Review drift",
                "description": "Some files changed.",
            }
        ]
    )
    stub = _StubOllamaClient(content=content)
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build(
        [],
        [],
        [],
        DriftInsight(churn_level=ChurnLevel.LOW, added_count=1, summary="1 file added"),
    )

    assert len(recommendations) == 1
    assert recommendations[0].supporting_finding_codes == []
    assert recommendations[0].affected_files == []


def test_build_filters_invalid_items_but_keeps_valid_ones():
    content = json.dumps(
        {
            "recommendations": [
                {"priority": "bogus", "category": "issue_correlation", "title": "x", "description": "y"},
                {"priority": "low", "category": "bogus", "title": "x", "description": "y"},
                {"priority": "low", "category": "issue_correlation", "title": "", "description": "y"},
                "not-an-object",
                {
                    "priority": "medium",
                    "category": "dependency_impact",
                    "title": "Valid one",
                    "description": "kept",
                },
            ]
        }
    )
    stub = _StubOllamaClient(content=content)
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build([_correlation_group()], [], [], None)

    assert len(recommendations) == 1
    assert recommendations[0].title == "Valid one"


def test_build_returns_empty_list_when_ollama_reports_nothing_actionable():
    content = json.dumps({"recommendations": []})
    stub = _StubOllamaClient(content=content)
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build([_correlation_group()], [], [], None)

    assert recommendations == []


def test_build_raises_parsing_error_when_all_items_invalid():
    content = json.dumps({"recommendations": [{"priority": "bogus", "category": "bogus"}]})
    stub = _StubOllamaClient(content=content)
    engine = LLMRecommendationEngine(ollama_client=stub)

    with pytest.raises(OllamaResponseParsingError):
        engine.build([_correlation_group()], [], [], None)


def test_build_raises_parsing_error_on_invalid_json():
    stub = _StubOllamaClient(content="not json at all")
    engine = LLMRecommendationEngine(ollama_client=stub)

    with pytest.raises(OllamaResponseParsingError):
        engine.build([_correlation_group()], [], [], None)


def test_build_raises_parsing_error_on_missing_recommendations_key():
    stub = _StubOllamaClient(content=json.dumps({"unexpected": []}))
    engine = LLMRecommendationEngine(ollama_client=stub)

    with pytest.raises(OllamaResponseParsingError):
        engine.build([_correlation_group()], [], [], None)


def test_build_propagates_ollama_unavailable_error():
    stub = _StubOllamaClient(error=OllamaUnavailableError("down"))
    engine = LLMRecommendationEngine(ollama_client=stub)

    with pytest.raises(OllamaUnavailableError):
        engine.build([_correlation_group()], [], [], None)


def test_build_sends_reasoning_stage_data_as_user_prompt():
    stub = _StubOllamaClient(content=json.dumps({"recommendations": []}))
    engine = LLMRecommendationEngine(ollama_client=stub)
    assessment = DependencyImpactAssessment(
        file_path="pkg/a.py", direct_dependents=1, transitive_dependents=1, risk_score=2.5
    )

    engine.build([], [assessment], [], None)

    payload = json.loads(stub.last_user_prompt)
    assert payload["dependency_assessments"][0]["file_path"] == "pkg/a.py"
