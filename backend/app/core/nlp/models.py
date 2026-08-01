"""
VIDUR Core - NLP
Submodule: Models
Purpose: Plain, JSON-serializable data structures produced and
consumed by the NLP pipeline (discovered documents, documented and
implemented intent, requirement/implementation consistency findings,
semantic similarity results, and the aggregated report).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.inspection_engine.enums import Severity
from app.core.nlp.enums import ConsistencyCategory, DocumentKind


@dataclass(frozen=True)
class DiscoveredDocument:
    """A single document discovered under a project root and
    classified by the role it plays in NLP analysis."""

    kind: DocumentKind
    relative_path: str
    absolute_path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
        }


@dataclass(frozen=True)
class RequirementStatement:
    """A single requirement- or user-story-style sentence extracted
    from a README document, along with the normalized keywords used to
    trace it against the implementation."""

    text: str
    source_path: str
    line: int
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_path": self.source_path,
            "line": self.line,
            "keywords": list(self.keywords),
        }


@dataclass(frozen=True)
class DocumentedIntent:
    """What the project's own documentation (README, dependency
    manifest) says it does and depends on."""

    project_title: Optional[str] = None
    declared_features: List[str] = field(default_factory=list)
    declared_dependencies: List[str] = field(default_factory=list)
    requirement_statements: List[RequirementStatement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_title": self.project_title,
            "declared_features": list(self.declared_features),
            "declared_dependencies": list(self.declared_dependencies),
            "requirement_statements": [
                statement.to_dict() for statement in self.requirement_statements
            ],
        }


@dataclass(frozen=True)
class ImplementedIntent:
    """What the project's own Python source actually imports and
    documents, extracted for comparison against DocumentedIntent."""

    analyzed_file_count: int = 0
    imported_third_party_packages: List[str] = field(default_factory=list)
    file_text_blobs: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyzed_file_count": self.analyzed_file_count,
            "imported_third_party_packages": list(self.imported_third_party_packages),
            "file_text_blobs": dict(self.file_text_blobs),
        }


@dataclass(frozen=True)
class ConsistencyFinding:
    """A single, concrete inconsistency between documented intent and
    the actual implementation. Advisory only: per Article 10-11, VIDUR
    recommends and never silently modifies documentation or code to
    resolve it."""

    category: ConsistencyCategory
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
class SemanticSimilarityResult:
    """Major-tier result: the best-matching implementation file for one
    documented claim (a requirement statement or declared feature),
    scored by TF-IDF cosine similarity rather than raw keyword overlap.
    Only produced when MAJOR_ADVANCED_NLP_DOCUMENT_REASONING is
    enabled."""

    claim_text: str
    best_match_file: Optional[str]
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "best_match_file": self.best_match_file,
            "similarity_score": self.similarity_score,
        }


@dataclass
class NLPReport:
    """Aggregated result of a single NLP analysis run over one project
    root."""

    project_id: str
    root_path: str
    generated_at: datetime
    documented_intent: DocumentedIntent
    implemented_intent: ImplementedIntent
    consistency_findings: List[ConsistencyFinding] = field(default_factory=list)
    semantic_similarity_results: List[SemanticSimilarityResult] = field(default_factory=list)

    def findings_by_category(self, category: ConsistencyCategory) -> List[ConsistencyFinding]:
        return [finding for finding in self.consistency_findings if finding.category is category]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_path": self.root_path,
            "generated_at": self.generated_at.isoformat(),
            "documented_intent": self.documented_intent.to_dict(),
            "implemented_intent": self.implemented_intent.to_dict(),
            "consistency_findings": [finding.to_dict() for finding in self.consistency_findings],
            "semantic_similarity_results": [
                result.to_dict() for result in self.semantic_similarity_results
            ],
        }
