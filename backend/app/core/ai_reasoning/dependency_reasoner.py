"""
VIDUR Core - AI Reasoning
Submodule: Dependency Reasoner
Purpose: Reason about the "blast radius" of files that carry
findings, using the internal import graph. A file with findings that
many other internal files transitively depend on is a higher priority
than an equally-flawed file nothing else imports.
"""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from app.core.ai_reasoning.models import DependencyImpactAssessment
from app.core.inspection_engine.dependency_analyzer import DependencyAnalyzer
from app.core.inspection_engine.models import FileRecord, Finding

#: Weight applied to a file's own finding-severity total when combining
#: it with dependent count into a single risk score. See
#: `DependencyReasoner.assess` for the full formula.
SEVERITY_CONTRIBUTION_SCALE = 0.5


class DependencyReasoner:
    """Computes dependency-impact (blast radius) assessments for every
    internal file that has at least one finding."""

    def __init__(self, dependency_analyzer: Optional[DependencyAnalyzer] = None) -> None:
        self._dependency_analyzer = dependency_analyzer or DependencyAnalyzer()

    def assess(
        self, files: List[FileRecord], findings: List[Finding]
    ) -> List[DependencyImpactAssessment]:
        """Return one DependencyImpactAssessment per internal file that
        has findings, ordered by descending risk score.

        `risk_score` combines how many other internal files transitively
        depend on the file (its blast radius) with the total severity
        weight of its own findings: `transitive_dependents +
        (own_severity_weight * SEVERITY_CONTRIBUTION_SCALE)`.
        """
        graph = self._dependency_analyzer.build_graph(files)
        reverse_graph = self._build_reverse_graph(graph)

        weight_by_file: Dict[str, int] = defaultdict(int)
        count_by_file: Dict[str, int] = defaultdict(int)
        for finding in findings:
            if finding.file_path is not None and finding.file_path in graph:
                weight_by_file[finding.file_path] += finding.severity.weight
                count_by_file[finding.file_path] += 1

        assessments: List[DependencyImpactAssessment] = []
        for file_path in weight_by_file:
            transitive = self._transitive_dependents(reverse_graph, file_path)
            direct = len(reverse_graph.get(file_path, set()))
            risk_score = round(
                len(transitive) + (weight_by_file[file_path] * SEVERITY_CONTRIBUTION_SCALE), 2
            )
            assessments.append(
                DependencyImpactAssessment(
                    file_path=file_path,
                    direct_dependents=direct,
                    transitive_dependents=len(transitive),
                    dependent_paths=sorted(transitive),
                    finding_count=count_by_file[file_path],
                    risk_score=risk_score,
                )
            )

        assessments.sort(key=lambda assessment: (-assessment.risk_score, assessment.file_path))
        return assessments

    @staticmethod
    def _build_reverse_graph(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        for importer, imported_set in graph.items():
            for imported in imported_set:
                reverse_graph[imported].add(importer)
        return reverse_graph

    @staticmethod
    def _transitive_dependents(reverse_graph: Dict[str, Set[str]], start: str) -> Set[str]:
        visited: Set[str] = set()
        queue: deque = deque(reverse_graph.get(start, set()))
        while queue:
            node = queue.popleft()
            if node in visited or node == start:
                continue
            visited.add(node)
            queue.extend(reverse_graph.get(node, set()) - visited)
        return visited
