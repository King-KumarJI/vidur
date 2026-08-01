import { useEffect, useState } from 'react'
import { Card, ErrorBanner, Spinner } from '../components/ui'
import { getAppInfo, getFeatureFlags } from '../services/apiClient'
import type { AppInfoResponse, FeatureFlagsResponse } from '../services/types'

export function FeatureFlagsPage() {
  const [appInfo, setAppInfo] = useState<AppInfoResponse | null>(null)
  const [flags, setFlags] = useState<FeatureFlagsResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([getAppInfo(), getFeatureFlags()])
      .then(([info, flagState]) => {
        if (cancelled) return
        setAppInfo(info)
        setFlags(flagState)
      })
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const minorFlags = flags ? Object.entries(flags.flags).filter(([name]) => name.startsWith('MINOR_')) : []
  const majorFlags = flags ? Object.entries(flags.flags).filter(([name]) => name.startsWith('MAJOR_')) : []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-vidur-text">Feature Flags / Settings</h1>
        <p className="text-sm text-vidur-text-muted">
          Resolved feature-flag state and application identity. Flags are read-only here — per Article
          41-44, they are activated exclusively via <code>backend/app/config/feature_flags.py</code> or
          environment variables, never at runtime through the API.
        </p>
      </div>

      {loading ? <Spinner label="Loading configuration…" /> : null}
      <ErrorBanner error={error} />

      {appInfo ? (
        <Card title="Application">
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <Field label="Name" value={appInfo.app_full_name} />
            <Field label="Version" value={appInfo.app_version} />
            <Field label="Constitution" value={appInfo.constitution_version} />
            <Field label="Environment" value={appInfo.environment} />
            <Field label="Debug" value={appInfo.debug ? 'true' : 'false'} />
          </dl>
        </Card>
      ) : null}

      {flags ? (
        <>
          <Card title="Minor Project (baseline)">
            <FlagList entries={minorFlags} />
          </Card>
          <Card title="Major Project (advanced)">
            <FlagList entries={majorFlags} />
          </Card>
        </>
      ) : null}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-vidur-text-muted">{label}</dt>
      <dd className="text-vidur-text">{value}</dd>
    </div>
  )
}

function FlagList({ entries }: { entries: [string, boolean][] }) {
  return (
    <ul className="space-y-1">
      {entries.map(([name, enabled]) => (
        <li key={name} className="flex items-center justify-between border-t border-vidur-border py-1.5 first:border-t-0">
          <span className="font-mono text-sm text-vidur-text">{name}</span>
          <span className={`flex items-center gap-1.5 text-xs font-medium ${enabled ? 'text-vidur-good' : 'text-vidur-text-muted'}`}>
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: enabled ? 'var(--color-vidur-good)' : 'var(--color-vidur-muted)' }}
            />
            {enabled ? 'Enabled' : 'Disabled'}
          </span>
        </li>
      ))}
    </ul>
  )
}
