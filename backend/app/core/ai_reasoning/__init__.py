"""
VIDUR Core - AI Reasoning Package.

Single import surface for running AI reasoning over a completed
Inspection Engine InspectionReport: issue correlation, dependency-
impact (blast radius) reasoning, rule-based debugging assistance, and
drift-significance reasoning, aggregated into a single, prioritized
list of advisory recommendations.
"""

from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.engine import AIReasoningEngine
from app.core.ai_reasoning.enums import (
    ChurnLevel,
    CorrelationBasis,
    InsightCategory,
    RecommendationPriority,
)
from app.core.ai_reasoning.exceptions import (
    AIReasoningError,
    InvalidReasoningInputError,
    ReasoningDisabledError,
)
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.ai_reasoning.models import (
    DebuggingHypothesis,
    DependencyImpactAssessment,
    DriftInsight,
    IssueCorrelationGroup,
    Recommendation,
    ReasoningReport,
)
from app.core.ai_reasoning.recommendation_engine import RecommendationEngine
from app.core.ai_reasoning.report_generator import ReasoningReportGenerator

__all__ = [
    "AIReasoningEngine",
    "IssueCorrelator",
    "DependencyReasoner",
    "DebuggingAssistant",
    "DriftReasoner",
    "RecommendationEngine",
    "ReasoningReportGenerator",
    "RecommendationPriority",
    "InsightCategory",
    "CorrelationBasis",
    "ChurnLevel",
    "IssueCorrelationGroup",
    "DependencyImpactAssessment",
    "DebuggingHypothesis",
    "DriftInsight",
    "Recommendation",
    "ReasoningReport",
    "AIReasoningError",
    "ReasoningDisabledError",
    "InvalidReasoningInputError",
]
