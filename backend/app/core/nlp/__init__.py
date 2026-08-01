"""
VIDUR Core - NLP Package.

Single import surface for running NLP analysis over a project root:
document discovery (README, dependency manifest, Python source),
documented/implemented intent extraction, requirement-to-
implementation consistency checking, and Major-tier TF-IDF semantic
similarity reasoning, aggregated into a single NLPReport.
"""

from app.core.nlp.code_intent_extractor import ImplementedIntentExtractor
from app.core.nlp.consistency_checker import ConsistencyChecker
from app.core.nlp.document_discovery import DocumentDiscovery
from app.core.nlp.engine import NLPEngine
from app.core.nlp.enums import ConsistencyCategory, DocumentKind, IntentSignalType
from app.core.nlp.exceptions import (
    DocumentReadError,
    InvalidNLPInputError,
    NLPDisabledError,
    NLPError,
)
from app.core.nlp.intent_extractor import DocumentedIntentExtractor
from app.core.nlp.models import (
    ConsistencyFinding,
    DiscoveredDocument,
    DocumentedIntent,
    ImplementedIntent,
    NLPReport,
    RequirementStatement,
    SemanticSimilarityResult,
)
from app.core.nlp.report_generator import NLPReportGenerator
from app.core.nlp.semantic_reasoner import SemanticSimilarityReasoner

__all__ = [
    "NLPEngine",
    "DocumentDiscovery",
    "DocumentedIntentExtractor",
    "ImplementedIntentExtractor",
    "ConsistencyChecker",
    "SemanticSimilarityReasoner",
    "NLPReportGenerator",
    "DocumentKind",
    "IntentSignalType",
    "ConsistencyCategory",
    "DiscoveredDocument",
    "RequirementStatement",
    "DocumentedIntent",
    "ImplementedIntent",
    "ConsistencyFinding",
    "SemanticSimilarityResult",
    "NLPReport",
    "NLPError",
    "NLPDisabledError",
    "InvalidNLPInputError",
    "DocumentReadError",
]
