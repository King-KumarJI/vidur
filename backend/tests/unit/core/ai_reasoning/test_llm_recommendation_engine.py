"""Unit tests for app.core.ai_reasoning.llm_recommendation_engine.

Uses a hand-written stub in place of OllamaClient (matching this
codebase's established constructor-injection test pattern), so no
network call is ever made by this test module.
"""

import json

import pytest

from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.enums import ChurnLevel, CorrelationBasis, InsightCategory, RecommendationPriority
from app.core.ai_reasoning.exceptions import OllamaResponseParsingError, OllamaUnavailableError
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.ai_reasoning.llm_recommendation_engine import (
    CHUNKING_THRESHOLD_CHARS,
    LLMRecommendationEngine,
)
from app.core.ai_reasoning.models import DependencyImpactAssessment, DriftInsight, IssueCorrelationGroup
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import FileRecord, Finding


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


class _MultiCallStubOllamaClient:
    """Records every (system_prompt, user_prompt) pair it is called
    with and returns one valid recommendation per call, so batching
    tests can assert both call count and per-call prompt content."""

    def __init__(self) -> None:
        self.calls: list = []

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        index = len(self.calls)
        self.calls.append((system_prompt, user_prompt))
        return json.dumps(
            {
                "recommendations": [
                    {
                        "priority": "low",
                        "category": "issue_correlation",
                        "title": f"Batch {index} recommendation",
                        "description": "Generated for this batch.",
                    }
                ]
            }
        )


class _ContextLimitedStubOllamaClient:
    """Simulates a local model with a limited context window: mirrors
    the live-reproduced bug (a well-formed but wrong-shaped JSON object
    - e.g. `{"reasoning": "..."}` instead of `{"recommendations":
    [...]}`- observed at ~97s against a real 112-finding inspection
    whose ~39KB prompt exceeded the model's context window) whenever a
    single call's user prompt exceeds a token-ish character budget, and
    a valid recommendations response otherwise. Used to prove batching
    is what makes large inputs succeed, not incidental to it."""

    def __init__(self, char_budget: int) -> None:
        self._char_budget = char_budget
        self.calls: list = []

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        index = len(self.calls)
        self.calls.append((system_prompt, user_prompt))
        if len(user_prompt) > self._char_budget:
            return json.dumps({"reasoning": "context overflowed; schema instructions were dropped"})
        return json.dumps(
            {
                "recommendations": [
                    {
                        "priority": "medium",
                        "category": "issue_correlation",
                        "title": f"Batch {index} finding",
                        "description": "Generated within a batch that stayed inside budget.",
                    }
                ]
            }
        )


def _padded_correlation_group(index: int) -> IssueCorrelationGroup:
    """A correlation group with enough text bulk that a modest number
    of them reliably exceeds CHUNKING_THRESHOLD_CHARS, without relying
    on a specific finding count."""
    finding = Finding(
        code="HIGH_COMPLEXITY",
        message="Function has too many independent branches to reason about safely. " * 3,
        severity=Severity.WARNING,
        category=FindingCategory.CODE_QUALITY,
        file_path=f"pkg/module_{index}/file_{index}.py",
    )
    return IssueCorrelationGroup(
        basis=CorrelationBasis.SAME_FILE,
        key=f"pkg/module_{index}/file_{index}.py",
        findings=[finding, finding],
        summary=(
            f"2 findings are concentrated in 'pkg/module_{index}/file_{index}.py'; "
            "the file likely needs focused review rather than a series of "
            "independent fixes. " * 2
        ),
    )


