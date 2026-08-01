"""Unit tests for app.core.inspection_engine.drift_detector."""

from datetime import datetime, timezone

from app.core.inspection_engine.drift_detector import DriftDetector
from app.core.inspection_engine.models import FileRecord, InspectionSnapshot


def _record(path: str, content_hash: str = "hash1") -> FileRecord:
    return FileRecord(
        relative_path=path,
        absolute_path=f"/root/{path}",
        size_bytes=10,
        line_count=1,
        extension="py",
        content_hash=content_hash,
    )


def _snapshot(files) -> InspectionSnapshot:
    return InspectionSnapshot(
        project_id="demo",
        root_path="/root",
        generated_at=datetime.now(timezone.utc),
        files={record.relative_path: record for record in files},
    )


def test_detect_returns_empty_when_no_previous_snapshot():
    current = _snapshot([_record("a.py")])
    assert DriftDetector().detect(None, current) == []


def test_detect_flags_added_file():
    previous = _snapshot([_record("a.py")])
    current = _snapshot([_record("a.py"), _record("b.py")])

    findings = DriftDetector().detect(previous, current)

    assert len(findings) == 1
    assert findings[0].code == "FILE_ADDED"
    assert findings[0].file_path == "b.py"


def test_detect_flags_removed_file():
    previous = _snapshot([_record("a.py"), _record("b.py")])
    current = _snapshot([_record("a.py")])

    findings = DriftDetector().detect(previous, current)

    assert len(findings) == 1
    assert findings[0].code == "FILE_REMOVED"
    assert findings[0].file_path == "b.py"


def test_detect_flags_modified_file_by_hash_change():
    previous = _snapshot([_record("a.py", content_hash="old-hash")])
    current = _snapshot([_record("a.py", content_hash="new-hash")])

    findings = DriftDetector().detect(previous, current)

    assert len(findings) == 1
    assert findings[0].code == "FILE_MODIFIED"


def test_detect_no_findings_when_unchanged():
    previous = _snapshot([_record("a.py")])
    current = _snapshot([_record("a.py")])

    assert DriftDetector().detect(previous, current) == []
