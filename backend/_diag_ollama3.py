"""Throwaway diagnostic: run the real LLMRecommendationEngine.build()
(with the new batching fix) against the same 112-finding synthetic
scenario, live against Ollama, to confirm it now produces genuine
parsed recommendations instead of raising OllamaResponseParsingError."""
import time

from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.ai_reasoning.llm_recommendation_engine import LLMRecommendationEngine
from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import FileRecord, Finding

CODES = [
    ("HIGH_COMPLEXITY", FindingCategory.CODE_QUALITY, Severity.WARNING),
    ("LOW_DOCSTRING_COVERAGE", FindingCategory.CODE_QUALITY, Severity.INFO),
    ("SYNTAX_ERROR", FindingCategory.SYNTAX, Severity.CRITICAL),
    ("CIRCULAR_DEPENDENCY", FindingCategory.DEPENDENCY, Severity.ERROR),
    ("MISSING_INIT_FILE", FindingCategory.ARCHITECTURE, Severity.WARNING),
    ("FILE_MODIFIED", FindingCategory.DRIFT, Severity.INFO),
]

findings = []
files = []
for i in range(112):
    path = f"app/module_{i % 20}/file_{i}.py"
    code, category, severity = CODES[i % len(CODES)]
    findings.append(
        Finding(
            category=category,
            severity=severity,
            code=code,
            message=f"Synthetic finding #{i} for {path}: {code} detected during diagnostic run.",
            file_path=path,
            line=(i % 200) + 1,
        )
    )

for i in range(20):
    rel = f"app/module_{i}/file_{i}.py"
    files.append(
        FileRecord(
            relative_path=rel,
            absolute_path=f"C:/nonexistent/{rel}",
            size_bytes=1000,
            line_count=50,
            extension="py",
            content_hash="deadbeef",
        )
    )

correlator = IssueCorrelator()
dep_reasoner = DependencyReasoner()
debug_assistant = DebuggingAssistant()
drift_reasoner = DriftReasoner()

correlation_groups = correlator.correlate(findings)
dependency_assessments = dep_reasoner.assess(files, findings)
debugging_hypotheses = debug_assistant.generate(findings)
drift_insight = drift_reasoner.reason(findings, dependency_assessments, len(files))

engine = LLMRecommendationEngine()
start = time.time()
recommendations = engine.build(correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight)
elapsed = time.time() - start

print(f"--- elapsed: {elapsed:.1f}s ---")
print(f"recommendations returned: {len(recommendations)}")
for rec in recommendations[:10]:
    print(f"  [{rec.priority.value}] ({rec.category.value}) {rec.title}: {rec.description[:100]}")
