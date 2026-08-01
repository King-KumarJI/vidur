import { useState } from 'react'
import { RootPathForm } from '../components/RootPathForm'
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { runInspection } from '../services/apiClient'
import type { InspectionReportResponse } from '../services/types'

export function InspectionPage() {
  const { projectId } = useProject()
  const [report, setReport] = useState<InspectionReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [running, setRunning] = useState(false)

  async function handleRun(rootPath: string) {
    setRunning(true)
    setError(null)
    try {
      setReport(await runInspection(rootPath))
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Inspection Reports</h1>
        <p className="text-sm text-vidur-text-muted">Run a full static inspection of a project root.</p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before running an inspection.')} />
      ) : (
        <Card>
          <RootPathForm onRun={handleRun} running={running} runLabel="Run Inspection" />
        </Card>
      )}

      {running ? <Spinner label="Running inspection…" /> : null}
      <ErrorBanner error={error} />

      {report ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card title="Health Score">
              <p className="text-3xl font-semibold text-vidur-text">{report.health_score.toFixed(1)}</p>
            </Card>
            <Card title="Status">
              <p className="text-lg text-vidur-text">{report.status}</p>
              <p className="text-xs text-vidur-text-muted">
                {report.started_at} {report.completed_at ? `→ ${report.completed_at}` : ''}
              </p>
            </Card>
            <Card title="Files Analyzed">
              <p className="text-3xl font-semibold text-vidur-text">{report.files.length}</p>
            </Card>
          </div>

          <Card title={`Findings (${report.findings.length})`}>
            {report.findings.length === 0 ? (
              <EmptyState message="No findings." />
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-vidur-surface text-xs uppercase text-vidur-text-muted">
                    <tr>
                      <th className="py-1.5 pr-3">Severity</th>
                      <th className="py-1.5 pr-3">Code</th>
                      <th className="py-1.5 pr-3">Message</th>
                      <th className="py-1.5 pr-3">Location</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.findings.map((finding, i) => (
                      <tr key={i} className="border-t border-vidur-border">
                        <td className="py-1.5 pr-3"><Badge label={finding.severity} /></td>
                        <td className="py-1.5 pr-3 font-mono text-xs text-vidur-text-muted">{finding.code}</td>
                        <td className="py-1.5 pr-3 text-vidur-text">{finding.message}</td>
                        <td className="py-1.5 pr-3 text-xs text-vidur-text-muted">
                          {finding.file_path ?? '—'}
                          {finding.line ? `:${finding.line}` : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title={`File Metrics (${report.file_metrics.length})`}>
            {report.file_metrics.length === 0 ? (
              <EmptyState message="No file metrics." />
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-vidur-surface text-xs uppercase text-vidur-text-muted">
                    <tr>
                      <th className="py-1.5 pr-3">File</th>
                      <th className="py-1.5 pr-3">Functions</th>
                      <th className="py-1.5 pr-3">Classes</th>
                      <th className="py-1.5 pr-3">Max CC</th>
                      <th className="py-1.5 pr-3">Avg CC</th>
                      <th className="py-1.5 pr-3">Docstring %</th>
                      <th className="py-1.5 pr-3">Syntax OK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.file_metrics.map((metric) => (
                      <tr key={metric.relative_path} className="border-t border-vidur-border">
                        <td className="py-1.5 pr-3 font-mono text-xs text-vidur-text">{metric.relative_path}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{metric.function_count}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{metric.class_count}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{metric.max_cyclomatic_complexity}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{metric.average_cyclomatic_complexity.toFixed(1)}</td>
                        <td className="py-1.5 pr-3 text-vidur-text-muted">{(metric.docstring_coverage * 100).toFixed(0)}%</td>
                        <td className="py-1.5 pr-3">
                          {metric.has_syntax_error ? <Badge label="error" /> : <Badge label="low" />}
                        </td>
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
