import { useEffect, useState } from 'react'
import { HealthScoreTrendChart } from '../components/HealthScoreTrendChart'
import { Card, EmptyState, ErrorBanner, Spinner } from '../components/ui'
import { useProject } from '../context/ProjectContext'
import { getAppInfo, getDatabaseHealth, getFeatureFlags, getHealthScoreTrend } from '../services/apiClient'
import type { AppInfoResponse, DatabaseHealthResponse, FeatureFlagsResponse } from '../services/types'

export function DashboardPage() {
  const { projectId } = useProject()

  const [appInfo, setAppInfo] = useState<AppInfoResponse | null>(null)
  const [dbHealth, setDbHealth] = useState<DatabaseHealthResponse | null>(null)
  const [flags, setFlags] = useState<FeatureFlagsResponse | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  const [healthScores, setHealthScores] = useState<number[] | null>(null)
  const [trendError, setTrendError] = useState<unknown>(null)
  const [trendLoading, setTrendLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    Promise.all([getAppInfo(), getDatabaseHealth(), getFeatureFlags()])
      .then(([info, health, flagState]) => {
        if (cancelled) return
        setAppInfo(info)
        setDbHealth(health)
        setFlags(flagState)
      })
      .catch((err) => !cancelled && setLoadError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!projectId) {
      setHealthScores(null)
      return
    }
    let cancelled = false
    setTrendLoading(true)
    setTrendError(null)
    getHealthScoreTrend()
      .then((result) => !cancelled && setHealthScores(result.health_scores))
      .catch((err) => !cancelled && setTrendError(err))
      .finally(() => !cancelled && setTrendLoading(false))
    return () => {
      cancelled = true
    }
  }, [projectId])

  const minorFlags = flags ? Object.entries(flags.flags).filter(([name]) => name.startsWith('MINOR_')) : []
  const majorFlags = flags ? Object.entries(flags.flags).filter(([name]) => name.startsWith('MAJOR_')) : []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Dashboard</h1>
        <p className="text-sm text-vidur-text-muted">Project health overview and system status.</p>
      </div>

      {loading ? <Spinner label="Loading application status…" /> : null}
      <ErrorBanner error={loadError} />

      {!loading && !loadError ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card title="Application">
            <p className="text-lg text-vidur-text">{appInfo?.app_full_name}</p>
            <p className="text-sm text-vidur-text-muted">
              v{appInfo?.app_version} · Constitution {appInfo?.constitution_version}
            </p>
            <p className="mt-2 text-xs uppercase tracking-wide text-vidur-text-muted">
              {appInfo?.environment} {appInfo?.debug ? '(debug)' : ''}
            </p>
          </Card>

          <Card title="Database Connectivity">
            <ul className="space-y-1 text-sm">
              <li className="flex items-center justify-between">
                <span className="text-vidur-text-muted">MongoDB</span>
                <StatusDot ok={dbHealth?.mongodb_connected ?? false} />
              </li>
              <li className="flex items-center justify-between">
                <span className="text-vidur-text-muted">ChromaDB</span>
                <StatusDot ok={dbHealth?.chromadb_connected ?? false} />
              </li>
              <li className="flex items-center justify-between border-t border-vidur-border pt-1">
                <span className="text-vidur-text-muted">Overall</span>
                <StatusDot ok={dbHealth?.healthy ?? false} />
              </li>
            </ul>
          </Card>

          <Card title="Feature Flags">
            <p className="text-sm text-vidur-text-muted">
              {minorFlags.filter(([, v]) => v).length}/{minorFlags.length} Minor enabled
            </p>
            <p className="text-sm text-vidur-text-muted">
              {majorFlags.filter(([, v]) => v).length}/{majorFlags.length} Major enabled
            </p>
          </Card>
        </div>
      ) : null}

      <Card title="Project Health Score Trend">
        {!projectId ? (
          <EmptyState message="Select a project to view its recorded health-score trend." />
        ) : trendLoading ? (
          <Spinner label="Loading trend…" />
        ) : trendError ? (
          <ErrorBanner error={trendError} />
        ) : (
          <HealthScoreTrendChart healthScores={healthScores ?? []} />
        )}
      </Card>
    </div>
  )
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`flex items-center gap-1.5 text-xs font-medium ${ok ? 'text-vidur-good' : 'text-vidur-bad'}`}>
      <span className="h-2 w-2 rounded-full" style={{ background: ok ? 'var(--color-vidur-good)' : 'var(--color-vidur-bad)' }} />
      {ok ? 'Connected' : 'Down'}
    </span>
  )
}
