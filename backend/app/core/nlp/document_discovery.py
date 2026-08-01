"""
VIDUR Core - NLP
Submodule: Document Discovery
Purpose: Locate and classify the documents an NLP run reasons about -
README files, dependency manifests, and Python source files - from a
project's file inventory. Reuses ProjectFileScanner (Article 31-32)
rather than re-walking the file system.
"""

from pathlib import PurePosixPath
from typing import List, Optional

from app.core.inspection_engine.file_scanner import ProjectFileScanner
from app.core.inspection_engine.models import FileRecord
from app.core.nlp.enums import DocumentKind
from app.core.nlp.models import DiscoveredDocument

#: A dependency manifest is any top-of-tree `requirements*.txt` file
#: (e.g. `requirements.txt`, `requirements-dev.txt`). Nested
#: requirements files (inside a vendored dependency, for example) are
#: intentionally still included - they are still valid manifests.
_MANIFEST_PREFIX = "requirements"
_MANIFEST_SUFFIX = ".txt"


def _is_readme(record: FileRecord) -> bool:
    stem = PurePosixPath(record.relative_path).stem.lower()
    return stem == "readme"


def _is_dependency_manifest(record: FileRecord) -> bool:
    name = PurePosixPath(record.relative_path).name.lower()
    return name.startswith(_MANIFEST_PREFIX) and name.endswith(_MANIFEST_SUFFIX)


def _is_test_file(relative_path: str) -> bool:
    path = PurePosixPath(relative_path)
    return path.name.startswith("test_") or "tests" in path.parts


def _is_python_source(record: FileRecord) -> bool:
    return record.extension == "py" and not _is_test_file(record.relative_path)


class DocumentDiscovery:
    """Discovers and classifies the documents an NLP run reasons
    about, from a project root's file inventory."""

    def __init__(self, file_scanner: Optional[ProjectFileScanner] = None) -> None:
        self._file_scanner = file_scanner or ProjectFileScanner()

    def discover(self, root_path: str) -> List[DiscoveredDocument]:
        """Scan `root_path` and return every README, dependency
        manifest, and non-test Python source file as a
        DiscoveredDocument, sorted by relative path for deterministic
        output."""
        files = self._file_scanner.scan(root_path)

        documents: List[DiscoveredDocument] = []
        for record in files:
            kind = self._classify(record)
            if kind is None:
                continue
            documents.append(
                DiscoveredDocument(
                    kind=kind,
                    relative_path=record.relative_path,
                    absolute_path=record.absolute_path,
                )
            )

        documents.sort(key=lambda document: document.relative_path)
        return documents

    @staticmethod
    def _classify(record: FileRecord) -> Optional[DocumentKind]:
        if _is_readme(record):
            return DocumentKind.README
        if _is_dependency_manifest(record):
            return DocumentKind.DEPENDENCY_MANIFEST
        if _is_python_source(record):
            return DocumentKind.PYTHON_SOURCE
        return None
