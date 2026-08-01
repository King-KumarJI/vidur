"""
VIDUR Core - Inspection Engine
Submodule: Health Score
Purpose: Reduce a list of Findings into a single 0-100 project health
score, weighted by severity and normalized by project size so that
larger projects are not unfairly penalized for a fixed issue count.
"""

from collections import Counter
from typing import Dict, List

from app.core.inspection_engine.enums import Severity
from app.core.inspection_engine.models import Finding

#: How strongly the per-file weighted-issue density reduces the
#: health score. Larger values make the score more sensitive to
#: findings; see `HealthScoreCalculator.calculate` for the formula.
DENSITY_PENALTY_SCALE = 20.0

MIN_SCORE = 0.0
MAX_SCORE = 100.0


class HealthScoreCalculator:
    """Computes an aggregated project health score from findings."""

    def calculate(self, findings: List[Finding], total_files: int) -> float:
        """Return a health score in [0, 100].

        The score starts at 100 and is reduced by the total severity
        weight of all findings, normalized by the number of inspected
        files so that the score reflects issue *density* rather than
        raw issue count.
        """
        if not findings:
            return MAX_SCORE

        total_weight = sum(finding.severity.weight for finding in findings)
        density = total_weight / max(total_files, 1)
        score = MAX_SCORE - (density * DENSITY_PENALTY_SCALE)
        return max(MIN_SCORE, min(MAX_SCORE, round(score, 2)))

    @staticmethod
    def count_by_severity(findings: List[Finding]) -> Dict[str, int]:
        """Return the number of findings per severity level, including
        zero counts for severities that had no findings."""
        counts = Counter(finding.severity.value for finding in findings)
        return {severity.value: counts.get(severity.value, 0) for severity in Severity}
