"""
VIDUR Core - Inspection Engine Package.

Single import surface for running a full static project inspection:
file scanning, AST-based code analysis, internal dependency-cycle
detection, Article 30 / package-structure architecture validation,
snapshot-based drift detection, health scoring, and report assembly.
"""

from app.core.inspection_engine.architecture_validator import ArchitectureValidator
from app.core.inspection_engine.code_analyzer import PythonCodeAnalyzer
from app.core.inspection_engine.dependency_analyzer import DependencyAnalyzer
from app.core.inspection_engine.drift_detector import DriftDetector
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.enums import FindingCategory, InspectionStatus, Severity
from app.core.inspection_engine.exceptions import (
    CodeAnalysisError,
    FileReadError,
    InspectionDisabledError,
    InspectionEngineError,
    InvalidInspectionTargetError,
)
from app.core.inspection_engine.file_scanner import ProjectFileScanner
from app.core.inspection_engine.health_score import HealthScoreCalculator
from app.core.inspection_engine.models import (
    FileMetrics,
    FileRecord,
    Finding,
    InspectionReport,
    InspectionSnapshot,
)
from app.core.inspection_engine.report_generator import InspectionReportGenerator

__all__ = [
    "InspectionEngine",
    "ProjectFileScanner",
    "PythonCodeAnalyzer",
    "DependencyAnalyzer",
    "ArchitectureValidator",
    "DriftDetector",
    "HealthScoreCalculator",
    "InspectionReportGenerator",
    "Severity",
    "FindingCategory",
    "InspectionStatus",
    "FileRecord",
    "FileMetrics",
    "Finding",
    "InspectionSnapshot",
    "InspectionReport",
    "InspectionEngineError",
    "InvalidInspectionTargetError",
    "FileReadError",
    "CodeAnalysisError",
    "InspectionDisabledError",
]
