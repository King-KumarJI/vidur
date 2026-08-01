"""
VIDUR Core - Inspection Engine
Submodule: Code Analyzer
Purpose: AST-based static analysis of Python source files - cyclomatic
complexity, docstring coverage, and syntax validity. Produces per-file
FileMetrics plus Findings for complexity and documentation issues.
"""

import ast
from pathlib import Path
from statistics import mean
from typing import List, Tuple, Union

from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.exceptions import FileReadError
from app.core.inspection_engine.models import Finding, FileMetrics

#: Per-function cyclomatic complexity thresholds. Above WARNING a
#: WARNING finding is raised; above ERROR the finding escalates to
#: ERROR severity.
COMPLEXITY_WARNING_THRESHOLD = 10
COMPLEXITY_ERROR_THRESHOLD = 20

#: Below this fraction of documented module/function/class targets,
#: a LOW_DOCSTRING_COVERAGE finding is raised. Files with fewer than
#: MIN_TARGETS_FOR_DOCSTRING_CHECK targets are exempt, to avoid noise
#: on trivial files (e.g. a two-line __init__.py).
DOCSTRING_COVERAGE_WARNING_THRESHOLD = 0.3
MIN_TARGETS_FOR_DOCSTRING_CHECK = 3

_FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


class _ComplexityVisitor(ast.NodeVisitor):
    """Counts McCabe cyclomatic complexity decision points within a
    single function's own body, without descending into nested
    function or class definitions (those are scored independently)."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += max(len(node.values) - 1, 0)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return None


def _function_complexity(func_node: _FunctionNode) -> int:
    visitor = _ComplexityVisitor()
    for statement in func_node.body:
        visitor.visit(statement)
    return visitor.complexity


class PythonCodeAnalyzer:
    """Performs AST-based static analysis on a single Python file."""

    def analyze(self, absolute_path: str, relative_path: str) -> Tuple[FileMetrics, List[Finding]]:
        """Analyze one Python source file.

        Always returns a `FileMetrics` instance; on a syntax error the
        metrics record `has_syntax_error=True` with zeroed figures and
        a CRITICAL finding is included describing the error.
        """
        source = self._read_source(absolute_path)

        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as exc:
            metrics = FileMetrics(
                relative_path=relative_path,
                function_count=0,
                class_count=0,
                max_cyclomatic_complexity=0,
                average_cyclomatic_complexity=0.0,
                docstring_coverage=0.0,
                has_syntax_error=True,
            )
            finding = Finding(
                category=FindingCategory.SYNTAX,
                severity=Severity.CRITICAL,
                code="SYNTAX_ERROR",
                message=f"Syntax error in {relative_path}: {exc.msg}",
                file_path=relative_path,
                line=exc.lineno,
            )
            return metrics, [finding]

        function_nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        complexities = [_function_complexity(node) for node in function_nodes]
        max_complexity = max(complexities) if complexities else 1
        average_complexity = mean(complexities) if complexities else 1.0

        docstring_coverage = self._docstring_coverage(tree, function_nodes, class_nodes)

        metrics = FileMetrics(
            relative_path=relative_path,
            function_count=len(function_nodes),
            class_count=len(class_nodes),
            max_cyclomatic_complexity=max_complexity,
            average_cyclomatic_complexity=round(average_complexity, 2),
            docstring_coverage=round(docstring_coverage, 2),
            has_syntax_error=False,
        )

        findings: List[Finding] = []
        findings.extend(self._complexity_findings(relative_path, function_nodes, complexities))
        findings.extend(
            self._docstring_findings(
                relative_path, docstring_coverage, len(function_nodes) + len(class_nodes) + 1
            )
        )
        return metrics, findings

    @staticmethod
    def _read_source(absolute_path: str) -> str:
        try:
            return Path(absolute_path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise FileReadError(f"Unable to decode {absolute_path} as UTF-8: {exc}") from exc
        except OSError as exc:
            raise FileReadError(f"Unable to read {absolute_path}: {exc}") from exc

    @staticmethod
    def _docstring_coverage(
        tree: ast.Module, function_nodes: List[_FunctionNode], class_nodes: List[ast.ClassDef]
    ) -> float:
        targets = [tree, *function_nodes, *class_nodes]
        if not targets:
            return 1.0
        documented = sum(1 for node in targets if bool(ast.get_docstring(node)))
        return documented / len(targets)

    @staticmethod
    def _complexity_findings(
        relative_path: str, function_nodes: List[_FunctionNode], complexities: List[int]
    ) -> List[Finding]:
        findings: List[Finding] = []
        for node, complexity in zip(function_nodes, complexities):
            if complexity >= COMPLEXITY_ERROR_THRESHOLD:
                severity = Severity.ERROR
            elif complexity >= COMPLEXITY_WARNING_THRESHOLD:
                severity = Severity.WARNING
            else:
                continue
            findings.append(
                Finding(
                    category=FindingCategory.CODE_QUALITY,
                    severity=severity,
                    code="HIGH_COMPLEXITY",
                    message=(
                        f"Function '{node.name}' has cyclomatic complexity "
                        f"{complexity}, exceeding the threshold of "
                        f"{COMPLEXITY_WARNING_THRESHOLD}."
                    ),
                    file_path=relative_path,
                    line=node.lineno,
                )
            )
        return findings

    @staticmethod
    def _docstring_findings(
        relative_path: str, docstring_coverage: float, target_count: int
    ) -> List[Finding]:
        if target_count < MIN_TARGETS_FOR_DOCSTRING_CHECK:
            return []
        if docstring_coverage >= DOCSTRING_COVERAGE_WARNING_THRESHOLD:
            return []
        return [
            Finding(
                category=FindingCategory.CODE_QUALITY,
                severity=Severity.WARNING,
                code="LOW_DOCSTRING_COVERAGE",
                message=(
                    f"Docstring coverage is {docstring_coverage:.0%}, below the "
                    f"{DOCSTRING_COVERAGE_WARNING_THRESHOLD:.0%} threshold."
                ),
                file_path=relative_path,
                line=None,
            )
        ]
