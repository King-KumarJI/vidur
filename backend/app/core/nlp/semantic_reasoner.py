"""
VIDUR Core - NLP
Submodule: Semantic Reasoner
Purpose: Major-tier (MAJOR_ADVANCED_NLP_DOCUMENT_REASONING), advanced
NLP document reasoning per Chapter VII - TF-IDF weighted cosine
similarity between documented claims (requirement statements and
declared features) and each analyzed file's text blob, producing a
graded traceability score and best-match file instead of the
Minor-tier's boolean keyword-overlap check. Pure stdlib (no external
NLP/ML library), consistent with the rest of the NLP pipeline. Ships
disabled by default per Article 42; gating is enforced by the caller
(NLPEngine), not by this class itself.
"""

import math
from collections import Counter
from typing import Dict, List

from app.core.nlp.models import DocumentedIntent, ImplementedIntent, SemanticSimilarityResult
from app.core.nlp.text_utils import tokenize

_TermVector = Dict[str, float]


class SemanticSimilarityReasoner:
    """Scores every documented claim (feature or requirement) against
    every analyzed file's text blob using TF-IDF cosine similarity,
    and returns the best-matching file per claim."""

    def reason(
        self, documented: DocumentedIntent, implemented: ImplementedIntent
    ) -> List[SemanticSimilarityResult]:
        """Return one SemanticSimilarityResult per non-empty documented
        claim, or an empty list if there are no claims or no analyzed
        files to compare against."""
        claims = self._collect_claims(documented)
        if not claims or not implemented.file_text_blobs:
            return []

        file_paths = sorted(implemented.file_text_blobs)
        file_token_lists = [tokenize(implemented.file_text_blobs[path]) for path in file_paths]
        idf = self._compute_idf(file_token_lists)
        file_vectors = [self._tfidf_vector(tokens, idf) for tokens in file_token_lists]

        results: List[SemanticSimilarityResult] = []
        for claim in claims:
            claim_tokens = tokenize(claim)
            if not claim_tokens:
                continue
            claim_vector = self._tfidf_vector(claim_tokens, idf)

            best_path = None
            best_score = 0.0
            for file_path, file_vector in zip(file_paths, file_vectors):
                score = self._cosine_similarity(claim_vector, file_vector)
                if score > best_score:
                    best_score = score
                    best_path = file_path

            results.append(
                SemanticSimilarityResult(
                    claim_text=claim,
                    best_match_file=best_path,
                    similarity_score=round(best_score, 4),
                )
            )
        return results

    @staticmethod
    def _collect_claims(documented: DocumentedIntent) -> List[str]:
        claims = list(documented.declared_features)
        claims.extend(statement.text for statement in documented.requirement_statements)
        return claims

    @staticmethod
    def _compute_idf(token_lists: List[List[str]]) -> Dict[str, float]:
        """Smoothed inverse document frequency, matching the standard
        `smooth_idf=True` formula: `ln((1 + N) / (1 + df)) + 1`. The
        smoothing avoids division by zero and prevents a term
        appearing in every document from being weighted to zero."""
        document_count = len(token_lists)
        document_frequency: Counter = Counter()
        for tokens in token_lists:
            document_frequency.update(set(tokens))

        return {
            term: math.log((1 + document_count) / (1 + freq)) + 1.0
            for term, freq in document_frequency.items()
        }

    @staticmethod
    def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> _TermVector:
        term_frequency = Counter(tokens)
        total_terms = sum(term_frequency.values())
        if total_terms == 0:
            return {}
        return {
            term: (count / total_terms) * idf.get(term, 0.0)
            for term, count in term_frequency.items()
        }

    @staticmethod
    def _cosine_similarity(vector_a: _TermVector, vector_b: _TermVector) -> float:
        if not vector_a or not vector_b:
            return 0.0
        shared_terms = set(vector_a) & set(vector_b)
        dot_product = sum(vector_a[term] * vector_b[term] for term in shared_terms)
        norm_a = math.sqrt(sum(value * value for value in vector_a.values()))
        norm_b = math.sqrt(sum(value * value for value in vector_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)
