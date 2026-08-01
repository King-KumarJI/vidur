"""Unit tests for app.core.nlp.text_utils."""

from app.core.nlp.text_utils import tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    tokens = tokenize("The system must send an Email to the user")
    assert "the" not in tokens
    assert "must" not in tokens  # stopword
    assert "send" in tokens
    assert "email" in tokens


def test_tokenize_splits_snake_case_identifiers():
    tokens = tokenize("code_analyzer")
    assert "code" in tokens
    assert "analyzer" in tokens


def test_tokenize_splits_camel_case_identifiers():
    tokens = tokenize("CodeAnalyzer")
    assert "code" in tokens
    assert "analyzer" in tokens


def test_tokenize_drops_short_tokens():
    tokens = tokenize("a an if to")
    assert tokens == []


def test_tokenize_empty_string_returns_empty_list():
    assert tokenize("") == []
