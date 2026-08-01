"""Unit tests for app.core.inspection_engine.report_generator."""

from datetime import datetime, timezone

from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.models import FileRecord
from app.core.inspection_engine.report_generator import InspectionReportGenerator


def _record(path: str) -> FileRecord:
    return FileRecord(
        relative_path=path,
        absolute_path=f"/root/{path}",
        size_bytes=10,
        line_count=1,
        extension="py",
        content_hash="hash",
    )


def test_build_snapshot_keys_files_by_relative_path():
    generator = InspectionReportGenerator()
    files = [_record("a.py"), _record("b.py")]

    snapshot = generator.build_snapshot("demo", "/root", files)

    assert set(snapshot.files) == {"a.py", "b.py"}
    assert snapshot.project_id == "demo"


def test_generate_builds_complete_report_with_health_score():
    generator = InspectionReportGenerator()
    files = [_record("a.py")]
    started_at = datetime.now(timezone.utc)

    report = generator.generate(
        project_id="demo",
        root_path="/root",
        status=InspectionStatus.COMPLETED,
        started_at=started_at,
        files=files,
        file_metrics=[],
        findings=[],
    )

    assert report.project_id == "demo"
    assert report.status is InspectionStatus.COMPLETED
    assert report.health_score == 100.0
    assert report.snapshot is not None
    assert set(report.snapshot.files) == {"a.py"}
    assert report.to_dict()["project_id"] == "demo"


def test_generate_reuses_provided_snapshot_instead_of_rebuilding():
    generator = InspectionReportGenerator()
    files = [_record("a.py")]
    provided_snapshot = generator.build_snapshot("demo", "/root", files)

    report = generator.generate(
        project_id="demo",
        root_path="/root",
        status=InspectionStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        files=files,
        file_metrics=[],
        findings=[],
        snapshot=provided_snapshot,
    )

    assert report.snapshot is provided_snapshot
