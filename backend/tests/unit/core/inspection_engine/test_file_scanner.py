"""Unit tests for app.core.inspection_engine.file_scanner."""

import pytest

from app.core.inspection_engine.exceptions import InvalidInspectionTargetError
from app.core.inspection_engine.file_scanner import ProjectFileScanner


def test_scan_raises_for_missing_root(tmp_path):
    scanner = ProjectFileScanner()
    with pytest.raises(InvalidInspectionTargetError):
        scanner.scan(str(tmp_path / "does-not-exist"))


def test_scan_raises_when_root_is_a_file(tmp_path):
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("hello")
    scanner = ProjectFileScanner()
    with pytest.raises(InvalidInspectionTargetError):
        scanner.scan(str(file_path))


def test_scan_returns_sorted_records_with_hash_and_line_count(tmp_path):
    (tmp_path / "b.py").write_text("line1\nline2\n")
    (tmp_path / "a.py").write_text("line1")

    records = ProjectFileScanner().scan(str(tmp_path))

    assert [record.relative_path for record in records] == ["a.py", "b.py"]
    b_record = records[1]
    assert b_record.line_count == 2
    assert b_record.extension == "py"
    assert len(b_record.content_hash) == 64


def test_scan_ignores_default_ignored_directories(tmp_path):
    ignored_dir = tmp_path / "__pycache__"
    ignored_dir.mkdir()
    (ignored_dir / "cached.pyc").write_text("binary-ish")
    (tmp_path / "real.py").write_text("x = 1\n")

    records = ProjectFileScanner().scan(str(tmp_path))

    assert [record.relative_path for record in records] == ["real.py"]


def test_scan_handles_nested_directories(tmp_path):
    nested = tmp_path / "pkg" / "sub"
    nested.mkdir(parents=True)
    (nested / "deep.py").write_text("x = 1\n")

    records = ProjectFileScanner().scan(str(tmp_path))

    assert [record.relative_path for record in records] == ["pkg/sub/deep.py"]
    assert records[0].absolute_path.endswith("deep.py")


def test_scan_large_file_skips_hash_and_line_count(tmp_path):
    big_file = tmp_path / "big.bin"
    big_file.write_bytes(b"0" * 100)

    records = ProjectFileScanner(max_inspected_bytes=10).scan(str(tmp_path))

    assert records[0].content_hash == ""
    assert records[0].line_count == 0
    assert records[0].size_bytes == 100
