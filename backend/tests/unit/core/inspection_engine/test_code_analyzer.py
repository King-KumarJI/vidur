"""Unit tests for app.core.inspection_engine.code_analyzer."""

from app.core.inspection_engine.code_analyzer import PythonCodeAnalyzer
from app.core.inspection_engine.enums import FindingCategory, Severity


def _analyze(tmp_path, source: str):
    file_path = tmp_path / "sample.py"
    file_path.write_text(source)
    return PythonCodeAnalyzer().analyze(str(file_path), "sample.py")


def test_analyze_reports_syntax_error(tmp_path):
    metrics, findings = _analyze(tmp_path, "def broken(:\n    pass\n")

    assert metrics.has_syntax_error is True
    assert metrics.function_count == 0
    assert len(findings) == 1
    assert findings[0].category is FindingCategory.SYNTAX
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].code == "SYNTAX_ERROR"


def test_analyze_simple_function_has_baseline_complexity(tmp_path):
    metrics, findings = _analyze(
        tmp_path,
        '"""Module docstring."""\n\n\ndef add(a, b):\n    """Add two numbers."""\n    return a + b\n',
    )

    assert metrics.has_syntax_error is False
    assert metrics.function_count == 1
    assert metrics.class_count == 0
    assert metrics.max_cyclomatic_complexity == 1
    assert metrics.docstring_coverage == 1.0
    assert findings == []


def test_analyze_flags_high_complexity_function(tmp_path):
    branches = "\n".join(f"    if x == {i}:\n        y += 1" for i in range(25))
    source = f'"""Module."""\n\n\ndef complex_func(x):\n    """Docs."""\n    y = 0\n{branches}\n    return y\n'
    metrics, findings = _analyze(tmp_path, source)

    assert metrics.max_cyclomatic_complexity >= 20
    complexity_findings = [f for f in findings if f.code == "HIGH_COMPLEXITY"]
    assert len(complexity_findings) == 1
    assert complexity_findings[0].severity is Severity.ERROR


def test_analyze_nested_functions_scored_independently(tmp_path):
    source = (
        '"""Module."""\n\n\n'
        "def outer():\n"
        '    """Outer."""\n'
        "    if True:\n"
        "        pass\n\n"
        "    def inner():\n"
        '        """Inner."""\n'
        "        if True:\n"
        "            pass\n"
        "        return 1\n"
        "    return inner()\n"
    )
    metrics, _ = _analyze(tmp_path, source)

    assert metrics.function_count == 2
    # Each function has exactly one decision point of its own (its
    # own `if`), so nested-function bodies must not be double counted
    # into the outer function's complexity.
    assert metrics.max_cyclomatic_complexity == 2


def test_analyze_low_docstring_coverage_flagged(tmp_path):
    source = "def a():\n    return 1\n\n\ndef b():\n    return 2\n\n\ndef c():\n    return 3\n"
    metrics, findings = _analyze(tmp_path, source)

    assert metrics.docstring_coverage < 0.3
    doc_findings = [f for f in findings if f.code == "LOW_DOCSTRING_COVERAGE"]
    assert len(doc_findings) == 1
    assert doc_findings[0].severity is Severity.WARNING
