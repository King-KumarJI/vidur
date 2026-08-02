"""Unit tests for app.core.nlp.linguistic_analyzer."""

from app.core.nlp.linguistic_analyzer import LinguisticAnalyzer
from app.core.nlp.text_utils import tokenize


def test_is_available_when_spacy_model_loads():
    analyzer = LinguisticAnalyzer()
    assert analyzer.is_available is True


def test_extract_keywords_returns_empty_set_for_blank_text():
    analyzer = LinguisticAnalyzer()
    assert analyzer.extract_keywords("") == set()
    assert analyzer.extract_keywords("   ") == set()


def test_extract_keywords_lemmatizes_verb_tense_and_plural_forms():
    analyzer = LinguisticAnalyzer()

    keywords = analyzer.extract_keywords("validates incoming request payloads")

    assert "validate" in keywords
    assert "request" in keywords
    assert "incoming" in keywords


def test_extract_keywords_normalizes_matching_documented_and_implemented_text():
    analyzer = LinguisticAnalyzer()

    documented_keywords = analyzer.extract_keywords(
        "The system should validate incoming requests"
    )
    implemented_keywords = analyzer.extract_keywords("validates incoming request payloads")

    # "requests" (documented, plural) and "validates" (implemented, conjugated)
    # do not exact-match their counterparts, but do share a lemma.
    assert documented_keywords & implemented_keywords >= {"validate", "incoming", "request"}


def test_extract_keywords_drops_stopwords_and_short_tokens():
    analyzer = LinguisticAnalyzer()

    keywords = analyzer.extract_keywords("The system is up and it was on")

    assert keywords == {"system"}


def test_extract_keywords_falls_back_to_tokenize_when_model_unavailable():
    analyzer = LinguisticAnalyzer()
    analyzer._model = None  # simulate spaCy/model not being installed

    text = "The system should validate incoming requests"
    assert analyzer.is_available is False
    assert analyzer.extract_keywords(text) == set(tokenize(text))
