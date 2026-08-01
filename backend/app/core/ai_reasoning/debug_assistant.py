"""
VIDUR Core - AI Reasoning
Submodule: Debugging Assistant
Purpose: Translate raw Inspection Engine finding codes into
probable-cause explanations and suggested diagnostic next steps for
the developer. Advisory only: per Article 10-11, VIDUR recommends and
never silently applies a fix.
"""

from collections import defaultdict
from typing import Dict, List, NamedTuple, Tuple

from app.core.ai_reasoning.models import DebuggingHypothesis
from app.core.inspection_engine.models import Finding


class _KnowledgeEntry(NamedTuple):
    probable_cause: str
    explanation: str
    suggested_next_steps: Tuple[str, ...]


#: Rule-based knowledge base keyed by exact Inspection Engine finding
#: code. Kept deliberately static and deterministic (no external
#: calls) so reasoning output is reproducible and explainable.
_KNOWLEDGE_BASE: Dict[str, _KnowledgeEntry] = {
    "SYNTAX_ERROR": _KnowledgeEntry(
        probable_cause="A Python source file could not be parsed.",
        explanation=(
            "The file has a syntax error, so no further static analysis "
            "(complexity, docstring coverage, dependency graph) could be "
            "performed on it. Every other finding for this file is "
            "incomplete until the syntax error is resolved."
        ),
        suggested_next_steps=(
            "Open the file at the reported line and confirm it parses "
            "with `python -m py_compile <file>`.",
            "Check for an unclosed bracket/string or an incomplete edit "
            "just above the reported line.",
        ),
    ),
    "HIGH_COMPLEXITY": _KnowledgeEntry(
        probable_cause="A function has accumulated too many independent branches.",
        explanation=(
            "High cyclomatic complexity usually means a function has grown "
            "multiple responsibilities over time (nested conditionals, "
            "long branch chains, repeated error handling), which makes it "
            "harder to test every path and more likely to hide a bug."
        ),
        suggested_next_steps=(
            "Identify independent branches inside the function and extract "
            "each into its own, separately testable function.",
            "Check whether unit tests exist for every branch; complexity "
            "hot-spots are the highest-value place to add coverage.",
        ),
    ),
    "LOW_DOCSTRING_COVERAGE": _KnowledgeEntry(
        probable_cause="Public functions/classes in the file lack documentation.",
        explanation=(
            "Low docstring coverage makes it harder for VIDUR (and other "
            "developers) to verify that the implementation matches its "
            "intended purpose, and often correlates with code that was "
            "written quickly under time pressure."
        ),
        suggested_next_steps=(
            "Add a one-line docstring to each undocumented public function "
            "or class stating its purpose.",
            "If the file's intent is unclear even to you, treat that as a "
            "signal the function may be doing more than one thing.",
        ),
    ),
    "CIRCULAR_DEPENDENCY": _KnowledgeEntry(
        probable_cause="Two or more modules import each other, directly or transitively.",
        explanation=(
            "Circular imports usually indicate that responsibilities are "
            "split across modules in a way that does not match their "
            "actual dependency direction, which can cause import-order "
            "failures and makes the modules impossible to reason about or "
            "test independently."
        ),
        suggested_next_steps=(
            "Identify the shared type or function causing the cycle and "
            "move it to a module that both sides can depend on one-way.",
            "Consider whether one of the two modules should not depend on "
            "the other at all.",
        ),
    ),
    "MISSING_INIT_FILE": _KnowledgeEntry(
        probable_cause="A directory holds Python source but is not an importable package.",
        explanation=(
            "Without an `__init__.py`, the directory is not a regular "
            "package, which can cause inconsistent import behavior "
            "depending on how the project is run or packaged."
        ),
        suggested_next_steps=(
            "Add an `__init__.py` to the reported directory.",
            "Confirm the directory was not intended to be excluded from "
            "the package (e.g. a scripts or notebooks folder).",
        ),
    ),
    "FILE_ADDED": _KnowledgeEntry(
        probable_cause="New source was introduced since the previous inspection.",
        explanation=(
            "New files are not inherently a problem, but they have not yet "
            "been through a full inspection history and are worth a first "
            "look to confirm they integrate cleanly."
        ),
        suggested_next_steps=(
            "Confirm the new file has its own findings reviewed, not just "
            "its existence noted.",
        ),
    ),
    "FILE_REMOVED": _KnowledgeEntry(
        probable_cause="A previously tracked source file no longer exists.",
        explanation=(
            "A removed file can be intentional cleanup, or it can silently "
            "break anything that still imports it. This is the highest-"
            "severity drift signal because it is the one most likely to "
            "cause a runtime failure elsewhere."
        ),
        suggested_next_steps=(
            "Search the rest of the project for remaining imports of the "
            "removed file's module path.",
            "Confirm the removal was intentional rather than an accidental "
            "delete.",
        ),
    ),
    "FILE_MODIFIED": _KnowledgeEntry(
        probable_cause="A tracked file's content changed since the previous inspection.",
        explanation=(
            "Modification alone is routine, but combined with other "
            "findings on the same file (or a large blast radius) it is a "
            "useful signal for where to focus review."
        ),
        suggested_next_steps=(
            "Review the modified file's other findings, if any, for "
            "issues introduced by the change.",
        ),
    ),
}

