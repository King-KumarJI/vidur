"""Throwaway diagnostic (not part of the test suite): send the SAME
112-finding synthetic scenario's reasoning-stage output as ONE
unbatched call directly to the real local Ollama instance (bypassing
LLMRecommendationEngine's batching), and print the raw response text
plus its length and elapsed time. Goal: directly observe whether the
model's response is truncated (a token-budget/num_predict problem) or
completes but is malformed/wrong-shaped (a schema-following-at-scale
problem), to confirm which failure mode is actually occurring before
deciding whether num_predict or batching is the right fix.
"""
import json
import time

from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.ai_reasoning.llm_recommendation_engine import _SYSTEM_PROMPT
from app.core.ai_reasoning.ollama_client import OllamaClient
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

payload = {
    "correlation_groups": [g.to_dict() for g in correlation_groups],
    "dependency_assessments": [a.to_dict() for a in dependency_assessments],
    "debugging_hypotheses": [h.to_dict() for h in debugging_hypotheses],
    "drift_insight": drift_insight.to_dict() if drift_insight else None,
}
user_prompt = json.dumps(payload, default=str)
print(f"--- unbatched user_prompt size: {len(user_prompt)} chars ---")

client = OllamaClient()  # real settings: llama3, 120s timeout
start = time.time()
raw = client.chat_json(_SYSTEM_PROMPT, user_prompt)
elapsed = time.time() - start

print(f"--- elapsed: {elapsed:.1f}s ---")
print(f"--- raw response length: {len(raw)} chars ---")
print("--- raw response (full) ---")
print(raw)
print("--- end raw response ---")

try:
    parsed = json.loads(raw)
    print(f"--- valid JSON. top-level type: {type(parsed).__name__} ---")
    if isinstance(parsed, dict):
        print(f"--- top-level keys: {list(parsed.keys())} ---")
        print(f"--- has 'recommendations' key: {'recommendations' in parsed} ---")
except json.JSONDecodeError as exc:
    print(f"--- INVALID JSON: {exc} ---")
    print(f"--- last 200 chars: {raw[-200:]!r} ---")
