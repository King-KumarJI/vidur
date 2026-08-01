"""
VIDUR Core - NLP
Submodule: Code Intent Extractor
Purpose: Extract ImplementedIntent - actually-imported third-party
packages and a per-file text blob of docstrings, symbol names, and
comments - from a project's Python source documents, for comparison
against DocumentedIntent.
"""

import ast
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Set

from app.config.logging_config import get_logger
from app.core.nlp.enums import DocumentKind
from app.core.nlp.models import DiscoveredDocument, ImplementedIntent

logger = get_logger("nlp.code_intent_extractor")

#: Standard-library module top-level names, used to exclude stdlib
#: imports from the "third-party dependency" set. `__future__` is
#: included explicitly for older interpreters where it is not part of
#: `sys.stdlib_module_names`.
_STDLIB_MODULE_NAMES: Set[str] = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

_SHEBANG_PREFIX = "#!"
_ENCODING_COOKIE_PATTERN = re.compile(r"coding[:=]\s*[-\w.]+")

_FunctionOrClassNode = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class ImplementedIntentExtractor:
    """Extracts ImplementedIntent from a project's discovered Python
    source documents."""

    def extract(self, documents: List[DiscoveredDocument]) -> ImplementedIntent:
        """Return the ImplementedIntent for `documents` (only entries
        with kind PYTHON_SOURCE are analyzed; others are ignored)."""
        python_documents = [doc for doc in documents if doc.kind is DocumentKind.PYTHON_SOURCE]
        internal_package_names = self._internal_package_names(python_documents)

        third_party_packages: Set[str] = set()
        file_text_blobs: Dict[str, str] = {}
        analyzed_count = 0

        for document in python_documents:
            source = self._read(document)
            if source is None:
                continue

            try:
                tree = ast.parse(source, filename=document.relative_path)
            except SyntaxError as exc:
                logger.warning("Skipping unparseable file %s: %s", document.relative_path, exc)
                continue

            analyzed_count += 1
            third_party_packages.update(self._third_party_imports(tree, internal_package_names))
            file_text_blobs[document.relative_path] = self._text_blob(tree, source)

        return ImplementedIntent(
            analyzed_file_count=analyzed_count,
            imported_third_party_packages=sorted(third_party_packages),
            file_text_blobs=file_text_blobs,
        )

    @staticmethod
    def _read(document: DiscoveredDocument) -> Optional[str]:
        try:
            return Path(document.absolute_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unreadable document %s: %s", document.relative_path, exc)
            return None

    @staticmethod
    def _internal_package_names(python_documents: List[DiscoveredDocument]) -> Set[str]:
        return {
            PurePosixPath(document.relative_path).parts[0] for document in python_documents
        }

    @staticmethod
    def _third_party_imports(tree: ast.Module, internal_package_names: Set[str]) -> Set[str]:
        imported: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue  # relative import: always internal
                if node.module:
                    imported.add(node.module.split(".")[0])

        return {
            name
            for name in imported
            if name not in _STDLIB_MODULE_NAMES and name not in internal_package_names
        }

    @staticmethod
    def _text_blob(tree: ast.Module, source: str) -> str:
        parts: List[str] = []

        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            parts.append(module_docstring.splitlines()[0])

        for node in ast.walk(tree):
            if isinstance(node, _FunctionOrClassNode):
                parts.append(node.name)
                node_docstring = ast.get_docstring(node)
                if node_docstring:
                    parts.append(node_docstring.splitlines()[0])

        parts.extend(ImplementedIntentExtractor._comment_texts(source))
        return " ".join(parts)

    @staticmethod
    def _comment_texts(source: str) -> List[str]:
        # Line-based scan, not full tokenization: a '#' inside a string
        # literal would be misread as a comment. This mirrors the same
        # deliberate trade-off the Inspection Engine's forbidden-marker
        # scan makes (see ArchitectureValidator) - acceptable for a
        # best-effort intent signal, not a correctness-critical check.
        texts: List[str] = []
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#") or stripped.startswith(_SHEBANG_PREFIX):
                continue
            comment_text = stripped.lstrip("#").strip()
            if not comment_text or _ENCODING_COOKIE_PATTERN.search(comment_text):
                continue
            texts.append(comment_text)
        return texts
