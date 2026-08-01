"""
VIDUR - Memory Package.

Single import surface for persisting and semantically recalling
VIDUR's own analysis history - Inspection Engine, AI Reasoning, NLP,
ML Prediction, and Deep Learning Vision reports, plus health-score
trends over time - per project, via the project-isolated MongoDB
record store and ChromaDB semantic index. Gated by the
MINOR_PROJECT_MEMORY feature flag (Article 41-44), enabled by default
as Minor-Project baseline infrastructure.

Scope (explicit, user-directed): VIDUR's own analysis history, not
conversational/chat memory.
"""

from app.memory.engine import MemoryEngine
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import (
    InvalidMemoryQueryError,
    MemoryDisabledError,
    MemoryModuleError,
    MemoryPersistenceError,
)
from app.memory.models import MemoryRecallMatch, MemoryRecord, MemorySemanticMatch
from app.memory.record_store import MemoryRecordStore
from app.memory.record_summarizer import RecordSummarizer
from app.memory.semantic_index import MemorySemanticIndex

__all__ = [
    "MemoryEngine",
    "MemoryRecordStore",
    "MemorySemanticIndex",
    "RecordSummarizer",
    "MemoryRecordType",
    "MemoryRecord",
    "MemorySemanticMatch",
    "MemoryRecallMatch",
    "MemoryModuleError",
    "MemoryDisabledError",
    "InvalidMemoryQueryError",
    "MemoryPersistenceError",
]
