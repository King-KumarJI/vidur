"""
VIDUR Core - Inspection Engine
Submodule: File Scanner
Purpose: Walk a project's file system and build a deterministic file
inventory (FileRecord per file), skipping build artifacts, virtual
environments, and other noise that is not part of the developer's own
source tree.
"""

import hashlib
import os
from pathlib import Path
from typing import FrozenSet, List, Optional

from app.config.logging_config import get_logger
from app.core.inspection_engine.exceptions import FileReadError, InvalidInspectionTargetError
from app.core.inspection_engine.models import FileRecord

logger = get_logger("inspection_engine.file_scanner")

#: Directory names that are never descended into. These are build
#: artifacts, dependency trees, or VCS internals - never a developer's
#: own source, so inspecting them only produces noise.
DEFAULT_IGNORED_DIR_NAMES: FrozenSet[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "venv",
        ".venv",
        "env",
        ".env",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "site-packages",
        ".eggs",
    }
)

#: Above this size, a file's content is not hashed or line-counted in
#: full; only its size is recorded. Protects the scanner from being
#: stalled by large binary assets (media, datasets, archives).
DEFAULT_MAX_INSPECTED_BYTES = 5 * 1024 * 1024

_HASH_CHUNK_SIZE = 65536


class ProjectFileScanner:
    """Builds a `FileRecord` inventory for every file under a project
    root, excluding non-source noise directories."""

    def __init__(
        self,
        ignored_dir_names: Optional[FrozenSet[str]] = None,
        max_inspected_bytes: int = DEFAULT_MAX_INSPECTED_BYTES,
    ) -> None:
        self._ignored_dir_names = ignored_dir_names or DEFAULT_IGNORED_DIR_NAMES
        self._max_inspected_bytes = max_inspected_bytes

    def scan(self, root_path: str) -> List[FileRecord]:
        """Return a `FileRecord` for every non-ignored file under
        `root_path`, sorted by relative path for deterministic
        output."""
        root = Path(root_path)
        if not root.exists():
            raise InvalidInspectionTargetError(f"Inspection root does not exist: {root_path}")
        if not root.is_dir():
            raise InvalidInspectionTargetError(f"Inspection root is not a directory: {root_path}")

        records: List[FileRecord] = []
        for current_dir, dir_names, file_names in os.walk(root):
            dir_names[:] = [
                name for name in dir_names if name not in self._ignored_dir_names
            ]
            for file_name in file_names:
                absolute_path = Path(current_dir) / file_name
                try:
                    records.append(self._build_record(root, absolute_path))
                except FileReadError as exc:
                    logger.warning("Skipping unreadable file %s: %s", absolute_path, exc)

        records.sort(key=lambda record: record.relative_path)
        return records

    def _build_record(self, root: Path, absolute_path: Path) -> FileRecord:
        try:
            stat_result = absolute_path.stat()
        except OSError as exc:
            raise FileReadError(f"Unable to stat {absolute_path}: {exc}") from exc

        size_bytes = stat_result.st_size
        relative_path = absolute_path.relative_to(root).as_posix()

        if size_bytes > self._max_inspected_bytes:
            content_hash = ""
            line_count = 0
        else:
            content_bytes = self._read_bytes(absolute_path)
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            line_count = self._count_lines(content_bytes)

        return FileRecord(
            relative_path=relative_path,
            absolute_path=str(absolute_path),
            size_bytes=size_bytes,
            line_count=line_count,
            extension=absolute_path.suffix.lstrip("."),
            content_hash=content_hash,
        )

    @staticmethod
    def _read_bytes(path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileReadError(f"Unable to read {path}: {exc}") from exc

    @staticmethod
    def _count_lines(content_bytes: bytes) -> int:
        if not content_bytes:
            return 0
        return content_bytes.count(b"\n") + (0 if content_bytes.endswith(b"\n") else 1)
