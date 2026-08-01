"""
VIDUR Core - NLP
Submodule: Enums
Purpose: Shared enumerations used across the NLP pipeline for
discovered-document classification, documented-intent signal type, and
requirement/implementation consistency-finding category.
"""

from enum import Enum


class DocumentKind(str, Enum):
    """Classification of a single document discovered under a project
    root, by the role it plays in NLP analysis."""

    README = "readme"
    DEPENDENCY_MANIFEST = "dependency_manifest"
    PYTHON_SOURCE = "python_source"


class IntentSignalType(str, Enum):
    """Classification of a single documented-intent signal extracted
    from a README or manifest document."""

    FEATURE_MENTION = "feature_mention"
    DEPENDENCY_MENTION = "dependency_mention"
    REQUIREMENT_STATEMENT = "requirement_statement"


class ConsistencyCategory(str, Enum):
    """Classification of what a ConsistencyFinding is about."""

    DEPENDENCY_CONSISTENCY = "dependency_consistency"
    REQUIREMENT_TRACEABILITY = "requirement_traceability"
    FEATURE_TRACEABILITY = "feature_traceability"
