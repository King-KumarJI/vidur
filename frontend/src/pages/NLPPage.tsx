import { useState } from 'react'
import { RootPathForm } from '../components/RootPathForm'
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { runNLPAnalysis } from '../services/apiClient'
import type { NLPReportResponse } from '../services/types'

export function NLPPage() {
  const { projectId } = useProject()
  const [report, setReport] = useState<NLPReportResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [running, setRunning] = useState(false)

  async function handleRun(rootPath: string) {
    setRunning(true)
    setError(null)
    try {
      setReport(await runNLPAnalysis(rootPath))
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">NLP Findings</h1>
        <p className="text-sm text-vidur-text-muted">
          Understands README/requirements/docstrings and checks whether the implementation matches
          documented intent.
        </p>
      </div>

      {!projectId ? (
        <ErrorBanner error={new Error('Select an active project on the Projects page before running NLP analysis.')} />
      ) : (
        <Card>
          <RootPathForm onRun={handleRun} running={running} runLabel="Run NLP Analysis" />
        </Card>
      )}

      {running ? <Spinner label="Running NLP analysis…" /> : null}
      <ErrorBanner error={error} />

      {report ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Documented Intent">
              <p className="text-lg text-vidur-text">{report.documented_intent.project_title ?? 'Untitled project'}</p>
              <div className="mt-2">
                <p className="text-xs uppercase text-vidur-text-muted">Declared Features</p>
                {report.documented_intent.declared_features.length === 0 ? (
                  <EmptyState message="None declared." />
                ) : (
                  <ul className="list-inside list-disc text-sm text-vidur-text-muted">
                    {report.documented_intent.declared_features.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="mt-2">
                <p className="text-xs uppercase text-vidur-text-muted">Declared Dependencies</p>
                <p className="text-sm text-vidur-text-muted">
                  {report.documented_intent.declared_dependencies.join(', ') || '—'}
                </p>
              </div>
            </Card>

            <Card title="Implemented Intent">
              <p className="text-sm text-vidur-text-muted">
                {report.implemented_intent.analyzed_file_count} file(s) analyzed
              </p>
              <div className="mt-2">
                <p className="text-xs uppercase text-vidur-text-muted">Imported Third-Party Packages</p>
                <p className="text-sm text-vidur-text-muted">
                  {report.implemented_intent.imported_third_party_packages.join(', ') || '—'}
                </p>
              </div>
            </Card>
          </div>

          <Card title={`Requirement Statements (${report.documented_intent.requirement_statements.length})`}>
            {report.documented_intent.requirement_statements.length === 0 ? (
              <EmptyState message="No requirement statements extracted." />
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto text-sm">
                {report.documented_intent.requirement_statements.map((r, i) => (
                  <li key={i} className="border-t border-vidur-border pt-2 first:border-t-0 first:pt-0">
                    <p className="text-vidur-text">{r.text}</p>
                    <p className="text-xs font-mono text-vidur-text-muted">{r.source_path}:{r.line}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title={`Consistency Findings (${report.consistency_findings.length})`}>
            {report.consistency_findings.length === 0 ? (
              <EmptyState message="No inconsistencies found." />
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
                    {report.consistency_findings.map((finding, i) => (
                      <tr key={i} className="border-t border-vidur-border">
                        <td className="py-1.5 pr-3"><Badge label={finding.severity} /></td>
                        <td className="py-1.5 pr-3 font-mono text-xs text-vidur-text-muted">{finding.code}</td>
                        <td className="py-1.5 pr-3 text-vidur-text">{finding.message}</td>
                        <td className="py-1.5 pr-3 text-xs text-vidur-text-muted">
                          {finding.file_path ?? '—'}{finding.line ? `:${finding.line}` : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title={`Semantic Similarity Results (${report.semantic_similarity_results.length})`}>
            {report.semantic_similarity_results.length === 0 ? (
              <EmptyState message="No semantic similarity results." />
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto text-sm">
                {report.semantic_similarity_results.map((r, i) => (
                  <li key={i} className="border-t border-vidur-border pt-2 first:border-t-0 first:pt-0">
                    <p className="text-vidur-text">{r.claim_text}</p>
                    <p className="text-xs text-vidur-text-muted">
                      Best match: <span className="font-mono">{r.best_match_file ?? 'none'}</span> · similarity {r.similarity_score.toFixed(2)}
                    </p>
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
