"""
VIDUR Core - NLP
Submodule: Consistency Checker
Purpose: Minor-tier (MINOR_REQUIREMENT_CONSISTENCY), deterministic
comparison of DocumentedIntent against ImplementedIntent: dependency
declaration mismatches, and keyword-overlap traceability of declared
requirements and features into the implementation. Advisory only -
per Article 10-11, VIDUR never edits documentation or code to resolve
a finding it raises here.

Requirement/feature traceability is checked first by exact stdlib
keyword overlap (unchanged), then - only when that check would flag a
claim as untraceable - by a second pass over the same
MIN_KEYWORD_OVERLAP_RATIO threshold using LinguisticAnalyzer's
spaCy-backed, morphology-normalized keywords (lemmas, noun chunks,
named entities). This catches paraphrased or loosely-worded
documentation (tense/plural variation the exact-match pass cannot see)
without weakening detection of genuinely unimplemented requirements: a
claim is only rescued if it has real lemma-level overlap with the
implementation corpus, never unconditionally.
"""

import re
from typing import List, Optional, Set

from app.core.inspection_engine.enums import Severity
from app.core.nlp.enums import ConsistencyCategory
from app.core.nlp.linguistic_analyzer import LinguisticAnalyzer
from app.core.nlp.models import ConsistencyFinding, DocumentedIntent, ImplementedIntent
from app.core.nlp.text_utils import tokenize

#: Well-known cases where a PyPI distribution name does not match its
#: importable top-level package name. Kept as a small static table
#: (not resolved via the local Python environment's installed package
#: metadata) so a check of an *inspected* project's manifest never
#: depends on what happens to be installed in VIDUR's own environment
#: (Article 21 spirit: analysis must not leak VIDUR's own runtime
#: state into another project's isolated results).
_KNOWN_DISTRIBUTION_ALIASES = {
    "python-dotenv": "dotenv",
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
    "pillow": "pil",
    "python-multipart": "multipart",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "protobuf": "google",
}

_NON_ALNUM_RUN_PATTERN = re.compile(r"[-_.]+")

#: Fraction of a documented claim's distinctive keywords that must
#: appear somewhere in the implementation's text corpus (docstrings,
#: symbol names, comments) for the claim to be considered traceable.
#: This is a coarse keyword-overlap heuristic; the Major-tier
#: SemanticSimilarityReasoner (TF-IDF cosine similarity) supersedes it
#: with a graded score when MAJOR_ADVANCED_NLP_DOCUMENT_REASONING is
#: enabled.
MIN_KEYWORD_OVERLAP_RATIO = 0.5


def _canonicalize(name: str) -> str:
    return _NON_ALNUM_RUN_PATTERN.sub("-", name.strip().lower())


def _expected_import_name(declared_dependency: str) -> str:
    canonical = _canonicalize(declared_dependency)
    if canonical in _KNOWN_DISTRIBUTION_ALIASES:
        return _KNOWN_DISTRIBUTION_ALIASES[canonical]
    return canonical.replace("-", "_")


