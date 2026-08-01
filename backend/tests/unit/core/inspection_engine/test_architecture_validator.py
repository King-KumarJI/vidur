"""Unit tests for app.core.inspection_engine.architecture_validator."""

from app.core.inspection_engine.architecture_validator import ArchitectureValidator
from app.core.inspection_engine.file_scanner import ProjectFileScanner


def _scan(tmp_path):
    return ProjectFileScanner().scan(str(tmp_path))


def test_validate_flags_todo_marker(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("# TODO: implement this\nx = 1\n")

    findings = ArchitectureValidator().validate(_scan(tmp_path))

    marker_findings = [f for f in findings if f.code == "FORBIDDEN_MARKER_TODO"]
    assert len(marker_findings) == 1
    assert marker_findings[0].file_path == "pkg/a.py"
    assert marker_findings[0].line == 1


def test_validate_ignores_markers_in_test_files(tmp_path):
    (tmp_path / "test_something.py").write_text("# TODO in a test file\n")

    findings = ArchitectureValidator().validate(_scan(tmp_path))

    assert findings == []


def test_validate_flags_missing_init_file(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("x = 1\n")

    findings = ArchitectureValidator().validate(_scan(tmp_path))

    missing_init = [f for f in findings if f.code == "MISSING_INIT_FILE"]
    assert len(missing_init) == 1
    assert missing_init[0].file_path == "pkg"


def test_validate_clean_package_has_no_findings(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("def add(a, b):\n    return a + b\n")

    findings = ArchitectureValidator().validate(_scan(tmp_path))

    assert findings == []