_FORBIDDEN_MARKER_PREFIX = "FORBIDDEN_MARKER_"

_GENERIC_ENTRY = _KnowledgeEntry(
    probable_cause="No specific rule is registered for this finding code.",
    explanation=(
        "This finding was raised by an analyzer but the Debugging "
        "Assistant does not yet have a specific hypothesis template for "
        "its code, so only the finding's own message is available."
    ),
    suggested_next_steps=(
        "Review the finding's message and file/line directly.",
    ),
)


def _forbidden_marker_entry(marker: str) -> _KnowledgeEntry:
    return _KnowledgeEntry(
        probable_cause=f"Unfinished or placeholder code marked '{marker}'.",
        explanation=(
            f"A '{marker}' marker signals work the original author knew was "
            "incomplete. Article 30 of the VIDUR Constitution prohibits "
            "placeholder/incomplete code from being treated as production-"
            "ready, so this line should not ship as-is."
        ),
        suggested_next_steps=(
            f"Resolve the work described at the '{marker}' marker, or "
            "confirm it is intentionally deferred and tracked elsewhere.",
            "Remove the marker once resolved so it stops surfacing here.",
        ),
    )


class DebuggingAssistant:
    """Generates one DebuggingHypothesis per distinct finding code
    present in a set of findings."""

    def generate(self, findings: List[Finding]) -> List[DebuggingHypothesis]:
        """Return one DebuggingHypothesis per distinct finding code,
        ordered by how often the code occurs (most frequent first)."""
        findings_by_code: Dict[str, List[Finding]] = defaultdict(list)
        for finding in findings:
            findings_by_code[finding.code].append(finding)

        hypotheses: List[DebuggingHypothesis] = []
        for code, code_findings in findings_by_code.items():
            entry = self._lookup(code)
            related_files = sorted(
                {finding.file_path for finding in code_findings if finding.file_path is not None}
            )
            hypotheses.append(
                DebuggingHypothesis(
                    finding_code=code,
                    probable_cause=entry.probable_cause,
                    explanation=entry.explanation,
                    suggested_next_steps=list(entry.suggested_next_steps),
                    occurrence_count=len(code_findings),
                    related_files=related_files,
                )
            )

        hypotheses.sort(key=lambda hypothesis: (-hypothesis.occurrence_count, hypothesis.finding_code))
        return hypotheses

    @staticmethod
    def _lookup(code: str) -> _KnowledgeEntry:
        if code in _KNOWLEDGE_BASE:
            return _KNOWLEDGE_BASE[code]
        if code.startswith(_FORBIDDEN_MARKER_PREFIX):
            return _forbidden_marker_entry(code[len(_FORBIDDEN_MARKER_PREFIX):])
        return _GENERIC_ENTRY
