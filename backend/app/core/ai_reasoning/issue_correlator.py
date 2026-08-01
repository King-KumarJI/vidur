"""
VIDUR Core - AI Reasoning
Submodule: Issue Correlator
Purpose: Group Inspection Engine findings that are likely related,
so the developer sees "one problem with five symptoms" instead of
five unrelated-looking findings. Two correlation bases are used:
findings concentrated in the same file, and the same finding code
recurring across multiple files (a systemic pattern).
"""

from collections import defaultdict
from typing import Dict, List

from app.core.ai_reasoning.enums import CorrelationBasis
from app.core.ai_reasoning.models import IssueCorrelationGroup
from app.core.inspection_engine.models import Finding

#: Minimum number of findings (same file) or distinct files (same
#: code) required before a correlation group is worth surfacing. Below
#: this, grouping adds noise rather than insight.
MIN_GROUP_SIZE = 2


class IssueCorrelator:
    """Derives IssueCorrelationGroups from a flat list of findings."""

    def correlate(self, findings: List[Finding]) -> List[IssueCorrelationGroup]:
        """Return correlation groups ordered by total severity weight
        (most significant first), then by group key for stability."""
        groups: List[IssueCorrelationGroup] = []
        groups.extend(self._same_file_groups(findings))
        groups.extend(self._same_code_groups(findings))
        groups.sort(key=lambda group: (-self._weight(group), group.basis.value, group.key))
        return groups

    @staticmethod
    def _weight(group: IssueCorrelationGroup) -> int:
        return sum(finding.severity.weight for finding in group.findings)

    def _same_file_groups(self, findings: List[Finding]) -> List[IssueCorrelationGroup]:
        by_file: Dict[str, List[Finding]] = defaultdict(list)
        for finding in findings:
            if finding.file_path is not None:
                by_file[finding.file_path].append(finding)

        groups: List[IssueCorrelationGroup] = []
        for file_path, file_findings in by_file.items():
            if len(file_findings) < MIN_GROUP_SIZE:
                continue
            groups.append(
                IssueCorrelationGroup(
                    basis=CorrelationBasis.SAME_FILE,
                    key=file_path,
                    findings=file_findings,
                    summary=(
                        f"{len(file_findings)} findings are concentrated in "
                        f"'{file_path}'; the file likely needs focused review "
                        "rather than a series of independent fixes."
                    ),
                )
            )
        return groups

    def _same_code_groups(self, findings: List[Finding]) -> List[IssueCorrelationGroup]:
        by_code: Dict[str, List[Finding]] = defaultdict(list)
        for finding in findings:
            by_code[finding.code].append(finding)

        groups: List[IssueCorrelationGroup] = []
        for code, code_findings in by_code.items():
            distinct_files = {f.file_path for f in code_findings if f.file_path is not None}
            if len(distinct_files) < MIN_GROUP_SIZE:
                continue
            groups.append(
                IssueCorrelationGroup(
                    basis=CorrelationBasis.SAME_CODE,
                    key=code,
                    findings=code_findings,
                    summary=(
                        f"'{code}' recurs across {len(distinct_files)} files, "
                        "suggesting a systemic pattern rather than an isolated issue."
                    ),
                )
            )
        return groups
