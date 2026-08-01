"""
VIDUR Core - Inspection Engine
Submodule: Dependency Analyzer
Purpose: Build an internal import graph across a project's own Python
files (ignoring stdlib/third-party imports) and detect circular
dependencies between them.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import FileRecord, Finding


def _module_name_for(relative_path: str) -> str:
    """Derive the dotted module name a file would be imported as,
    from its slash-separated relative path."""
    dotted = relative_path[:-3] if relative_path.endswith(".py") else relative_path
    dotted = dotted.replace("/", ".")
    if dotted.endswith(".__init__"):
        dotted = dotted[: -len(".__init__")]
    return dotted


def _is_package_init(relative_path: str) -> bool:
    return Path(relative_path).name == "__init__.py"


def _resolve_relative_import(
    importer_module: str, importer_is_package: bool, level: int, module: Optional[str]
) -> str:
    """Resolve a `from . import x` / `from ..pkg import y` style import
    to an absolute dotted module name, using the same algorithm as
    `importlib._bootstrap._resolve_name`."""
    base_bits = importer_module.split(".")
    if not importer_is_package:
        base_bits = base_bits[:-1]
    if level > 1:
        base_bits = base_bits[: -(level - 1)] if len(base_bits) >= (level - 1) else []
    if module:
        base_bits = [*base_bits, *module.split(".")]
    return ".".join(bit for bit in base_bits if bit)


class DependencyAnalyzer:
    """Builds an internal (project-own-files-only) import graph and
    detects circular import chains within it."""

    def build_graph(self, files: List[FileRecord]) -> Dict[str, Set[str]]:
        """Return an adjacency map of `relative_path -> {relative_path, ...}`
        representing internal import edges (importer -> imported)."""
        python_files = [record for record in files if record.extension == "py"]
        module_to_path: Dict[str, str] = {
            _module_name_for(record.relative_path): record.relative_path
            for record in python_files
        }

        graph: Dict[str, Set[str]] = {record.relative_path: set() for record in python_files}
        for record in python_files:
            imported_modules = self._imported_module_names(record)
            for module_name in imported_modules:
                target_path = self._resolve_to_internal_path(module_name, module_to_path)
                if target_path is not None and target_path != record.relative_path:
                    graph[record.relative_path].add(target_path)

        return graph

    def find_findings(self, files: List[FileRecord]) -> List[Finding]:
        """Build the internal dependency graph and return one Finding
        per detected circular dependency chain."""
        graph = self.build_graph(files)
        cycles = self._detect_cycles(graph)

        findings: List[Finding] = []
        for cycle in cycles:
            chain = " -> ".join(cycle + [cycle[0]])
            findings.append(
                Finding(
                    category=FindingCategory.DEPENDENCY,
                    severity=Severity.ERROR,
                    code="CIRCULAR_DEPENDENCY",
                    message=f"Circular import dependency detected: {chain}",
                    file_path=cycle[0],
                    line=None,
                )
            )
        return findings

    @staticmethod
    def _imported_module_names(record: FileRecord) -> List[str]:
        try:
            source = Path(record.absolute_path).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=record.relative_path)
        except (OSError, SyntaxError, UnicodeDecodeError):
            return []

        importer_module = _module_name_for(record.relative_path)
        importer_is_package = _is_package_init(record.relative_path)

        names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    base = _resolve_relative_import(
                        importer_module, importer_is_package, node.level, node.module
                    )
                else:
                    base = node.module

                if base:
                    names.append(base)
                    # `from X import Y` may import submodule X.Y (as
                    # opposed to an attribute defined in X itself), so
                    # both candidates are recorded and resolved later.
                    names.extend(f"{base}.{alias.name}" for alias in node.names)
        return names

    @staticmethod
    def _resolve_to_internal_path(
        module_name: str, module_to_path: Dict[str, str]
    ) -> Optional[str]:
        if module_name in module_to_path:
            return module_to_path[module_name]
        # An import may reference a specific attribute/submodule of an
        # internal package (e.g. `import app.core.foo` where only
        # `app.core.foo` itself, not a deeper attribute, is a file).
        # Walk up the dotted path to find the longest matching prefix.
        bits = module_name.split(".")
        while len(bits) > 1:
            bits.pop()
            candidate = ".".join(bits)
            if candidate in module_to_path:
                return module_to_path[candidate]
        return None

    @staticmethod
    def _detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node: WHITE for node in graph}
        parent: Dict[str, Optional[str]] = {node: None for node in graph}
        found_cycles: List[List[str]] = []
        seen_cycle_sets: Set[frozenset] = set()

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in sorted(graph.get(node, set())):
                if neighbor not in color:
                    continue
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor)
                elif color[neighbor] == GRAY:
                    cycle = _reconstruct_cycle(parent, node, neighbor)
                    cycle_set = frozenset(cycle)
                    if cycle_set not in seen_cycle_sets:
                        seen_cycle_sets.add(cycle_set)
                        found_cycles.append(cycle)
            color[node] = BLACK

        for start_node in sorted(graph):
            if color[start_node] == WHITE:
                dfs(start_node)

        return found_cycles


def _reconstruct_cycle(parent: Dict[str, Optional[str]], from_node: str, to_node: str) -> List[str]:
    path = [from_node]
    current = from_node
    while current != to_node and parent[current] is not None:
        current = parent[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path
