"""
VIDUR Core - NLP
Submodule: Linguistic Analyzer
Purpose: Real linguistic analysis via spaCy's pretrained `en_core_web_sm`
pipeline (CLAUDE.md "Real AI/ML/DL/NLP Upgrade" -> NLP amendment),
layered on top of - not replacing - the existing AST-based
ImplementedIntentExtractor and TF-IDF SemanticSimilarityReasoner, which
both stay exactly as they are. Gives ConsistencyChecker a morphology-
normalized keyword set (lemmas of content-bearing tokens, noun-chunk
heads, and named entities) that survives the tense/plural/paraphrase
variation the stdlib `tokenize()` exact-word matching misses, reducing
both over-flagging (paraphrased documentation wrongly called
untraceable) and under-flagging.

Never blocks the pipeline: if spaCy or the `en_core_web_sm` model is
not installed, `LinguisticAnalyzer` degrades transparently to the
existing stdlib tokenizer and logs a warning once, matching the same
additive-fallback pattern the AI Reasoning module uses for Ollama.
"""

from functools import lru_cache
from typing import Any, Optional, Set

from app.config.logging_config import get_logger
from app.core.nlp.text_utils import tokenize

logger = get_logger("nlp.linguistic_analyzer")

_MODEL_NAME = "en_core_web_sm"

#: Keywords shorter than this are dropped as too generic to carry
#: matching signal, mirroring text_utils._MIN_TOKEN_LENGTH.
_MIN_KEYWORD_LENGTH = 3


@lru_cache(maxsize=1)
def _load_spacy_model() -> Optional[Any]:
    """Load and cache the spaCy `en_core_web_sm` pipeline for the
    lifetime of the process. Returns None instead of raising if spaCy
    or the model is not installed, so callers can degrade gracefully
    rather than crash an NLP run."""
    try:
        import spacy
    except ImportError as exc:
        logger.warning(
            "spaCy is not installed; linguistic analysis will fall back to the "
            "stdlib tokenizer. Install with: pip install spacy (%s)",
            exc,
        )
        return None

    try:
        return spacy.load(_MODEL_NAME)
    except OSError as exc:
        logger.warning(
            "spaCy model '%s' is not installed; linguistic analysis will fall "
            "back to the stdlib tokenizer. Install with: "
            "python -m spacy download %s (%s)",
            _MODEL_NAME,
            _MODEL_NAME,
            exc,
        )
        return None


class LinguisticAnalyzer:
    """Extracts a morphology-normalized keyword set from free text
    using spaCy's pretrained pipeline: lemmas of alphabetic,
    non-stopword tokens, lemmas of each noun chunk's head word, and
    the constituent words of every named entity. Falls back to
    `tokenize()` when spaCy is unavailable."""

    def __init__(self, model: Optional[Any] = None) -> None:
        self._model = model if model is not None else _load_spacy_model()

    @property
    def is_available(self) -> bool:
        """Whether a real spaCy pipeline is backing this analyzer
        (False means every call degrades to the stdlib tokenizer)."""
        return self._model is not None

    def extract_keywords(self, text: str) -> Set[str]:
        """Return a set of lowercase, morphology-normalized keywords
        for `text`. Uses spaCy's tagger/parser-informed lemmatizer,
        noun-chunk detection, and named-entity recognition when
        available; otherwise falls back to `tokenize(text)`."""
        if not text or not text.strip():
            return set()
        if self._model is None:
            return set(tokenize(text))

        doc = self._model(text)
        keywords: Set[str] = set()

        for token in doc:
            if not token.is_alpha or token.is_stop or token.is_punct:
                continue
            self._add_keyword(keywords, token.lemma_)

        for chunk in doc.noun_chunks:
            self._add_keyword(keywords, chunk.root.lemma_)

        for entity in doc.ents:
            for word in entity.text.split():
                if word.isalpha():
                    self._add_keyword(keywords, word)

        return keywords

    @staticmethod
    def _add_keyword(keywords: Set[str], raw: str) -> None:
        normalized = raw.strip().lower()
        if len(normalized) >= _MIN_KEYWORD_LENGTH:
            keywords.add(normalized)
