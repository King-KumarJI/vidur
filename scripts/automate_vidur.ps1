# automate_vidur.ps1
#
# Runs Claude Code headlessly through each remaining VIDUR module in
# sequence, with no interactive confirmation. Stops immediately if a
# step fails, so nothing gets silently skipped or marked done.
#
# Usage (from the vidur/ project root):
#   powershell -ExecutionPolicy Bypass -File scripts\automate_vidur.ps1
#
# Requires: `claude` CLI installed and authenticated (`claude login`),
# run from inside the vidur/ folder so CLAUDE.md is picked up.

$modules = @(
    "Inspection Engine (backend/app/core/inspection_engine)",
    "AI Reasoning (backend/app/core/ai_reasoning)",
    "NLP (backend/app/core/nlp)",
    "ML Prediction (backend/app/core/ml_prediction)",
    "Deep Learning Vision (backend/app/core/deep_learning_vision)",
    "Memory (backend/app/memory)",
    "API Layer (backend/app/api/v1)"
)

foreach ($m in $modules) {
    Write-Host "=== Building module: $m ===" -ForegroundColor Cyan

    $prompt = @"
Read CLAUDE.md, docs/constitution/VIDUR_CONSTITUTION.md, and docs/tracker/development-tracker.md first.
Build the '$m' module completely: every planned file, fully production-ready, no placeholders.
Verify each file (py_compile at minimum, unit tests if applicable) before moving to the next file.
Update docs/tracker/development-tracker.md when the module is done.
Stop and report instead of guessing if you hit a decision only the project owner can make.
"@

    claude -p "$prompt" --dangerously-skip-permissions

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Module '$m' failed (exit code $LASTEXITCODE). Stopping so nothing downstream builds on a broken module." -ForegroundColor Red
        exit 1
    }

    Write-Host "=== Module complete: $m ===" -ForegroundColor Green
}

Write-Host "All modules complete." -ForegroundColor Green
