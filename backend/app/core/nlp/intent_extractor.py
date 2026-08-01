"""
VIDUR Core - NLP
Submodule: Intent Extractor
Purpose: Extract DocumentedIntent - project title, declared features,
requirement/user-story statements, and declared dependencies - from
README and dependency-manifest documents. Deterministic, rule-based
text extraction; no external NLP library or LLM call (Article 38: no
new dependency beyond the approved stack).
"""

import re
from pathlib import Path
from typing import List, Optional, Set

from app.config.logging_config import get_logger
from app.core.nlp.enums import DocumentKind
from app.core.nlp.models import DiscoveredDocument, DocumentedIntent, RequirementStatement
from app.core.nlp.text_utils import tokenize

logger = get_logger("nlp.intent_extractor")

_TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_FEATURE_HEADING_PATTERN = re.compile(r"^#{1,6}\s*Features?\b.*$", re.IGNORECASE | re.MULTILINE)
_BULLET_PATTERN = re.compile(r"^[-*+]\s+(.+)$")
_MODAL_PATTERN = re.compile(r"\b(must|shall|should)\b", re.IGNORECASE)
_USER_STORY_PATTERN = re.compile(r"^as\s+an?\s+.+,?\s*i\s+want\b", re.IGNORECASE)
_PACKAGE_NAME_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)")


class DocumentedIntentExtractor:
    """Extracts DocumentedIntent from a project's discovered README
    and dependency-manifest documents."""

    def extract(self, documents: List[DiscoveredDocument]) -> DocumentedIntent:
        """Return the DocumentedIntent for `documents`. Multiple
        README documents are merged (first title found wins, features
        and requirement statements are concatenated); multiple
        manifests contribute a single merged dependency set."""
        readmes = [doc for doc in documents if doc.kind is DocumentKind.README]
        manifests = [doc for doc in documents if doc.kind is DocumentKind.DEPENDENCY_MANIFEST]

        title: Optional[str] = None
        features: List[str] = []
        seen_features: Set[str] = set()
        requirement_statements: List[RequirementStatement] = []

        for document in readmes:
            content = self._read(document)
            if content is None:
                continue
            if title is None:
                title = self._extract_title(content)
            for feature in self._extract_features(content):
                if feature not in seen_features:
                    seen_features.add(feature)
                    features.append(feature)
            requirement_statements.extend(self._extract_requirement_statements(document, content))

        dependencies: Set[str] = set()
        for document in manifests:
            content = self._read(document)
            if content is None:
                continue
            dependencies.update(self._extract_dependencies(content))

        return DocumentedIntent(
            project_title=title,
            declared_features=features,
            declared_dependencies=sorted(dependencies),
            requirement_statements=requirement_statements,
        )

    @staticmethod
    def _read(document: DiscoveredDocument) -> Optional[str]:
        try:
            return Path(document.absolute_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unreadable document %s: %s", document.relative_path, exc)
            return None

    @staticmethod
    def _extract_title(content: str) -> Optional[str]:
        match = _TITLE_PATTERN.search(content)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_features(content: str) -> List[str]:
        heading_match = _FEATURE_HEADING_PATTERN.search(content)
        if heading_match is None:
            return []

        features: List[str] = []
        for line in content[heading_match.end():].splitlines():
            stripped = line.strip()
            if not stripped:
                if features:
                    break
                continue
            if stripped.startswith("#"):
                break
            bullet_match = _BULLET_PATTERN.match(stripped)
            if bullet_match:
                features.append(bullet_match.group(1).strip())
            elif features:
                break
        return features

    @staticmethod
    def _extract_requirement_statements(
        document: DiscoveredDocument, content: str
    ) -> List[RequirementStatement]:
        statements: List[RequirementStatement] = []
        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if not (_MODAL_PATTERN.search(stripped) or _USER_STORY_PATTERN.match(stripped)):
                continue

            bullet_match = _BULLET_PATTERN.match(stripped)
            clean_text = bullet_match.group(1).strip() if bullet_match else stripped
            keywords = sorted(set(tokenize(clean_text)))
            if not keywords:
                continue

            statements.append(
                RequirementStatement(
                    text=clean_text,
                    source_path=document.relative_path,
                    line=line_number,
                    keywords=keywords,
                )
            )
        return statements

    @staticmethod
    def _extract_dependencies(content: str) -> Set[str]:
        packages: Set[str] = set()
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            match = _PACKAGE_NAME_PATTERN.match(line)
            if match:
                packages.add(match.group(1).lower())
        return packages
