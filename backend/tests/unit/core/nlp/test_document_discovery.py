"""Unit tests for app.core.nlp.document_discovery."""

from app.core.nlp.document_discovery import DocumentDiscovery
from app.core.nlp.enums import DocumentKind


def _write_project(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "requirements.txt").write_text("fastapi==0.115.0\n")
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "main.py").write_text('"""Entry point."""\n')
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_x(): pass\n")
    (pkg / "data.json").write_text("{}")


def test_discover_classifies_readme_manifest_and_python_source(tmp_path):
    _write_project(tmp_path)
    documents = DocumentDiscovery().discover(str(tmp_path))

    kinds_by_path = {doc.relative_path: doc.kind for doc in documents}
    assert kinds_by_path["README.md"] == DocumentKind.README
    assert kinds_by_path["requirements.txt"] == DocumentKind.DEPENDENCY_MANIFEST
    assert kinds_by_path["app/main.py"] == DocumentKind.PYTHON_SOURCE


def test_discover_excludes_test_files_and_non_source(tmp_path):
    _write_project(tmp_path)
    documents = DocumentDiscovery().discover(str(tmp_path))

    relative_paths = {doc.relative_path for doc in documents}
    assert "tests/test_main.py" not in relative_paths
    assert "app/data.json" not in relative_paths


def test_discover_is_sorted_by_relative_path(tmp_path):
    _write_project(tmp_path)
    documents = DocumentDiscovery().discover(str(tmp_path))
    paths = [doc.relative_path for doc in documents]
    assert paths == sorted(paths)
