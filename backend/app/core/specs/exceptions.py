"""
VIDUR Core - Specs
Submodule: Exceptions
Purpose: Exception types for the Specs module (Personal / Computer /
Calendar / Environmental telemetry ingestion and storage, plus manual
deadline entries).
"""


class SpecsModuleError(Exception):
    """Base class for all Specs module errors."""


class SpecsDisabledError(SpecsModuleError):
    """Raised when a Specs operation is requested while the
    MAJOR_IOT_ENVIRONMENTAL_ANALYTICS feature flag is disabled."""


class InvalidSpecsPayloadError(SpecsModuleError):
    """Raised when an ingestion or deadline payload fails structural
    validation (for example, an empty deadline title)."""


class SpecsPersistenceError(SpecsModuleError):
    """Raised when the underlying MongoDB store fails to persist or
    retrieve Specs data."""
