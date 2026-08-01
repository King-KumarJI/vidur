"""Unit tests for app.core.nlp.code_intent_extractor."""

from app.core.nlp.code_intent_extractor import ImplementedIntentExtractor
from app.core.nlp.document_discovery import DocumentDiscovery


def _discover(tmp_path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "service.py").write_text(
        '"""Sends notification emails."""\n'
        "import os\n"
        "import requests\n"
        "from app.util import helper\n"
        "\n"
        "# handles email delivery\n"
        "class EmailSender:\n"
        '    """Sends an email."""\n'
        "    def send(self):\n"
        "        pass\n"
    )
    (pkg / "broken.py").write_text("def broken(:\n")
    return DocumentDiscovery().discover(str(tmp_path))


def test_extract_collects_third_party_imports_excluding_stdlib_and_internal(tmp_path):
    documents = _discover(tmp_path)
    intent = ImplementedIntentExtractor().extract(documents)
    assert intent.imported_third_party_packages == ["requests"]


def test_extract_skips_unparseable_files(tmp_path):
    documents = _discover(tmp_path)
    intent = ImplementedIntentExtractor().extract(documents)
    assert "app/broken.py" not in intent.file_text_blobs
    assert intent.analyzed_file_count == 2  # __init__.py + service.py, not broken.py


def test_extract_builds_text_blob_from_docstrings_names_and_comments(tmp_path):
    documents = _discover(tmp_path)
    intent = ImplementedIntentExtractor().extract(documents)
    blob = intent.file_text_blobs["app/service.py"]

    assert "Sends notification emails" in blob
    assert "EmailSender" in blob
    assert "Sends an email" in blob
    assert "handles email delivery" in blob


def test_extract_with_no_documents_returns_empty_intent():
    intent = ImplementedIntentExtractor().extract([])
    assert intent.analyzed_file_count == 0
    assert intent.imported_third_party_packages == []
    assert intent.file_text_blobs == {}