def _large_synthetic_inspection_groups(finding_target: int = 112) -> list:
    """Builds correlation groups from a synthetic inspection with at
    least `finding_target` findings (2 per group), reproducing the
    scale of the live-Playwright bug report (a real 112-finding
    inspection run)."""
    group_count = -(-finding_target // 2)  # ceil division: 2 findings per group
    return [_padded_correlation_group(i) for i in range(group_count)]


def test_build_splits_large_input_into_multiple_batches_and_merges_results():
    groups = _large_synthetic_inspection_groups()
    total_chars = sum(len(json.dumps(group.to_dict(), default=str)) for group in groups)
    assert total_chars > CHUNKING_THRESHOLD_CHARS, "fixture must actually exceed the chunking threshold"

    stub = _MultiCallStubOllamaClient()
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build(groups, [], [], None)

    assert len(stub.calls) > 1
    assert len(recommendations) == len(stub.calls)
    assert all(
        "NOTE: this call carries only one batch" in system_prompt for system_prompt, _ in stub.calls
    )


def test_build_does_not_batch_small_input():
    stub = _MultiCallStubOllamaClient()
    engine = LLMRecommendationEngine(ollama_client=stub)

    recommendations = engine.build([_correlation_group()], [], [], None)

    assert len(stub.calls) == 1
    assert len(recommendations) == 1
    assert "NOTE: this call carries only one batch" not in stub.calls[0][0]


def test_build_attaches_drift_insight_only_to_first_batch():
    groups = _large_synthetic_inspection_groups()
    drift = DriftInsight(churn_level=ChurnLevel.LOW, added_count=1, summary="1 file added")
    stub = _MultiCallStubOllamaClient()
    engine = LLMRecommendationEngine(ollama_client=stub)

    engine.build(groups, [], [], drift)

    assert len(stub.calls) > 1
    first_payload = json.loads(stub.calls[0][1])
    assert first_payload["drift_insight"] is not None
    for _, user_prompt in stub.calls[1:]:
        payload = json.loads(user_prompt)
        assert payload["drift_insight"] is None


def test_build_succeeds_at_scale_where_a_single_unbatched_call_would_fail():
    """Regression test for the live-Playwright-reported bug: a real
    112-finding inspection produced a genuinely well-formed (so it
    never raised a JSON parse error) but wrong-shaped LLM response,
    because the request exceeded the model's context window. Proves
    two things at once: (1) with batching active (the fix), a
    100+-finding scenario succeeds end-to-end with genuine LLM-parsed
    recommendations, not the rule-based fallback; and (2) the same
    fixture, with batching artificially disabled to reproduce the
    pre-fix single-call behavior, does raise OllamaResponseParsingError
    - confirming batching (not something else) is what fixes it.
    """
    findings = []
    files = []
    codes = [
        ("HIGH_COMPLEXITY", FindingCategory.CODE_QUALITY, Severity.WARNING),
        ("LOW_DOCSTRING_COVERAGE", FindingCategory.CODE_QUALITY, Severity.INFO),
        ("SYNTAX_ERROR", FindingCategory.SYNTAX, Severity.CRITICAL),
        ("CIRCULAR_DEPENDENCY", FindingCategory.DEPENDENCY, Severity.ERROR),
        ("MISSING_INIT_FILE", FindingCategory.ARCHITECTURE, Severity.WARNING),
        ("FILE_MODIFIED", FindingCategory.DRIFT, Severity.INFO),
    ]
    for i in range(112):
        path = f"app/module_{i % 20}/file_{i}.py"
        code, category, severity = codes[i % len(codes)]
        findings.append(
            Finding(
                category=category,
                severity=severity,
                code=code,
                message=f"Synthetic finding #{i} for {path}: {code} detected.",
                file_path=path,
                line=(i % 200) + 1,
            )
        )
    for i in range(20):
        rel = f"app/module_{i}/file_{i}.py"
        files.append(
            FileRecord(
                relative_path=rel,
                absolute_path=f"/nonexistent/{rel}",
                size_bytes=1000,
                line_count=50,
                extension="py",
                content_hash="deadbeef",
            )
        )

    correlation_groups = IssueCorrelator().correlate(findings)
    dependency_assessments = DependencyReasoner().assess(files, findings)
    debugging_hypotheses = DebuggingAssistant().generate(findings)
    drift_insight = DriftReasoner().reason(findings, dependency_assessments, len(files))

    # (1) With batching active (real CHUNKING_THRESHOLD_CHARS), the
    # scaled-up scenario succeeds via genuine LLM-parsed recommendations.
    batching_stub = _ContextLimitedStubOllamaClient(char_budget=CHUNKING_THRESHOLD_CHARS + 500)
    engine = LLMRecommendationEngine(ollama_client=batching_stub)
    recommendations = engine.build(
        correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight
    )

    assert len(batching_stub.calls) > 1
    assert len(recommendations) == len(batching_stub.calls)
    assert all(rec.title.startswith("Batch ") for rec in recommendations)

    # (2) The identical fixture, sent as a single unbatched call
    # (reproducing pre-fix behavior), hits the simulated context limit
    # and fails to parse - proving batching is the operative fix.
    unbatched_stub = _ContextLimitedStubOllamaClient(char_budget=CHUNKING_THRESHOLD_CHARS + 500)
    unbatched_content = unbatched_stub.chat_json(
        "system",
        json.dumps(
            {
                "correlation_groups": [g.to_dict() for g in correlation_groups],
                "dependency_assessments": [a.to_dict() for a in dependency_assessments],
                "debugging_hypotheses": [h.to_dict() for h in debugging_hypotheses],
                "drift_insight": drift_insight.to_dict() if drift_insight else None,
            },
            default=str,
        ),
    )
    with pytest.raises(OllamaResponseParsingError):
        LLMRecommendationEngine._parse(unbatched_content)
