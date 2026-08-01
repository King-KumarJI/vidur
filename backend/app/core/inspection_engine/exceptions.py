"""
VIDUR Core - Inspection Engine
Submodule: Exceptions
Purpose: Exception types for the static project inspection pipeline
(file scanning, code analysis, dependency analysis, architecture
validation, drift detection, and report generation).
"""


class InspectionEngineError(Exception):
    """Base class for all Inspection Engine errors."""


class InvalidInspectionTargetError(InspectionEngineError):
    """Raised when the target path to inspect does not exist, is not
    a directory, or is otherwise not a valid inspection root."""


class FileReadError(InspectionEngineError):
    """Raised when a file selected for inspection cannot be read
    (permission error, encoding error, I/O failure)."""


class CodeAnalysisError(InspectionEngineError):
    """Raised when static analysis of a source file fails for a
    reason other than a syntax error in the analyzed file itself."""


class InspectionDisabledError(InspectionEngineError):
    """Raised when an inspection is requested while the
    MINOR_PROJECT_INSPECTION feature flag is disabled."""
