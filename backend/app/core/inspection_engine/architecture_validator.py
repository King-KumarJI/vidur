"""
VIDUR Core - Inspection Engine
Submodule: Architecture Validator
Purpose: Enforce Article 30 (no TODO/FIXME/placeholder/pseudocode in
production code) and basic Python package structure consistency
(every directory containing source files is an importable package).
"""

import re
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, List, Pattern

from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import FileRecord, Finding

#: Marker code -> regex. Matched against raw source lines of non-test
#: Python files. These are the concrete, textual signals of
#: unfinished/placeholder code prohibited by Article 30.
FORBIDDEN_MARKERS: Dict[str, Pattern] = {
    "TODO": re.compile(r"\bTODO\b", re.IGNORECASE),
    "FIXME": re.compile(r"\bFIXME\b", re.IGNORECASE),
    "XXX": re.compile(r"\bXXX\b"),
    "PLACEHOLDER": re.compile(r"\bplaceholder\b", re.IGNORECASE),
    "PSEUDOCODE": re.compile(r"\bpseudocode\b", re.IGNORECASE),
}


class ArchitectureValidator:
    """Validates a scanned project's file inventory against the
    Constitution's production-readiness and package-structure rules."""

    def validate(self, files: List[FileRecord]) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._forbidden_marker_findings(files))
        findings.extend(self._missing_init_findings(files))
        return findings

    def _forbidden_marker_findings(self, files: List[FileRecord]) -> List[Finding]:
        findings: List[Finding] = []
        for record in files:
            if record.extension != "py" or self._is_test_file(record.relative_path):
                continue

            try:
                source = self._read_text(record)
            except (OSError, UnicodeDecodeError):
                continue

            for line_number, line in enumerate(source.splitlines(), start=1):
                for marker_code, pattern in FORBIDDEN_MARKERS.items():
                    if pattern.search(line):
                        findings.append(
                            Finding(
                                category=FindingCategory.ARCHITECTURE,
                                severity=Severity.WARNING,
                                code=f"FORBIDDEN_MARKER_{marker_code}",
                                message=(
                                    f"Line contains a prohibited '{marker_code}' marker; "
                                    "Article 30 forbids placeholder/incomplete code."
                                ),
                                file_path=record.relative_path,
                                line=line_number,
                            )
                        )
        return findings

    def _missing_init_findings(self, files: List[FileRecord]) -> List[Finding]:
        python_paths_by_dir: Dict[str, List[str]] = defaultdict(list)
        for record in files:
            if record.extension != "py" or self._is_test_file(record.relative_path):
                continue
            parent = str(PurePosixPath(record.relative_path).parent)
            python_paths_by_dir[parent].append(record.relative_path)

        findings: List[Finding] = []
        for directory, paths in python_paths_by_dir.items():
            expected_init = "__init__.py" if directory == "." else f"{directory}/__init__.py"
            if expected_init in paths:
                continue
            findings.append(
                Finding(
                    category=FindingCategory.ARCHITECTURE,
                    severity=Severity.WARNING,
                    code="MISSING_INIT_FILE",
                    message=(
                        f"Directory '{directory}' contains Python source files but no "
                        "__init__.py, so it is not an importable package."
                    ),
                    file_path=directory,
                    line=None,
                )
            )
        return findings

    @staticmethod
    def _is_test_file(relative_path: str) -> bool:
        path = PurePosixPath(relative_path)
        return path.name.startswith("test_") or "tests" in path.parts

    @staticmethod
    def _read_text(record: FileRecord) -> str:
        with open(record.absolute_path, "r", encoding="utf-8") as handle:
            return handle.read()
