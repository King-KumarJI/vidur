"""Unit tests for app.core.ai_reasoning.debug_assistant."""

from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding


def _finding(code, file_path):
    return Finding(
        category=FindingCategory.CODE_QUALITY,
        severity=Severity.WARNING,
        code=code,
        message="test finding",
        file_path=file_path,
    )


def test_generate_returns_known_hypothesis_for_known_code():
    findings = [_finding("HIGH_COMPLEXITY", "a.py")]
    hypotheses = DebuggingAssistant().generate(findings)
    assert len(hypotheses) == 1
    assert hypotheses[0].finding_code == "HIGH_COMPLEXITY"
    assert hypotheses[0].suggested_next_steps


def test_generate_handles_forbidden_marker_prefix():
    findings = [_finding("FORBIDDEN_MARKER_FIXME", "a.py")]
    hypotheses = DebuggingAssistant().generate(findings)
    assert "FIXME" in hypotheses[0].probable_cause


def test_generate_falls_back_for_unknown_code():
    findings = [_finding("SOME_UNKNOWN_CODE", "a.py")]
    hypotheses = DebuggingAssistant().generate(findings)
    assert hypotheses[0].finding_code == "SOME_UNKNOWN_CODE"
    assert hypotheses[0].probable_cause


def test_generate_counts_occurrences_and_related_files():
    findings = [
        _finding("HIGH_COMPLEXITY", "a.py"),
        _finding("HIGH_COMPLEXITY", "b.py"),
    ]
    hypotheses = DebuggingAssistant().generate(findings)
    assert hypotheses[0].occurrence_count == 2
    assert hypotheses[0].related_files == ["a.py", "b.py"]


def test_generate_orders_by_occurrence_count_descending():
    findings = [
        _finding("LOW_DOCSTRING_COVERAGE", "a.py"),
        _finding("HIGH_COMPLEXITY", "a.py"),
        _finding("HIGH_COMPLEXITY", "b.py"),
    ]
    hypotheses = DebuggingAssistant().generate(findings)
    assert hypotheses[0].finding_code == "HIGH_COMPLEXITY"
