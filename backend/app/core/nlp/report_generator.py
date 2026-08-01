"""
VIDUR Core - NLP
Submodule: Report Generator
Purpose: Assemble the outputs of a full NLP run (documented intent,
implemented intent, consistency findings, and optional Major-tier
semantic similarity results) into a single NLPReport.
"""

from datetime import datetime
from typing import List, Optional

from app.core.inspection_engine.models import utc_now
from app.core.nlp.models import (
    ConsistencyFinding,
    DocumentedIntent,
    ImplementedIntent,
    NLPReport,
    SemanticSimilarityResult,
)


class NLPReportGenerator:
    """Builds the final NLPReport for a completed NLP run."""

    def generate(
        self,
        *,
        project_id: str,
        root_path: str,
        documented_intent: DocumentedIntent,
        implemented_intent: ImplementedIntent,
        consistency_findings: List[ConsistencyFinding],
        semantic_similarity_results: List[SemanticSimilarityResult],
        generated_at: Optional[datetime] = None,
    ) -> NLPReport:
        """Assemble the final NLPReport for one NLP analysis run."""
        return NLPReport(
            project_id=project_id,
            root_path=root_path,
            generated_at=generated_at or utc_now(),
            documented_intent=documented_intent,
            implemented_intent=implemented_intent,
            consistency_findings=consistency_findings,
            semantic_similarity_results=semantic_similarity_results,
        )
