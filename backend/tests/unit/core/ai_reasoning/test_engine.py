"""Unit tests for app.core.ai_reasoning.engine.

Every test constructs `AIReasoningEngine` with a stub
`llm_recommendation_engine` so the standard suite never depends on a
live Ollama instance being reachable, matching this module's
`test_llm_recommendation_engine.py` and `test_ollama_client.py` (which
mock the Ollama HTTP boundary directly).
"""

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.ai_reasoning.engine import AIReasoningEngine
from app.core.ai_reasoning.enums import InsightCategory, RecommendationPriority
from app.core.ai_reasoning.exceptions import (
    InvalidReasoningInputError,
    OllamaResponseParsingError,
    OllamaUnavailableError,
    ReasoningDisabledError,
)
from app.core.ai_reasoning.models import Recommendation
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.models import InspectionReport
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=False))


class _StubLLMRecommendationEngine:
    """Always raises OllamaUnavailableError, forcing the deterministic
    rule-based fallback path so pre-existing assertions about
    `reasoning.recommendations` remain stable regardless of whether a
    real Ollama instance happens to be running on the host machine."""

    def build(self, correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight):
        raise OllamaUnavailableError("stubbed: Ollama not available in this test")


class _StubSucceedingLLMRecommendationEngine:
    def __init__(self, recommendations):
        self._recommendations = recommendations
        self.called = False

    def build(self, correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight):
        self.called = True
        return self._recommendations


class _StubFailingLLMRecommendationEngine:
    def __init__(self, error: Exception):
        self._error = error

    def build(self, correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight):
        raise self._error


def _fallback_engine(**kwargs) -> AIReasoningEngine:
    kwargs.setdefault("llm_recommendation_engine", _StubLLMRecommendationEngine())
    kwargs.setdefault("feature_flag_registry", _enabled_registry())
    return AIReasoningEngine(**kwargs)


def _inspection_report(tmp_path, project_id: str = "demo-project") -> InspectionReport:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("# TODO: cleanup\nx = 1\n")
    (pkg / "b.py").write_text("from pkg import a\n")
    return InspectionEngine().run(project_id, str(tmp_path))


def test_run_raises_when_feature_flag_disabled(tmp_path):
    report = _inspection_report(tmp_path)
    engine = _fallback_engine(feature_flag_registry=_disabled_registry())
    with pytest.raises(ReasoningDisabledError):
        engine.run("demo-project", report)


def test_run_raises_for_invalid_project_id(tmp_path):
    report = _inspection_report(tmp_path)
    engine = _fallback_engine()
    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", report)


def test_run_raises_for_mismatched_project(tmp_path):
    report = _inspection_report(tmp_path, project_id="project-a")
    engine = _fallback_engine()
    with pytest.raises(InvalidReasoningInputError):
        engine.run("project-b", report)


def test_run_produces_reasoning_report(tmp_path):
    report = _inspection_report(tmp_path)
    engine = _fallback_engine()

    reasoning = engine.run("demo-project", report)

    assert reasoning.project_id == "demo-project"
    assert reasoning.recommendations
    codes = {hypothesis.finding_code for hypothesis in reasoning.debugging_hypotheses}
    assert "FORBIDDEN_MARKER_TODO" in codes


def test_run_normalizes_project_id_case(tmp_path):
    report = _inspection_report(tmp_path)
    engine = _fallback_engine()

    reasoning = engine.run("Demo-Project", report)

    assert reasoning.project_id == "demo-project"


def test_run_falls_back_to_rule_based_recommendations_when_ollama_unavailable(tmp_path):
    """The core contract from the CLAUDE.md AI Reasoning upgrade: if
    Ollama is unreachable, the run must still succeed using the
    pre-existing rule-based RecommendationEngine, not crash."""
    report = _inspection_report(tmp_path)
    engine = _fallback_engine()

    reasoning = engine.run("demo-project", report)

    assert reasoning.recommendations


def test_run_falls_back_when_llm_response_cannot_be_parsed(tmp_path):
    report = _inspection_report(tmp_path)
    engine = AIReasoningEngine(
        llm_recommendation_engine=_StubFailingLLMRecommendationEngine(
            OllamaResponseParsingError("malformed response")
        ),
        feature_flag_registry=_enabled_registry(),
    )

    reasoning = engine.run("demo-project", report)

    assert reasoning.recommendations


def test_run_uses_llm_recommendations_when_available(tmp_path):
    """When the LLM path succeeds, its recommendations are used
    verbatim rather than being replaced by the rule-based engine."""
    report = _inspection_report(tmp_path)
    llm_recommendation = Recommendation(
        priority=RecommendationPriority.CRITICAL,
        category=InsightCategory.DEBUGGING_ASSISTANCE,
        title="LLM-authored recommendation",
        description="Produced by the local model, not the rule-based engine.",
    )
    stub = _StubSucceedingLLMRecommendationEngine([llm_recommendation])
    engine = AIReasoningEngine(
        llm_recommendation_engine=stub,
        feature_flag_registry=_enabled_registry(),
    )

    reasoning = engine.run("demo-project", report)

    assert stub.called
    assert reasoning.recommendations == [llm_recommendation]
