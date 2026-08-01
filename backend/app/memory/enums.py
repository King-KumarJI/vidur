"""
VIDUR - Memory
Submodule: Enums
Purpose: Shared enumerations used across the Memory module to classify
which upstream pipeline produced a stored memory record.
"""

from enum import Enum


class MemoryRecordType(str, Enum):
    """The upstream VIDUR pipeline that produced a stored MemoryRecord.

    One member per report-producing module that the Memory module
    knows how to persist and recall (Chapter VII domains: AI,
    Requirement/Architecture Consistency via NLP, ML, and Deep
    Learning). IoT is intentionally excluded - Chapter VII scopes IoT
    as isolated from the core inspection engine, and Memory's scope is
    VIDUR's own analysis history, not sensor telemetry.
    """

    INSPECTION = "inspection"
    AI_REASONING = "ai_reasoning"
    NLP = "nlp"
    ML_PREDICTION = "ml_prediction"
    VISUAL_REGRESSION = "visual_regression"
