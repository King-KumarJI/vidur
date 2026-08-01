import { useState } from 'react'
import { RootPathForm } from '../components/RootPathForm'
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { runAIReasoning } from '../services/apiClient'
import type { ReasoningReportResponse } from '../services/types'

export function AIReasoningPage() {
  const { projectId } = useProject()
  const [report, setReport] = useState<ReasoningReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [running, setRunning] = useState(false)

  async function handleRun(rootPath: string) {
    setRunning(true)
    setError(null)
    try {
      setReport(await runAIReasoning(rootPath))
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">AI Reasoning</h1>
        <p className="text-sm text-vidur-text-muted">
          Runs a fresh inspection, then correlates findings, assesses dependency impact, forms debugging
          hypotheses, and produces prioritized recommendations.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before running AI reasoning.')} />
      ) : (
        <Card>
          <RootPathForm onRun={handleRun} running={running} runLabel="Run AI Reasoning" />
        </Card>
      )}

      {running ? <Spinner label="Running inspection + reasoning…" /> : null}
      <ErrorBanner error={error} />

      {report ? (
        <div className="space-y-4">
          {report.drift_insight ? (
            <Card title="Drift Insight">
              <p className="mb-2 text-sm text-vidur-text">{report.drift_insight.summary}</p>
              <div className="flex flex-wrap gap-4 text-sm text-vidur-text-muted">
                <span>Churn: <Badge label={report.drift_insight.churn_level} /></span>
                <span>+{report.drift_insight.added_count} / -{report.drift_insight.removed_count} / ~{report.drift_insight.modified_count}</span>
              </div>
              {report.drift_insight.high_impact_files.length > 0 ? (
                <ul className="mt-2 list-inside list-disc text-xs text-vidur-text-muted">
                  {report.drift_insight.high_impact_files.map((f) => (
                    <li key={f} className="font-mono">{f}</li>
                  ))}
                </ul>
              ) : null}
            </Card>
          ) : null}

          <Card title={`Recommendations (${report.recommendations.length})`}>
            {report.recommendations.length === 0 ? (
              <EmptyState message="No recommendations." />
            ) : (
              <ul className="space-y-3">
                {report.recommendations.map((rec, i) => (
                  <li key={i} className="rounded-md border border-vidur-border p-3">
                    <div className="mb-1 flex items-center gap-2">
                      <Badge label={rec.priority} />
                      <span className="text-xs uppercase text-vidur-text-muted">{rec.category}</span>
                    </div>
                    <p className="font-medium text-vidur-text">{rec.title}</p>
                    <p className="text-sm text-vidur-text-muted">{rec.description}</p>
                    {rec.affected_files.length > 0 ? (
                      <p className="mt-1 text-xs font-mono text-vidur-text-muted">{rec.affected_files.join(', ')}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title={`Issue Correlation Groups (${report.correlation_groups.length})`}>
            {report.correlation_groups.length === 0 ? (
              <EmptyState message="No correlated issue groups." />
            ) : (
              <ul className="space-y-3">
                {report.correlation_groups.map((group) => (
                  <li key={group.key} className="rounded-md border border-vidur-border p-3">
                    <p className="text-xs uppercase text-vidur-text-muted">{group.basis} · {group.key}</p>
                    <p className="text-sm text-vidur-text">{group.summary}</p>
                    <p className="mt-1 text-xs text-vidur-text-muted">{group.findings.length} finding(s)</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title={`Debugging Hypotheses (${report.debugging_hypotheses.length})`}>
            {report.debugging_hypotheses.length === 0 ? (
              <EmptyState message="No debugging hypotheses." />
            ) : (
              <ul className="space-y-3">
                {report.debugging_hypotheses.map((h) => (
                  <li key={h.finding_code} className="rounded-md border border-vidur-border p-3">
                    <p className="font-mono text-xs text-vidur-text-muted">{h.finding_code} · seen {h.occurrence_count}×</p>
                    <p className="font-medium text-vidur-text">{h.probable_cause}</p>
                    <p className="text-sm text-vidur-text-muted">{h.explanation}</p>
                    {h.suggested_next_steps.length > 0 ? (
                      <ul className="mt-1 list-inside list-disc text-xs text-vidur-text-muted">
                        {h.suggested_next_steps.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title={`Dependency Impact Assessments (${report.dependency_assessments.length})`}>
            {report.dependency_assessments.length === 0 ? (
              <EmptyState message="No dependency impact data." />
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-vidur-surface text-xs uppercase text-vidur-text-muted">
                    <tr>
                      <th className="py-1.5 pr-3">File</th>
                      <th className="py-1.5 pr-3">Direct Dependents</th>
                      <th className="py-1.5 pr-3">Transitive Dependents</th>
                      <th className="py-1.5 pr-3">Findings</th>
                      <th className="py-1.5 pr-3">Risk Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.dependency_assessments.map((a) => (
                      <tr key={a.file_path} className="border-t border-vidur-border">
                        <td className="py-1.5 pr-3 font-mono text-xs text-vidur-text">{a.file_path}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{a.direct_dependents}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{a.transitive_dependents}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{a.finding_count}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{a.risk_score.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  )
}
