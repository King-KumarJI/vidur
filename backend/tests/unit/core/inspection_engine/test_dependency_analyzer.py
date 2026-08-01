"""Unit tests for app.core.inspection_engine.dependency_analyzer."""

from app.core.inspection_engine.dependency_analyzer import DependencyAnalyzer
from app.core.inspection_engine.file_scanner import ProjectFileScanner


def _scan(tmp_path):
    return ProjectFileScanner().scan(str(tmp_path))


def test_build_graph_resolves_absolute_internal_imports(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from pkg import b\n")
    (pkg / "b.py").write_text("import os\n")

    graph = DependencyAnalyzer().build_graph(_scan(tmp_path))

    assert "pkg/b.py" in graph["pkg/a.py"]
    assert graph["pkg/b.py"] == set()


def test_build_graph_ignores_external_imports(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("import numpy\nimport os.path\n")

    graph = DependencyAnalyzer().build_graph(_scan(tmp_path))

    assert graph["pkg/a.py"] == set()


def test_build_graph_resolves_relative_imports(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from . import b\n")
    (pkg / "b.py").write_text("x = 1\n")

    graph = DependencyAnalyzer().build_graph(_scan(tmp_path))

    assert "pkg/b.py" in graph["pkg/a.py"]


def test_find_findings_detects_circular_dependency(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from pkg import b\n")
    (pkg / "b.py").write_text("from pkg import c\n")
    (pkg / "c.py").write_text("from pkg import a\n")

    findings = DependencyAnalyzer().find_findings(_scan(tmp_path))

    assert len(findings) == 1
    assert findings[0].code == "CIRCULAR_DEPENDENCY"
    assert "pkg/a.py" in findings[0].message
    assert "pkg/b.py" in findings[0].message
    assert "pkg/c.py" in findings[0].message


def test_find_findings_no_cycle_for_acyclic_graph(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from pkg import b\n")
    (pkg / "b.py").write_text("x = 1\n")

    findings = DependencyAnalyzer().find_findings(_scan(tmp_path))

    assert findings == []