class ConsistencyChecker:
    """Compares DocumentedIntent against ImplementedIntent and returns
    the resulting ConsistencyFindings."""

    def __init__(self, linguistic_analyzer: Optional[LinguisticAnalyzer] = None) -> None:
        self._linguistic_analyzer = linguistic_analyzer or LinguisticAnalyzer()

    def check(
        self, documented: DocumentedIntent, implemented: ImplementedIntent
    ) -> List[ConsistencyFinding]:
        findings: List[ConsistencyFinding] = []
        findings.extend(self._dependency_findings(documented, implemented))

        corpus_keywords = self._corpus_keywords(implemented)
        linguistic_corpus_keywords = self._linguistic_corpus_keywords(implemented)
        findings.extend(
            self._requirement_findings(documented, corpus_keywords, linguistic_corpus_keywords)
        )
        findings.extend(
            self._feature_findings(documented, corpus_keywords, linguistic_corpus_keywords)
        )
        return findings

    @staticmethod
    def _corpus_keywords(implemented: ImplementedIntent) -> Set[str]:
        keywords: Set[str] = set()
        for blob in implemented.file_text_blobs.values():
            keywords.update(tokenize(blob))
        return keywords

    def _linguistic_corpus_keywords(self, implemented: ImplementedIntent) -> Set[str]:
        keywords: Set[str] = set()
        for blob in implemented.file_text_blobs.values():
            keywords.update(self._linguistic_analyzer.extract_keywords(blob))
        return keywords

    def _linguistically_traceable(
        self, claim_text: str, linguistic_corpus_keywords: Set[str]
    ) -> bool:
        if not linguistic_corpus_keywords:
            return False
        claim_keywords = self._linguistic_analyzer.extract_keywords(claim_text)
        if not claim_keywords:
            return False
        overlap_ratio = len(claim_keywords & linguistic_corpus_keywords) / len(claim_keywords)
        return overlap_ratio >= MIN_KEYWORD_OVERLAP_RATIO

    @staticmethod
    def _dependency_findings(
        documented: DocumentedIntent, implemented: ImplementedIntent
    ) -> List[ConsistencyFinding]:
        if not documented.declared_dependencies:
            # No manifest was discovered (or it declared nothing), so
            # there is nothing authoritative to compare imports
            # against; raising findings here would just be noise.
            return []

        imported = {name.lower() for name in implemented.imported_third_party_packages}
        expected_imports_by_dependency = {
            dependency: _expected_import_name(dependency)
            for dependency in documented.declared_dependencies
        }
        all_expected_imports = set(expected_imports_by_dependency.values())

        findings: List[ConsistencyFinding] = []
        for dependency, expected_import in expected_imports_by_dependency.items():
            if expected_import not in imported:
                findings.append(
                    ConsistencyFinding(
                        category=ConsistencyCategory.DEPENDENCY_CONSISTENCY,
                        severity=Severity.WARNING,
                        code="DECLARED_DEPENDENCY_UNUSED",
                        message=(
                            f"'{dependency}' is declared in the dependency manifest but no "
                            "matching import was found in the analyzed source. Confirm it is "
                            "still needed."
                        ),
                    )
                )

        for import_name in sorted(imported):
            if import_name not in all_expected_imports:
                findings.append(
                    ConsistencyFinding(
                        category=ConsistencyCategory.DEPENDENCY_CONSISTENCY,
                        severity=Severity.WARNING,
                        code="UNDECLARED_DEPENDENCY_USED",
                        message=(
                            f"Module '{import_name}' is imported in the analyzed source but no "
                            "matching entry was found in the dependency manifest. Confirm it is "
                            "declared."
                        ),
                    )
                )
        return findings

    def _requirement_findings(
        self,
        documented: DocumentedIntent,
        corpus_keywords: Set[str],
        linguistic_corpus_keywords: Set[str],
    ) -> List[ConsistencyFinding]:
        findings: List[ConsistencyFinding] = []
        for statement in documented.requirement_statements:
            keywords = set(statement.keywords)
            if not keywords:
                continue
            overlap_ratio = len(keywords & corpus_keywords) / len(keywords)
            if overlap_ratio >= MIN_KEYWORD_OVERLAP_RATIO:
                continue
            if self._linguistically_traceable(statement.text, linguistic_corpus_keywords):
                continue
            findings.append(
                ConsistencyFinding(
                    category=ConsistencyCategory.REQUIREMENT_TRACEABILITY,
                    severity=Severity.WARNING,
                    code="REQUIREMENT_NOT_TRACEABLE",
                    message=(
                        f"Requirement statement '{statement.text}' has no clear match in the "
                        f"implementation (keyword overlap {overlap_ratio:.0%}). Confirm it is "
                        "implemented or update the documentation."
                    ),
                    file_path=statement.source_path,
                    line=statement.line,
                )
            )
        return findings

    def _feature_findings(
        self,
        documented: DocumentedIntent,
        corpus_keywords: Set[str],
        linguistic_corpus_keywords: Set[str],
    ) -> List[ConsistencyFinding]:
        findings: List[ConsistencyFinding] = []
        for feature in documented.declared_features:
            keywords = set(tokenize(feature))
            if not keywords:
                continue
            overlap_ratio = len(keywords & corpus_keywords) / len(keywords)
            if overlap_ratio >= MIN_KEYWORD_OVERLAP_RATIO:
                continue
            if self._linguistically_traceable(feature, linguistic_corpus_keywords):
                continue
            findings.append(
                ConsistencyFinding(
                    category=ConsistencyCategory.FEATURE_TRACEABILITY,
                    severity=Severity.WARNING,
                    code="FEATURE_NOT_TRACEABLE",
                    message=(
                        f"Declared feature '{feature}' has no clear match in the implementation "
                        f"(keyword overlap {overlap_ratio:.0%}). Confirm it is implemented or "
                        "update the documentation."
                    ),
                )
            )
        return findings
