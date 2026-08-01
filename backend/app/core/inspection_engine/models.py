"""
VIDUR Core - Inspection Engine
Submodule: Models
Purpose: Plain, JSON-serializable data structures produced and
consumed by the inspection pipeline (file inventory, per-file
metrics, findings, snapshots, and the aggregated report).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.inspection_engine.enums import FindingCategory, InspectionStatus, Severity


@dataclass(frozen=True)
class FileRecord:
    """Inventory record for a single file discovered during a scan."""

    relative_path: str
    absolute_path: str
    size_bytes: int
    line_count: int
    extension: str
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "extension": self.extension,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class FileMetrics:
    """Static code analysis metrics for a single Python source file."""

    relative_path: str
    function_count: int
    class_count: int
    max_cyclomatic_complexity: int
    average_cyclomatic_complexity: float
    docstring_coverage: float
    has_syntax_error: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "average_cyclomatic_complexity": self.average_cyclomatic_complexity,
            "docstring_coverage": self.docstring_coverage,
            "has_syntax_error": self.has_syntax_error,
        }


@dataclass(frozen=True)
class Finding:
    """A single inspection finding: one concrete, actionable issue
    surfaced by an analyzer."""

    category: FindingCategory
    severity: Severity
    code: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
        }


@dataclass(frozen=True)
class InspectionSnapshot:
    """Point-in-time record of a project's file inventory, keyed by
    relative path. Used as the baseline for drift detection against a
    later inspection run. Persistence of snapshots between runs is
    the responsibility of the caller (the future Memory module); the
    Inspection Engine itself only produces and compares them."""

    project_id: str
    root_path: str
    generated_at: datetime
    files: Dict[str, FileRecord] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_path": self.root_path,
            "generated_at": self.generated_at.isoformat(),
            "files": {path: record.to_dict() for path, record in self.files.items()},
        }


@dataclass
class InspectionReport:
    """Aggregated result of a single inspection run."""

    project_id: str
    root_path: str
    status: InspectionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    files: List[FileRecord] = field(default_factory=list)
    file_metrics: List[FileMetrics] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    health_score: float = 100.0
    snapshot: Optional[InspectionSnapshot] = None

    def findings_by_severity(self, severity: Severity) -> List[Finding]:
        return [finding for finding in self.findings if finding.severity is severity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_path": self.root_path,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files": [record.to_dict() for record in self.files],
            "file_metrics": [metrics.to_dict() for metrics in self.file_metrics],
            "findings": [finding.to_dict() for finding in self.findings],
            "health_score": self.health_score,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
        }


def utc_now() -> datetime:
    """Return the current UTC time. Centralized so every part of the
    inspection pipeline stamps timestamps consistently."""
    return datetime.now(timezone.utc)
