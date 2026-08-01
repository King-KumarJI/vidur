import { useState } from 'react'
import { RootPathForm } from '../components/RootPathForm'
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { runMLPrediction } from '../services/apiClient'
import type { MLPredictionReportResponse } from '../services/types'

const RISK_BAR_COLOR: Record<string, string> = {
  low: 'var(--color-vidur-good)',
  medium: 'var(--color-vidur-warn)',
  high: 'var(--color-vidur-serious)',
  critical: 'var(--color-vidur-bad)',
}

export function MLPredictionPage() {
  const { projectId } = useProject()
  const [report, setReport] = useState<MLPredictionReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [running, setRunning] = useState(false)
  const [includeReasoning, setIncludeReasoning] = useState(true)

  async function handleRun(rootPath: string) {
    setRunning(true)
    setError(null)
    try {
      setReport(await runMLPrediction(rootPath, includeReasoning))
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">ML Prediction</h1>
        <p className="text-sm text-vidur-text-muted">
          Major Project capability (feature flag <code>MAJOR_ML_RISK_PREDICTION</code>, disabled by
          default). Predicts regression probability, technical debt, quality trend, and failure
          probability from inspection data.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before running ML prediction.')} />
      ) : (
        <Card>
          <RootPathForm
            onRun={handleRun}
            running={running}
            runLabel="Run ML Prediction"
            extraControls={
              <label className="flex items-center gap-2 text-sm text-vidur-text-muted">
                <input
                  type="checkbox"
                  checked={includeReasoning}
                  onChange={(e) => setIncludeReasoning(e.target.checked)}
                  className="accent-vidur-accent"
                />
                Include AI reasoning
              </label>
            }
          />
        </Card>
      )}

      {running ? <Spinner label="Running inspection + prediction…" /> : null}
      <ErrorBanner error={error} />

      {report ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <PredictionCard
              title="Regression Risk"
              probability={report.regression_risk.probability}
              riskLevel={report.regression_risk.risk_level}
              summary={report.regression_risk.summary}
            />
            <Card title="Technical Debt">
              <p className="text-2xl font-semibold text-vidur-text">{report.technical_debt.debt_score.toFixed(1)}</p>
              <Badge label={report.technical_debt.risk_level} />
              <p className="mt-1 text-xs text-vidur-text-muted">
                ~{report.technical_debt.estimated_remediation_hours.toFixed(1)}h remediation
              </p>
              <p className="mt-1 text-sm text-vidur-text-muted">{report.technical_debt.summary}</p>
            </Card>
            <Card title="Quality Trend">
              <p className="text-lg text-vidur-text">{report.quality_trend.direction}</p>
              <p className="text-xs text-vidur-text-muted">
                {report.quality_trend.current_health_score.toFixed(1)} → {report.quality_trend.projected_next_health_score.toFixed(1)}
              </p>
              <p className="mt-1 text-sm text-vidur-text-muted">{report.quality_trend.summary}</p>
            </Card>
            <PredictionCard
              title="Failure Probability"
              probability={report.failure_probability.probability}
              riskLevel={report.failure_probability.risk_level}
              summary={report.failure_probability.summary}
            />
          </div>

          <Card title="Project Feature Vector">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-5">
              {Object.entries(report.feature_vector).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs text-vidur-text-muted">{key.replace(/_/g, ' ')}</dt>
                  <dd className="text-vidur-text">{typeof value === 'number' ? value.toFixed(2) : String(value)}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card title={`Module Risk Scores (${report.module_risk_scores.length})`}>
            {report.module_risk_scores.length === 0 ? (
              <EmptyState message="No module risk scores." />
            ) : (
              <ul className="max-h-96 space-y-2 overflow-y-auto">
                {[...report.module_risk_scores]
                  .sort((a, b) => b.composite_risk_score - a.composite_risk_score)
                  .map((m) => (
                    <li key={m.file_path} className="text-sm">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="truncate font-mono text-xs text-vidur-text">{m.file_path}</span>
                        <span className="shrink-0 text-xs text-vidur-text-muted">{m.composite_risk_score.toFixed(2)}</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-vidur-surface-raised">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(100, m.composite_risk_score * 100)}%`,
                            background: RISK_BAR_COLOR[m.risk_level.toLowerCase()] ?? 'var(--color-vidur-accent)',
                          }}
                        />
                      </div>
                    </li>
                  ))}
              </ul>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  )
}

function PredictionCard({ title, probability, riskLevel, summary }: { title: string; probability: number; riskLevel: string; summary: string }) {
  return (
    <Card title={title}>
      <p className="text-2xl font-semibold text-vidur-text">{(probability * 100).toFixed(0)}%</p>
      <Badge label={riskLevel} />
      <p className="mt-1 text-sm text-vidur-text-muted">{summary}</p>
    </Card>
  )
}
