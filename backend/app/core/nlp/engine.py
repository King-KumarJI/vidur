"""
VIDUR Core - NLP
Submodule: Engine
Purpose: Orchestrates a full NLP analysis run over a project root -
document discovery, documented/implemented intent extraction,
requirement-to-implementation consistency checking, and (when enabled)
Major-tier semantic similarity reasoning - into a single NLPReport.
Enforces the MINOR_REQUIREMENT_CONSISTENCY feature flag and Article 21
(Absolute Project Isolation) by requiring and binding a valid Project
ID for the duration of the run.
"""

from typing import Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.inspection_engine.exceptions import InvalidInspectionTargetError
from app.core.nlp.code_intent_extractor import ImplementedIntentExtractor
from app.core.nlp.consistency_checker import ConsistencyChecker
from app.core.nlp.document_discovery import DocumentDiscovery
from app.core.nlp.exceptions import NLPDisabledError, NLPError
from app.core.nlp.intent_extractor import DocumentedIntentExtractor
from app.core.nlp.models import NLPReport
from app.core.nlp.report_generator import NLPReportGenerator
from app.core.nlp.semantic_reasoner import SemanticSimilarityReasoner
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError

logger = get_logger("nlp.engine")


class NLPEngine:
    """Top-level orchestrator for a single NLP analysis run over a
    project root."""

    def __init__(
        self,
        document_discovery: Optional[DocumentDiscovery] = None,
        documented_intent_extractor: Optional[DocumentedIntentExtractor] = None,
        implemented_intent_extractor: Optional[ImplementedIntentExtractor] = None,
        consistency_checker: Optional[ConsistencyChecker] = None,
        semantic_reasoner: Optional[SemanticSimilarityReasoner] = None,
        report_generator: Optional[NLPReportGenerator] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._document_discovery = document_discovery or DocumentDiscovery()
        self._documented_intent_extractor = documented_intent_extractor or DocumentedIntentExtractor()
        self._implemented_intent_extractor = implemented_intent_extractor or ImplementedIntentExtractor()
        self._consistency_checker = consistency_checker or ConsistencyChecker()
        self._semantic_reasoner = semantic_reasoner or SemanticSimilarityReasoner()
        self._report_generator = report_generator or NLPReportGenerator()
        self._feature_flags = feature_flag_registry or feature_flags

    def run(self, project_id: str, root_path: str) -> NLPReport:
        """Run a full NLP analysis of `root_path` scoped to
        `project_id`.

        Raises NLPDisabledError if MINOR_REQUIREMENT_CONSISTENCY is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, InvalidInspectionTargetError if `root_path` is not
        an inspectable directory, and NLPError wrapping any other
        unexpected failure encountered mid-run. Major-tier semantic
        similarity reasoning is included only when
        MAJOR_ADVANCED_NLP_DOCUMENT_REASONING is enabled; otherwise the
        report's `semantic_similarity_results` is an empty list
        (Article 41-44: the capability exists and runs, but stays
        inert until explicitly activated).
        """
        if not self._feature_flags.is_enabled(FeatureFlag.MINOR_REQUIREMENT_CONSISTENCY):
            raise NLPDisabledError(
                "NLP analysis was requested but the MINOR_REQUIREMENT_CONSISTENCY "
                "feature flag is disabled."
            )

        normalized_project_id = validate_project_id_format(project_id)
        logger.info("NLP analysis started for project_id=%s root=%s", normalized_project_id, root_path)

        with project_scope(normalized_project_id):
            try:
                report = self._execute(normalized_project_id, root_path)
            except (NLPError, ProjectIsolationError, InvalidInspectionTargetError):
                raise
            except Exception as exc:  # extraction/reasoning stages must never crash a whole run
                logger.error(
                    "NLP analysis failed for project_id=%s root=%s: %s",
                    normalized_project_id,
                    root_path,
                    exc,
                )
                raise NLPError(
                    f"NLP analysis run failed for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "NLP analysis completed for project_id=%s consistency_findings=%d",
            normalized_project_id,
            len(report.consistency_findings),
        )
        return report

    def _execute(self, project_id: str, root_path: str) -> NLPReport:
        documents = self._document_discovery.discover(root_path)
        documented_intent = self._documented_intent_extractor.extract(documents)
        implemented_intent = self._implemented_intent_extractor.extract(documents)
        consistency_findings = self._consistency_checker.check(documented_intent, implemented_intent)

        semantic_similarity_results = []
        if self._feature_flags.is_enabled(FeatureFlag.MAJOR_ADVANCED_NLP_DOCUMENT_REASONING):
            semantic_similarity_results = self._semantic_reasoner.reason(
                documented_intent, implemented_intent
            )

        return self._report_generator.generate(
            project_id=project_id,
            root_path=root_path,
            documented_intent=documented_intent,
            implemented_intent=implemented_intent,
            consistency_findings=consistency_findings,
            semantic_similarity_results=semantic_similarity_results,
        )
