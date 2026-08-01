"""
VIDUR Core - NLP
Submodule: Text Utilities
Purpose: Shared, stdlib-only tokenization used across the NLP pipeline
(requirement/feature keyword extraction, implemented-intent corpus
building, and TF-IDF semantic reasoning), so every stage normalizes
text identically.
"""

import re
from typing import List

#: Matches a run of alphanumeric/underscore characters - deliberately
#: simple (no external tokenizer library) so behavior is deterministic
#: and reproducible across environments.
_WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")

#: Common English function words plus a handful of project/document
#: filler words that carry no discriminating signal for requirement
#: traceability matching.
STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "for", "to",
        "of", "in", "on", "at", "by", "with", "as", "is", "are", "was", "were",
        "be", "been", "being", "this", "that", "these", "those", "it", "its",
        "so", "not", "no", "do", "does", "did", "will", "would", "can", "could",
        "should", "shall", "must", "may", "might", "than", "into", "from",
        "about", "each", "which", "who", "whom", "i", "you", "we", "they",
        "user", "want", "wants",
    }
)

#: Tokens shorter than this length are dropped as too generic to be a
#: useful matching signal (e.g. single letters left over from splitting
#: identifiers).
_MIN_TOKEN_LENGTH = 3


def tokenize(text: str) -> List[str]:
    """Split `text` into lowercase word tokens, dropping stopwords and
    tokens shorter than the minimum useful length.

    Underscore- and camelCase-style identifiers are split into their
    constituent words first (e.g. `code_analyzer` and `CodeAnalyzer`
    both yield `code`, `analyzer`), so identifier names extracted from
    source code are comparable with natural-language document text.
    """
    tokens: List[str] = []
    for raw_word in _WORD_PATTERN.findall(text):
        for part in _split_identifier(raw_word):
            lowered = part.lower()
            if len(lowered) < _MIN_TOKEN_LENGTH or lowered in STOPWORDS:
                continue
            tokens.append(lowered)
    return tokens


def _split_identifier(word: str) -> List[str]:
    """Split a single token on underscores and camelCase boundaries."""
    parts: List[str] = []
    for underscore_part in word.split("_"):
        if not underscore_part:
            continue
        camel_split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", underscore_part)
        parts.extend(camel_split if camel_split else [underscore_part])
    return parts
