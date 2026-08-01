"""Unit tests for app.core.nlp.intent_extractor."""

from app.core.nlp.document_discovery import DocumentDiscovery
from app.core.nlp.intent_extractor import DocumentedIntentExtractor

README_CONTENT = """# Demo Project

A short description.

## Features

- User authentication
- Email notifications

## Requirements

The system must send a confirmation email after signup.
As a user, I want to reset my password so that I can regain access.
This line is just prose about the project background.
"""

REQUIREMENTS_CONTENT = """
fastapi==0.115.0
pydantic-settings>=2.5.2
# a comment
-r other-requirements.txt
python-dotenv
"""


def _discover(tmp_path):
    (tmp_path / "README.md").write_text(README_CONTENT)
    (tmp_path / "requirements.txt").write_text(REQUIREMENTS_CONTENT)
    return DocumentDiscovery().discover(str(tmp_path))


def test_extract_title(tmp_path):
    documents = _discover(tmp_path)
    intent = DocumentedIntentExtractor().extract(documents)
    assert intent.project_title == "Demo Project"


def test_extract_features(tmp_path):
    documents = _discover(tmp_path)
    intent = DocumentedIntentExtractor().extract(documents)
    assert intent.declared_features == ["User authentication", "Email notifications"]


def test_extract_requirement_statements(tmp_path):
    documents = _discover(tmp_path)
    intent = DocumentedIntentExtractor().extract(documents)

    texts = [statement.text for statement in intent.requirement_statements]
    assert any("confirmation email" in text for text in texts)
    assert any(text.lower().startswith("as a user") for text in texts)
    assert not any("just prose" in text for text in texts)


def test_extract_dependencies_strips_versions_and_ignores_options(tmp_path):
    documents = _discover(tmp_path)
    intent = DocumentedIntentExtractor().extract(documents)

    assert intent.declared_dependencies == ["fastapi", "pydantic-settings", "python-dotenv"]


def test_extract_with_no_documents_returns_empty_intent(tmp_path):
    intent = DocumentedIntentExtractor().extract([])
    assert intent.project_title is None
    assert intent.declared_features == []
    assert intent.declared_dependencies == []
    assert intent.requirement_statements == []


def test_extract_handles_empty_readme(tmp_path):
    (tmp_path / "README.md").write_text("")
    documents = DocumentDiscovery().discover(str(tmp_path))
    intent = DocumentedIntentExtractor().extract(documents)
    assert intent.project_title is None
    assert intent.declared_features == []
